"""
FIX 519: Sistema de Auto-Aprendizaje de Patrones
Guarda transcripciones no reconocidas y aprende nuevos patrones automáticamente.

Similar al cache de audios, pero para patrones de texto.
"""

import json
import os
import re
from datetime import datetime
from collections import Counter
from typing import Optional, Dict, List

class CachePatronesAprendidos:
    """
    Cache que guarda transcripciones no reconocidas y aprende patrones.

    Flujo:
    1. Cuando una transcripción NO matchea ningún patrón → se guarda aquí
    2. Se registra qué tipo de respuesta dio GPT (pedir contacto, despedirse, etc.)
    3. Si el mismo patrón aparece N veces con la misma respuesta → se sugiere agregar
    """

    # Archivo de cache persistente
    CACHE_FILE = "cache_patrones_aprendidos.json"

    # Número mínimo de ocurrencias para sugerir un patrón
    MIN_OCURRENCIAS_SUGERIR = 3

    # Categorías de respuestas para clasificar
    CATEGORIAS_RESPUESTA = {
        "PIDE_CONTACTO": ["whatsapp", "correo", "número", "contacto", "6624151997"],
        "CALLBACK": ["llamo más tarde", "qué hora", "horario", "vuelvo a llamar"],
        "DESPEDIDA": ["gracias por su tiempo", "excelente día", "hasta luego"],
        "ENCARGADO_NO_ESTA": ["no está", "no se encuentra", "más tarde"],
        "CONFIRMACION": ["perfecto", "entendido", "claro"],
        "PEDIR_WHATSAPP": ["whatsapp del encargado", "proporcionar el whatsapp"],
        "PEDIR_CORREO": ["correo electrónico", "email"],
    }

    def __init__(self, directorio_cache: str = None):
        """Inicializa el cache de patrones."""
        if directorio_cache:
            self.cache_file = os.path.join(directorio_cache, self.CACHE_FILE)
        else:
            # Usar directorio del script
            self.cache_file = os.path.join(os.path.dirname(__file__), self.CACHE_FILE)

        self.cache = self._cargar_cache()
        print(f" FIX 519: Cache de patrones inicializado ({len(self.cache.get('patrones', {}))} patrones guardados)")

    def _cargar_cache(self) -> Dict:
        """Carga el cache desde disco."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"   [WARN] Error cargando cache de patrones: {e}")

        # Cache vacío por defecto
        return {
            "patrones": {},  # {texto_normalizado: {categoria, count, ejemplos[], ultima_vez}}
            "sugerencias": [],  # Patrones listos para agregar al código
            "estadisticas": {
                "total_guardados": 0,
                "total_sugeridos": 0,
                "ultima_actualizacion": None
            }
        }

    def _guardar_cache(self):
        """Guarda el cache a disco."""
        try:
            self.cache["estadisticas"]["ultima_actualizacion"] = datetime.now().isoformat()
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"   [WARN] Error guardando cache de patrones: {e}")

    def _normalizar_texto(self, texto: str) -> str:
        """
        Normaliza el texto para encontrar patrones similares.
        Elimina números, puntuación excesiva, y normaliza espacios.
        """
        texto = texto.lower().strip()
        # Eliminar números de teléfono (secuencias de dígitos)
        texto = re.sub(r'\d{7,}', '[TELEFONO]', texto)
        # Eliminar emails
        texto = re.sub(r'[\w.-]+@[\w.-]+\.\w+', '[EMAIL]', texto)
        # Normalizar espacios
        texto = re.sub(r'\s+', ' ', texto)
        # Eliminar puntuación repetida
        texto = re.sub(r'[.,!?]+', '', texto)
        return texto.strip()

    def _detectar_categoria(self, respuesta_bruce: str) -> str:
        """Detecta la categoría de la respuesta de Bruce."""
        respuesta_lower = respuesta_bruce.lower()

        for categoria, palabras_clave in self.CATEGORIAS_RESPUESTA.items():
            if any(palabra in respuesta_lower for palabra in palabras_clave):
                return categoria

        return "OTRO"

    def _extraer_patron_clave(self, texto: str) -> str:
        """
        Extrae las palabras clave del texto para formar un patrón.
        Elimina artículos, preposiciones comunes, etc.
        """
        palabras_ignorar = {
            'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
            'de', 'del', 'al', 'a', 'en', 'con', 'por', 'para',
            'que', 'qué', 'como', 'cómo', 'donde', 'dónde',
            'es', 'son', 'está', 'están', 'hay',
            'me', 'te', 'se', 'le', 'lo', 'nos', 'les',
            'mi', 'tu', 'su', 'mis', 'tus', 'sus',
            'y', 'o', 'pero', 'si', 'no', 'sí',
            'muy', 'más', 'menos', 'tan', 'tanto',
        }

        palabras = texto.lower().split()
        palabras_clave = [p for p in palabras if p not in palabras_ignorar and len(p) > 2]

        # Tomar las primeras 5 palabras clave
        return ' '.join(palabras_clave[:5])

    def registrar_transcripcion_no_reconocida(
        self,
        texto_cliente: str,
        respuesta_bruce: str,
        bruce_id: str = None,
        contexto: str = None
    ):
        """
        Registra una transcripción que no fue reconocida por ningún patrón.

        Args:
            texto_cliente: Lo que dijo el cliente (transcripción Deepgram)
            respuesta_bruce: Lo que respondió Bruce (GPT)
            bruce_id: ID de la llamada para referencia
            contexto: Contexto adicional (ej: "después de pedir encargado")
        """
        if not texto_cliente or len(texto_cliente) < 5:
            return

        texto_normalizado = self._normalizar_texto(texto_cliente)
        patron_clave = self._extraer_patron_clave(texto_cliente)
        categoria = self._detectar_categoria(respuesta_bruce)

        # Usar patrón clave como key (agrupa variantes similares)
        if patron_clave not in self.cache["patrones"]:
            self.cache["patrones"][patron_clave] = {
                "categoria": categoria,
                "count": 0,
                "ejemplos": [],
                "respuestas_bruce": [],
                "ultima_vez": None,
                "bruce_ids": []
            }

        patron = self.cache["patrones"][patron_clave]
        patron["count"] += 1
        patron["ultima_vez"] = datetime.now().isoformat()

        # Guardar ejemplo (máximo 5)
        if len(patron["ejemplos"]) < 5:
            if texto_cliente not in patron["ejemplos"]:
                patron["ejemplos"].append(texto_cliente)

        # Guardar respuesta de Bruce (máximo 3)
        if len(patron["respuestas_bruce"]) < 3:
            if respuesta_bruce not in patron["respuestas_bruce"]:
                patron["respuestas_bruce"].append(respuesta_bruce[:100])

        # Guardar BRUCE ID
        if bruce_id and bruce_id not in patron["bruce_ids"]:
            patron["bruce_ids"].append(bruce_id)
            if len(patron["bruce_ids"]) > 10:
                patron["bruce_ids"] = patron["bruce_ids"][-10:]

        self.cache["estadisticas"]["total_guardados"] += 1

        # Verificar si ya es candidato para sugerir
        if patron["count"] >= self.MIN_OCURRENCIAS_SUGERIR:
            self._agregar_sugerencia(patron_clave, patron)

        # Guardar cada 10 registros
        if self.cache["estadisticas"]["total_guardados"] % 10 == 0:
            self._guardar_cache()

        print(f"   FIX 519: Patrón guardado '{patron_clave[:30]}...' (count={patron['count']}, cat={categoria})")

    def _agregar_sugerencia(self, patron_clave: str, patron: Dict):
        """Agrega un patrón a las sugerencias si cumple criterios."""
        # Verificar si ya está en sugerencias
        for sug in self.cache["sugerencias"]:
            if sug["patron_clave"] == patron_clave:
                sug["count"] = patron["count"]
                return

        sugerencia = {
            "patron_clave": patron_clave,
            "categoria": patron["categoria"],
            "count": patron["count"],
            "ejemplos": patron["ejemplos"][:3],
            "respuesta_sugerida": patron["respuestas_bruce"][0] if patron["respuestas_bruce"] else None,
            "codigo_sugerido": self._generar_codigo_patron(patron_clave, patron),
            "fecha_sugerencia": datetime.now().isoformat()
        }

        self.cache["sugerencias"].append(sugerencia)
        self.cache["estadisticas"]["total_sugeridos"] += 1
        print(f"   FIX 519: NUEVO PATRÓN SUGERIDO: '{patron_clave}' ({patron['count']} ocurrencias)")

    def _generar_codigo_patron(self, patron_clave: str, patron: Dict) -> str:
        """Genera el código Python para agregar el patrón."""
        ejemplos = patron["ejemplos"][:2]
        ejemplos_str = ", ".join([f'"{ej}"' for ej in ejemplos])

        return f'''# Patrón aprendido automáticamente (FIX 519)
# Ejemplos: {ejemplos_str}
# Categoría: {patron["categoria"]}
# Ocurrencias: {patron["count"]}
"{patron_clave}",'''

    def obtener_sugerencias(self, min_count: int = None) -> List[Dict]:
        """Obtiene las sugerencias de patrones para agregar."""
        min_count = min_count or self.MIN_OCURRENCIAS_SUGERIR
        return [
            s for s in self.cache["sugerencias"]
            if s["count"] >= min_count
        ]

    def obtener_estadisticas(self) -> Dict:
        """Obtiene estadísticas del cache."""
        patrones = self.cache["patrones"]

        # Contar por categoría
        por_categoria = Counter(p["categoria"] for p in patrones.values())

        # Top 10 más frecuentes
        top_frecuentes = sorted(
            [(k, v["count"]) for k, v in patrones.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "total_patrones": len(patrones),
            "total_sugerencias": len(self.cache["sugerencias"]),
            "por_categoria": dict(por_categoria),
            "top_10_frecuentes": top_frecuentes,
            "ultima_actualizacion": self.cache["estadisticas"]["ultima_actualizacion"]
        }

    def exportar_patrones_para_codigo(self, categoria: str = None, min_count: int = 3) -> str:
        """
        Exporta los patrones aprendidos como código Python listo para copiar.

        Args:
            categoria: Filtrar por categoría (opcional)
            min_count: Mínimo de ocurrencias

        Returns:
            String con código Python para agregar al agente
        """
        patrones = self.cache["patrones"]

        lineas = [
            "# ============================================================",
            "# PATRONES APRENDIDOS AUTOMÁTICAMENTE (FIX 519)",
            f"# Exportados: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "# ============================================================",
            ""
        ]

        for patron_clave, data in sorted(patrones.items(), key=lambda x: x[1]["count"], reverse=True):
            if data["count"] < min_count:
                continue
            if categoria and data["categoria"] != categoria:
                continue

            ejemplos = data["ejemplos"][:2]
            lineas.append(f'# Categoría: {data["categoria"]} | Count: {data["count"]}')
            lineas.append(f'# Ejemplos: {ejemplos}')
            lineas.append(f'"{patron_clave}",')
            lineas.append("")

        return "\n".join(lineas)

    def limpiar_patrones_antiguos(self, dias: int = 30):
        """Elimina patrones que no se han visto en X días."""
        from datetime import timedelta

        fecha_limite = datetime.now() - timedelta(days=dias)
        patrones_eliminar = []

        for patron_clave, data in self.cache["patrones"].items():
            if data["ultima_vez"]:
                ultima = datetime.fromisoformat(data["ultima_vez"])
                if ultima < fecha_limite and data["count"] < self.MIN_OCURRENCIAS_SUGERIR:
                    patrones_eliminar.append(patron_clave)

        for patron in patrones_eliminar:
            del self.cache["patrones"][patron]

        if patrones_eliminar:
            print(f"   FIX 519: Limpiados {len(patrones_eliminar)} patrones antiguos")
            self._guardar_cache()

    def guardar(self):
        """Guarda el cache manualmente."""
        self._guardar_cache()


# Instancia global (se inicializa en el servidor)
cache_patrones = None

def inicializar_cache_patrones(directorio: str = None) -> CachePatronesAprendidos:
    """Inicializa el cache global de patrones."""
    global cache_patrones
    cache_patrones = CachePatronesAprendidos(directorio)
    return cache_patrones

def obtener_cache_patrones() -> Optional[CachePatronesAprendidos]:
    """Obtiene la instancia del cache de patrones."""
    return cache_patrones
