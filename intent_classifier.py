# -*- coding: utf-8 -*-
"""
FIX 701: Intent Classifier - Clasificador centralizado de intenciones con fuzzy matching.

Problema: 330+ patrones hardcodeados en _detectar_patron_simple_optimizado() usan
substring exacto. STT produce variantes ("mándame" vs "mandame", "mandarme" vs "enviarme")
que no matchean. Cada variante requiere un FIX nuevo.

Solución: Clasificador centralizado con:
  1. Exact match (rápido, 0ms) para patrones conocidos
  2. Fuzzy match (SequenceMatcher >= 0.80) para variantes STT

Arquitectura ADITIVA: Si este módulo falla, el código existente (patrones inline) sigue funcionando.
"""

import re
from enum import Enum
from difflib import SequenceMatcher


class IntentCategory(Enum):
    """Categorías de intención del cliente."""
    CALLBACK = "callback"               # Llamar después / marcar más tarde
    TRANSFER = "transfer"               # Transferir llamada / "espere un momento"
    OFFER_DATA = "offer_data"           # Cliente ofrece dato ("te paso su número")
    REJECT_DATA = "reject_data"         # Cliente rechaza dar dato ("no tengo WhatsApp")
    FAREWELL = "farewell"               # Despedida ("hasta luego", "adiós")
    INTEREST = "interest"               # Interés ("sí, dígame", "me interesa")
    NO_INTEREST = "no_interest"         # Sin interés ("no me interesa", "no gracias")
    QUESTION = "question"               # Pregunta directa ("¿qué venden?")
    ANOTHER_BRANCH = "another_branch"   # Otra sucursal / ubicación
    CORRECTION = "correction"           # Corrección ("no es eso", "me equivoqué")
    IDENTITY = "identity"               # Pregunta identidad ("¿quién habla?")
    CONFIRMATION = "confirmation"       # Confirmación simple ("sí", "claro", "ok")
    CLOSED = "closed"                   # Negocio cerrado
    MANAGER_ABSENT = "manager_absent"   # Encargado no disponible


class IntentResult:
    """Resultado de clasificación."""
    __slots__ = ('category', 'confidence', 'pattern', 'method')

    def __init__(self, category, confidence, pattern, method='exact'):
        self.category = category
        self.confidence = confidence
        self.pattern = pattern
        self.method = method  # 'exact' o 'fuzzy'

    def __repr__(self):
        return (f"IntentResult(category={self.category.value}, "
                f"confidence={self.confidence:.2f}, pattern='{self.pattern}', "
                f"method='{self.method}')")


class IntentClassifier:
    """
    Clasificador centralizado de intenciones con exact + fuzzy matching.
    Complementa _detectar_patron_simple_optimizado() sin reemplazarlo.
    """

    FUZZY_THRESHOLD = 0.80  # SequenceMatcher similarity mínima

    # Orden de prioridad: categorías más específicas/negativas ANTES de genéricas/positivas
    # Evita que "no me interesa" matchee "me interesa" (INTEREST) antes que NO_INTEREST
    PRIORITY_ORDER = [
        IntentCategory.CALLBACK,        # Antes de TRANSFER (más específico)
        IntentCategory.CORRECTION,       # Específico
        IntentCategory.ANOTHER_BRANCH,   # Específico
        IntentCategory.CLOSED,           # Específico
        IntentCategory.MANAGER_ABSENT,   # Específico
        IntentCategory.REJECT_DATA,      # Antes de OFFER_DATA
        IntentCategory.OFFER_DATA,
        IntentCategory.NO_INTEREST,      # Antes de INTEREST
        IntentCategory.FAREWELL,
        IntentCategory.IDENTITY,         # Antes de QUESTION (patrones superpuestos)
        IntentCategory.QUESTION,
        IntentCategory.TRANSFER,         # Después de CALLBACK, antes de INTEREST
        IntentCategory.INTEREST,         # Después de NO_INTEREST y TRANSFER
        IntentCategory.CONFIRMATION,     # Último (más genérico)
    ]

    def __init__(self):
        self._patterns = self._build_patterns()
        # Cache de normalizaciones para evitar re-cómputo
        self._norm_cache = {}
        self._norm_cache_max = 500

    def classify(self, texto):
        """
        Clasifica texto del cliente.

        Args:
            texto: Transcripción del cliente (raw de STT)

        Returns:
            IntentResult o None si no hay match con confianza suficiente
        """
        if not texto or not texto.strip():
            return None

        texto_norm = self._normalize(texto)

        if not texto_norm:
            return None

        # Paso 1: Exact match (rápido)
        result = self._exact_match(texto_norm)
        if result:
            return result

        # Paso 2: Fuzzy match (solo si exact falló)
        result = self._fuzzy_match(texto_norm)
        if result:
            return result

        return None

    def classify_callback_vs_transfer(self, texto):
        """
        Clasificación específica: ¿es callback o transfer?
        Útil para servidor_llamadas.py antes de frases_espera_cliente.

        Returns:
            IntentResult con CALLBACK o TRANSFER, o None
        """
        if not texto or not texto.strip():
            return None

        texto_norm = self._normalize(texto)

        # Primero verificar callback (tiene prioridad sobre transfer)
        for pattern in self._patterns.get(IntentCategory.CALLBACK, []):
            if pattern in texto_norm:
                return IntentResult(IntentCategory.CALLBACK, 1.0, pattern, 'exact')

        # Luego verificar transfer
        for pattern in self._patterns.get(IntentCategory.TRANSFER, []):
            if pattern in texto_norm:
                return IntentResult(IntentCategory.TRANSFER, 1.0, pattern, 'exact')

        # Fuzzy solo para callback (más importante evitar false positive transfer)
        for pattern in self._patterns.get(IntentCategory.CALLBACK, []):
            score = self._similarity(texto_norm, pattern)
            if score >= 0.85:  # Threshold más alto para callback vs transfer
                return IntentResult(IntentCategory.CALLBACK, score, pattern, 'fuzzy')

        return None

    def _exact_match(self, texto_norm):
        """Busca match exacto (substring) en patrones, iterando en orden de prioridad."""
        for category in self.PRIORITY_ORDER:
            patterns = self._patterns.get(category, [])
            for pattern in patterns:
                if pattern in texto_norm:
                    return IntentResult(category, 1.0, pattern, 'exact')
        return None

    def _fuzzy_match(self, texto_norm):
        """Busca match fuzzy usando SequenceMatcher, iterando en orden de prioridad."""
        best_result = None
        best_score = 0.0

        # Extraer segmentos del texto para comparar
        # (evita que un texto largo tenga score bajo contra patrón corto)
        palabras = texto_norm.split()
        segmentos = [texto_norm]  # Texto completo

        # Generar ventanas de 2-6 palabras para matching parcial
        for window_size in range(2, min(7, len(palabras) + 1)):
            for i in range(len(palabras) - window_size + 1):
                segmento = ' '.join(palabras[i:i + window_size])
                segmentos.append(segmento)

        for category in self.PRIORITY_ORDER:
            patterns = self._patterns.get(category, [])
            for pattern in patterns:
                for segmento in segmentos:
                    score = self._similarity(segmento, pattern)
                    if score >= self.FUZZY_THRESHOLD and score > best_score:
                        best_score = score
                        best_result = IntentResult(category, score, pattern, 'fuzzy')

        return best_result

    def _similarity(self, a, b):
        """Calcula similitud entre dos strings."""
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a, b).ratio()

    def _normalize(self, texto):
        """Normaliza texto: lowercase + strip acentos (compatible FIX 631)."""
        if not texto:
            return ""

        # Check cache
        if texto in self._norm_cache:
            return self._norm_cache[texto]

        resultado = texto.lower().strip()
        for a, b in [('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'),
                      ('ú', 'u'), ('ü', 'u'), ('ñ', 'n')]:
            resultado = resultado.replace(a, b)

        # Limpiar puntuación excesiva pero mantener ? (útil para detección de preguntas)
        resultado = re.sub(r'[¡¿!,;:\.]', '', resultado)
        resultado = re.sub(r'\s+', ' ', resultado).strip()

        # Cache con límite
        if len(self._norm_cache) < self._norm_cache_max:
            self._norm_cache[texto] = resultado

        return resultado

    def get_patterns_for_category(self, category):
        """Retorna patrones de una categoría (útil para debugging)."""
        return list(self._patterns.get(category, []))

    def get_all_categories(self):
        """Retorna todas las categorías con conteo de patrones."""
        return {cat.value: len(patterns) for cat, patterns in self._patterns.items()}

    def _build_patterns(self):
        """
        Construye diccionario de patrones por categoría.
        Patrones normalizados (sin acentos, lowercase).
        """
        patterns = {}

        # === CALLBACK: Cliente pide llamar después ===
        patterns[IntentCategory.CALLBACK] = [
            # FIX 645: Esperar a que regrese (incluye variante STT sin 'r' final)
            'esperar a que regrese', 'esperar a que llegue', 'esperar a que venga',
            'esperar a que vuelva', 'esperar a que entre', 'esperar a que este',
            'espera a que regrese', 'espera a que llegue', 'espera a que venga',
            'espera a que vuelva', 'espera a que entre', 'espera a que este',
            'tendrias que esperar', 'tienes que esperar', 'tiene que esperar',
            'tendria que esperar', 'tendriamos que esperar',
            'habria que esperar', 'hay que esperar',
            'debe esperar', 'debes esperar', 'mejor esperar',
            'esperar hasta que', 'esperar cuando',
            # Marcar/llamar después
            'marcar mas tarde', 'llamar mas tarde', 'marcar despues', 'llamar despues',
            'volver a marcar', 'volver a llamar', 'regresar la llamada',
            'marquen mas tarde', 'llamen mas tarde', 'llame mas tarde',
            'marque mas tarde', 'marque despues', 'llame despues',
            # FIX 695: Hablar luego
            'hablar luego', 'hablar mas tarde', 'hablar despues',
            'si gusta hablar', 'si gustas hablar',
            'hableme manana', 'llame manana', 'marquen manana',
            # FIX 657: Mandar información
            'mandar la informacion', 'enviar la informacion',
            'mandar el correo', 'enviar el correo',
            'donde tiene que mandar', 'donde tiene que enviar', 'a donde manda',
            'tiene que mandar', 'tiene que enviar',
            # FIX 698: Pronombres
            'mandarme informacion', 'enviarme informacion',
            'mandame informacion', 'enviame informacion',
            'mandarme la informacion', 'enviarme la informacion',
            'si gusta mandar', 'si gusta enviar', 'si gustas mandar', 'si gustas enviar',
            'si gusta mandarme', 'si gustas mandarme',
            'si gusta enviarme', 'si gustas enviarme',
            # Variantes adicionales para fuzzy
            'puede mandarme', 'puede enviarme', 'podria mandarme', 'podria enviarme',
            'mande la informacion', 'envie la informacion',
            'mandeme informacion', 'envieme informacion',
            'nos puede mandar', 'nos puede enviar',
        ]

        # === TRANSFER: Transferir llamada / esperar en línea ===
        patterns[IntentCategory.TRANSFER] = [
            'permitame', 'permiteme', 'permiso', 'con permiso', 'con su permiso',
            'un momento', 'un momentito', 'un segundo', 'un segundito',
            'dame un momento', 'deme un momento', 'dame un segundo', 'deme un segundo',
            'espere', 'espereme', 'espera', 'esperame',
            'dejeme', 'dejame',
            'aguarde', 'aguardeme', 'aguarda', 'aguardame',
            'tantito', 'un tantito', 'ahi le', 'ahorita le', 'ahorita te',
            'voy a ver', 'dejeme ver', 'dejame ver',
            'ahorita se lo paso', 'se lo paso', 'ahorita lo paso',
            'en un momento', 'un minuto', 'un minutito',
        ]

        # === OFFER_DATA: Cliente ofrece dato ===
        patterns[IntentCategory.OFFER_DATA] = [
            # Ofrece contacto del encargado
            'te paso su telefono', 'le paso su telefono',
            'te paso su numero', 'le paso su numero',
            'te paso su cel', 'le paso su cel',
            'te doy su telefono', 'le doy su telefono',
            'te doy su numero', 'le doy su numero',
            'te doy el telefono', 'le doy el telefono',
            'te doy el numero', 'le doy el numero',
            'te paso el numero', 'le paso el numero',
            # Ofrece su propio contacto
            'te puedo pasar mi', 'le puedo pasar mi',
            'le voy a dar un correo', 'le voy a dar mi correo',
            'te voy a dar mi', 'le voy a dar mi',
            'le doy mi telefono', 'te doy mi telefono',
            'le doy mi numero', 'te doy mi numero',
            'le doy mi correo', 'te doy mi correo',
            'le paso mi', 'te paso mi',
            # Genéricos de oferta
            'te paso su', 'le paso su', 'te voy a dar', 'le voy a dar',
            'te puedo pasar', 'le puedo pasar', 'te doy el', 'le doy el',
            'aqui le va', 'ahi le va', 'apunte', 'anote',
            'quieres que te pase', 'quiere que le pase',
            # Variantes pronominales
            'pasarle el numero', 'pasarte el numero',
            'darle el numero', 'darte el numero',
        ]

        # === REJECT_DATA: Cliente rechaza dar dato ===
        patterns[IntentCategory.REJECT_DATA] = [
            'no tengo whatsapp', 'no tengo watsap', 'no tengo wasap',
            'no tengo correo', 'no tengo email', 'no tengo mail',
            'no tengo celular', 'no tengo telefono',
            'no manejo whatsapp', 'no manejo wasap', 'no manejo watsap',
            'no uso whatsapp', 'no uso wasap', 'no uso watsap',
            'solo tengo telefono', 'solo tengo el fijo',
            'nada mas tengo telefono',
            'no quiero dejar', 'no quiero dar', 'no le quiero dar',
            'no le puedo dar', 'no te puedo dar',
            'no estoy autorizado', 'no estoy autorizada',
            'no estaba autorizado', 'no estaba autorizada',
            'no me permiten', 'no nos permiten', 'no tengo autorizacion',
            'no puedo dar datos', 'no puedo dar informacion',
            'prefiero no dar', 'prefiero no dejar',
        ]

        # === FAREWELL: Despedida ===
        patterns[IntentCategory.FAREWELL] = [
            'hasta luego', 'adios', 'que le vaya bien', 'que te vaya bien',
            'buen dia', 'buenos dias', 'buenas tardes', 'buenas noches',
            'nos vemos', 'bye', 'con permiso',
            'ya esta todo', 'eso es todo', 'es todo',
            'ya no necesito nada', 'no necesito nada mas',
            'gracias por llamar', 'gracias por la llamada',
            'que tenga buen dia', 'que tenga buena tarde',
            'igualmente', 'de igual manera',
            # Cierres naturales
            'no hay ahorita', 'no tenemos ahorita',
            'habla a otra sucursal', 'llame a otra sucursal',
            # Corteses mexicanos (FIX 654/658)
            'no oiga', 'no joven', 'no muchacho', 'no senor', 'no senora',
            'no gracias joven', 'no gracias senor',
        ]

        # === INTEREST: Muestra interés ===
        patterns[IntentCategory.INTEREST] = [
            'me interesa', 'si me interesa', 'suena interesante',
            'digame', 'digame mas', 'cuenteme', 'cuenteme mas',
            'a ver digame', 'si digame',
            'platiqueme', 'explicame', 'expliqueme',
            'que tienen', 'que manejan', 'que productos',
            'si estoy interesado', 'si estoy interesada',
            'mandeme el catalogo', 'mandame el catalogo',
            'me gustaria ver', 'quiero ver',
        ]

        # === NO_INTEREST: Sin interés ===
        patterns[IntentCategory.NO_INTEREST] = [
            'no me interesa', 'no nos interesa', 'no estoy interesado',
            'no gracias', 'no necesito', 'no necesitamos',
            'estamos bien asi', 'estamos completos',
            'ya tenemos proveedor', 'ya tenemos proveedores',
            'ya compramos', 'ya tenemos', 'ya contamos con',
            'no ocupamos', 'no ocupo', 'no requerimos',
            'no por el momento', 'por el momento no',
            'dejame pensarlo', 'dejeme pensarlo',
            'lo voy a pensar', 'lo pensare',
        ]

        # === QUESTION: Pregunta directa ===
        patterns[IntentCategory.QUESTION] = [
            'que marca manejan', 'que marcas manejan', 'que marca es',
            'que venden', 'que vende', 'que productos',
            'de que se trata',
            'de donde hablan', 'de donde llaman', 'de donde son',
            'para que es', 'para que llaman', 'para que me hablan',
            'que necesitan', 'que se le ofrece', 'que se les ofrece',
            'como se llama la empresa', 'cual es el nombre',
            'que tipo de productos', 'que linea manejan',
            'tienen catalogo', 'tienen pagina', 'tienen pagina web',
            'cuanto cuesta', 'que precio', 'que precios manejan',
            'a cuanto', 'cuanto sale',
        ]

        # === ANOTHER_BRANCH: Otra sucursal ===
        patterns[IntentCategory.ANOTHER_BRANCH] = [
            'otra sucursal', 'la otra sucursal', 'las otras sucursales',
            'comunicarse con', 'comunicarme con',
            'marque a la otra', 'llame a la otra',
            'esa es otra tienda', 'esa es otra sucursal',
            'no es esta sucursal', 'sucursal equivocada',
            'directamente con', 'comunicarse directamente',
        ]

        # === CORRECTION: Corrección ===
        patterns[IntentCategory.CORRECTION] = [
            'no es lo que dije', 'no es eso', 'no es asi',
            'me equivoque', 'se equivoco', 'esta equivocado',
            'incorrecto', 'es incorrecto', 'no es correcto',
            'no es esa sucursal', 'no es esa tienda',
            'le dije otro', 'le dije otra cosa',
            'no fue lo que dije', 'no fue eso',
        ]

        # === IDENTITY: Pregunta identidad ===
        patterns[IntentCategory.IDENTITY] = [
            'quien habla', 'quien llama', 'quien es',
            'de parte de quien', 'a nombre de quien',
            'con quien hablo', 'con quien tengo el gusto',
            'quien me habla', 'quien me llama',
            'de que empresa', 'de que compania',
            'de que negocio', 'de que marca',
            'a que se dedican', 'que empresa es',
        ]

        # === CONFIRMATION: Confirmación simple ===
        patterns[IntentCategory.CONFIRMATION] = [
            'si claro', 'claro que si', 'por supuesto',
            'asi es', 'efectivamente', 'correcto',
            'afirmativo', 'exacto', 'exactamente',
            'esta bien', 'de acuerdo', 'va',
            'orale', 'sale', 'dale',
            'si senor', 'si senora', 'como no',
            'con gusto', 'con mucho gusto',
        ]

        # === CLOSED: Negocio cerrado ===
        patterns[IntentCategory.CLOSED] = [
            'estamos cerrados', 'esta cerrado', 'ya cerramos',
            'ya cerro', 'cerro la tienda', 'cerro el negocio',
            'no estamos abiertos', 'abrimos manana',
            'ya no abrimos', 'no abrimos hoy',
            'cerramos temprano', 'hoy no abrimos',
        ]

        # === MANAGER_ABSENT: Encargado no disponible ===
        patterns[IntentCategory.MANAGER_ABSENT] = [
            'no esta el encargado', 'no esta la encargada',
            'no esta el dueno', 'no esta la duena',
            'no esta el jefe', 'no esta la jefa',
            'no se encuentra', 'salio', 'salio a comer',
            'no ha llegado', 'todavia no llega',
            'esta de vacaciones', 'esta descansando',
            'esta ocupado', 'esta ocupada', 'esta en una junta',
            'esta en una reunion', 'no esta disponible',
            'llega mas tarde', 'llega en la tarde',
            'viene hasta manana', 'viene mas tarde',
            'no viene hoy', 'hoy no viene',
            'esta fuera', 'anda fuera',
        ]

        return patterns

    def get_stats(self):
        """Retorna estadísticas del clasificador para logging."""
        total = sum(len(p) for p in self._patterns.values())
        return {
            'total_patterns': total,
            'categories': len(self._patterns),
            'cache_size': len(self._norm_cache),
            'fuzzy_threshold': self.FUZZY_THRESHOLD,
            'patterns_per_category': {
                cat.value: len(patterns)
                for cat, patterns in self._patterns.items()
            }
        }
