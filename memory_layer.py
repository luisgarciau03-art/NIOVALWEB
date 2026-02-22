# -*- coding: utf-8 -*-
"""
FIX 699: Memory Layer - Capa de Memoria Conversacional para Bruce W

Problema: 10+ post-filters (FIX 646A, 649, 655, 658, 667A, 667B, 697A, 697B)
cada uno re-escanea conversation_history buscando los mismos hechos.
GPT no tiene acceso a hechos estructurados → repite preguntas.

Solución: Extraer hechos UNA VEZ por turno, proporcionarlos a GPT en el prompt,
y validar respuestas GPT contra hechos conocidos ANTES de enviar al cliente.

Arquitectura ADITIVA: Si este módulo falla, el código existente sigue funcionando.
"""

import re
from difflib import SequenceMatcher


class ConversationMemory:
    """
    Extrae y mantiene hechos estructurados de la conversación.
    Llamar extract_facts() una vez por turno antes de GPT.
    """

    def __init__(self):
        self.facts = {}
        self.rechazos = []
        self.datos_proporcionados = {}
        self.contexto_cliente = []
        self._last_history_len = 0

    def reset(self):
        """Resetea toda la memoria (inicio de nueva llamada)."""
        self.facts = {}
        self.rechazos = []
        self.datos_proporcionados = {}
        self.contexto_cliente = []
        self._last_history_len = 0

    def extract_facts(self, conversation_history):
        """
        Extrae hechos estructurados de conversation_history.
        Llamar UNA VEZ por turno antes de enviar a GPT.
        Escanea solo mensajes nuevos desde la última extracción para eficiencia.
        """
        if not conversation_history:
            return

        # Optimización: solo procesar mensajes nuevos
        nuevos = conversation_history[self._last_history_len:]
        self._last_history_len = len(conversation_history)

        for msg in nuevos:
            role = msg.get('role', '')
            content = msg.get('content', '')
            if not content:
                continue

            content_lower = self._normalize(content)

            if role == 'user':
                self._extract_client_facts(content_lower, content)
            elif role == 'assistant':
                self._extract_bruce_facts(content_lower, content)

    def _normalize(self, texto):
        """Normaliza texto: lowercase + strip acentos (compatible con FIX 631)."""
        texto = texto.lower().strip()
        for a, b in [('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'),
                      ('ú', 'u'), ('ü', 'u'), ('ñ', 'n')]:
            texto = texto.replace(a, b)
        return texto

    def _extract_client_facts(self, content_lower, content_original):
        """Extrae hechos de mensajes del CLIENTE."""

        # --- Encargado no disponible ---
        patrones_no_esta = [
            'no esta', 'no se encuentra', 'salio', 'no vino',
            'no ha llegado', 'no viene', 'esta de vacaciones',
            'no esta disponible', 'no se encuentra disponible',
            'no hay encargado', 'no hay nadie', 'ya se fue',
            'ya no esta', 'no esta ahorita', 'no anda'
        ]
        if any(p in content_lower for p in patrones_no_esta):
            self.facts['encargado_disponible'] = False

        # --- Encargado disponible / es el encargado ---
        patrones_es_encargado = [
            'soy yo', 'yo soy', 'si soy', 'con el habla',
            'el mismo', 'ella misma', 'servidor', 'a sus ordenes',
            'yo me encargo', 'soy el encargado', 'soy la encargada',
            'soy el dueno', 'soy la duena', 'el habla', 'aqui el'
        ]
        if any(p in content_lower for p in patrones_es_encargado):
            self.facts['es_encargado'] = True
            self.facts['encargado_disponible'] = True

        # --- Mismo número ---
        patrones_mismo = [
            'mismo numero', 'este mismo', 'es el mismo',
            'ese mismo', 'es este', 'es ese', 'al mismo'
        ]
        if any(p in content_lower for p in patrones_mismo):
            self.facts['mismo_numero'] = True
            self.contexto_cliente.append('mismo_numero')

        # --- Rechazos de datos ---
        patrones_rechazo = [
            ('no quiero dejar', 'contacto'),
            ('no te quiero dejar', 'contacto'),
            ('no le quiero dejar', 'contacto'),
            ('no puedo dar', 'contacto'),
            ('no puedo dejar', 'contacto'),
            ('no puedo proporcionar', 'contacto'),
            ('no tengo whatsapp', 'whatsapp'),
            ('no uso whatsapp', 'whatsapp'),
            ('no manejo whatsapp', 'whatsapp'),
            ('solo tengo telefono', 'whatsapp'),
            ('no tengo correo', 'email'),
            ('no uso correo', 'email'),
            ('no tengo email', 'email'),
            ('no lo tengo', 'dato_solicitado'),
            ('no cuento con eso', 'dato_solicitado'),
            ('no tengo ese dato', 'dato_solicitado'),
        ]
        for patron, tipo_rechazo in patrones_rechazo:
            if patron in content_lower:
                if tipo_rechazo not in self.rechazos:
                    self.rechazos.append(tipo_rechazo)
                self.contexto_cliente.append(f'rechazo_{tipo_rechazo}')

        # --- No autorizado ---
        patrones_no_autorizado = [
            'no estoy autorizado', 'no estaba autorizado',
            'no me permiten', 'no le permiten', 'no puedo dar informacion',
            'no nos permiten', 'no esta autorizado'
        ]
        if any(p in content_lower for p in patrones_no_autorizado):
            self.facts['cliente_no_autorizado'] = True
            if 'contacto' not in self.rechazos:
                self.rechazos.append('contacto')

        # --- Datos proporcionados: teléfono ---
        digitos = re.findall(r'\d', content_original)
        if len(digitos) >= 7:
            numero = ''.join(digitos)
            self.datos_proporcionados['telefono'] = numero

        # --- Datos proporcionados: email ---
        email_match = re.search(r'[\w.+-]+@[\w.-]+\.\w+', content_original)
        if email_match:
            self.datos_proporcionados['email'] = email_match.group()

        # Email dictado verbalmente
        if 'arroba' in content_lower and ('punto com' in content_lower or
                                           'punto' in content_lower):
            self.facts['email_dictado_verbal'] = True

        # --- Callback ---
        patrones_callback = [
            'hableme despues', 'hableme manana', 'marque mas tarde',
            'llame mas tarde', 'llame manana',
            'hablar luego', 'llamar luego', 'manana',
            'la proxima semana', 'el lunes', 'el martes', 'el miercoles',
            'el jueves', 'el viernes', 'el sabado',
            'mandarme informacion', 'enviarme informacion',
            'esperar a que regrese', 'esperar a que llegue',
            'llame a las', 'marquen a las', 'marque a las'
        ]
        if any(p in content_lower for p in patrones_callback):
            self.facts['cliente_pide_callback'] = True
            # Detectar si mencionó hora
            hora_match = re.search(r'(\d{1,2}:\d{2}|\d{1,2}\s*(am|pm|de la manana|de la tarde))',
                                   content_lower)
            if hora_match:
                self.facts['hora_callback'] = hora_match.group()
            else:
                self.facts['callback_sin_hora'] = True

        # --- Despedida ---
        patrones_despedida = [
            'hasta luego', 'adios', 'bye', 'que le vaya bien',
            'gracias por llamar', 'ya esta todo', 'es todo',
            'no gracias', 'no me interesa'
        ]
        if any(p in content_lower for p in patrones_despedida):
            self.facts['cliente_se_despide'] = True

        # --- Interés ---
        patrones_interes = [
            'si me interesa', 'me interesa', 'si claro', 'mandame',
            'enviame', 'mandeme', 'enviemelo', 'si por favor',
            'me gustaria', 'suena bien', 'suena interesante'
        ]
        if any(p in content_lower for p in patrones_interes):
            self.facts['cliente_interesado'] = True

        # --- FIX 704C: Cliente pide que Bruce repita ---
        patrones_repetir = [
            'repitame', 'repiteme', 'no le escuche', 'que me decia',
            'que decia', 'no escuche', 'puede repetir', 'otra vez'
        ]
        if any(p in content_lower for p in patrones_repetir):
            self.contexto_cliente.append('pide_repetir')

    def _extract_bruce_facts(self, content_lower, content_original):
        """Extrae hechos de mensajes de BRUCE."""

        # --- Pitch dado ---
        if 'nioval' in content_lower and any(
            p in content_lower for p in ['catalogo', 'productos', 'ferretero',
                                          'distribuidor', 'linea', 'marca']
        ):
            self.facts['pitch_dado'] = True

        # --- Encargado preguntado ---
        if any(p in content_lower for p in [
            'encargado de compras', 'encargada de compras',
            'se encuentra el encargado', 'se encontrara el encargado'
        ]):
            self.facts['encargado_preguntado'] = True

        # --- Datos solicitados ---
        if any(p in content_lower for p in [
            'whatsapp', 'numero de whatsapp', 'su whatsapp'
        ]):
            self.facts['whatsapp_solicitado'] = True

        if any(p in content_lower for p in [
            'correo', 'email', 'correo electronico'
        ]):
            self.facts['email_solicitado'] = True

        if any(p in content_lower for p in [
            'telefono fijo', 'telefono directo', 'numero directo'
        ]):
            self.facts['telefono_solicitado'] = True

        # --- Catálogo ofrecido ---
        if any(p in content_lower for p in [
            'le envio el catalogo', 'le mando el catalogo',
            'enviarle el catalogo', 'mandarle el catalogo'
        ]):
            self.facts['catalogo_ofrecido'] = True

    def get_gpt_context(self):
        """
        Retorna string con hechos conocidos para inyectar en prompt GPT.
        Formato compacto para minimizar tokens.
        """
        lines = []

        # Encargado
        if self.facts.get('es_encargado'):
            lines.append("- Hablas con el encargado de compras")
        elif self.facts.get('encargado_disponible') == False:
            lines.append("- El encargado NO esta disponible (ya lo confirmaron). NO volver a preguntar por el")

        # No autorizado
        if self.facts.get('cliente_no_autorizado'):
            lines.append("- El cliente NO esta autorizado para dar datos del encargado. NO insistir")

        # Mismo número
        if self.facts.get('mismo_numero'):
            lines.append("- El cliente indico que el encargado usa ESTE MISMO numero. NO pedir otro numero/WhatsApp")

        # Rechazos
        for rechazo in self.rechazos:
            if rechazo == 'whatsapp':
                lines.append("- El cliente rechazo dar WhatsApp. NO volver a pedir WhatsApp. Ofrecer correo o telefono fijo")
            elif rechazo == 'email':
                lines.append("- El cliente rechazo dar correo. NO volver a pedir correo")
            elif rechazo == 'contacto':
                lines.append("- El cliente rechazo dar contacto. NO insistir. Ofrecer enviar catalogo al telefono general")
            elif rechazo == 'dato_solicitado':
                lines.append("- El cliente dijo que NO tiene el dato solicitado. Ofrecer alternativa diferente")

        # Datos ya proporcionados
        if 'telefono' in self.datos_proporcionados:
            lines.append(f"- Telefono YA proporcionado: {self.datos_proporcionados['telefono']}. NO pedir de nuevo")
        if 'email' in self.datos_proporcionados:
            lines.append(f"- Email YA proporcionado: {self.datos_proporcionados['email']}. NO pedir de nuevo")

        # Callback
        if self.facts.get('cliente_pide_callback'):
            if self.facts.get('hora_callback'):
                lines.append(f"- Cliente pidio callback a las {self.facts['hora_callback']}. Confirmar hora")
            elif self.facts.get('callback_sin_hora'):
                lines.append("- Cliente pidio callback pero NO dio hora. Preguntar a que hora")

        # Pitch
        if self.facts.get('pitch_dado'):
            lines.append("- Ya presentaste NIOVAL y sus productos. NO repetir pitch completo")

        if not lines:
            return ""

        header = "[MEMORIA CONVERSACIONAL - FIX 699] Hechos conocidos de esta llamada:"
        return header + "\n" + "\n".join(lines)

    def should_block_question(self, question_type):
        """
        Retorna True si NO debemos hacer esta pregunta.

        Args:
            question_type: "whatsapp", "email", "encargado", "telefono", "contacto", "pitch"
        """
        if question_type == 'whatsapp':
            if 'whatsapp' in self.rechazos or 'contacto' in self.rechazos:
                return True
            if self.facts.get('mismo_numero'):
                return True
            if 'telefono' in self.datos_proporcionados and self.facts.get('whatsapp_solicitado'):
                return True

        elif question_type == 'email':
            if 'email' in self.rechazos or 'contacto' in self.rechazos:
                return True
            if 'email' in self.datos_proporcionados:
                return True

        elif question_type == 'encargado':
            if self.facts.get('encargado_disponible') == False:
                return True
            if self.facts.get('es_encargado'):
                return True
            if self.facts.get('encargado_preguntado') and self.facts.get('encargado_disponible') is not None:
                return True

        elif question_type == 'telefono':
            if 'telefono' in self.datos_proporcionados:
                return True

        elif question_type == 'contacto':
            if 'contacto' in self.rechazos:
                return True
            if self.facts.get('cliente_no_autorizado'):
                return True

        elif question_type == 'pitch':
            if self.facts.get('pitch_dado'):
                return True

        return False

    def validate_response(self, respuesta):
        """
        Valida respuesta GPT contra hechos conocidos.
        Retorna (ok, alternativa).
        - ok=True: respuesta es válida, enviar tal cual
        - ok=False: respuesta contradice hechos, usar alternativa
        """
        if not respuesta:
            # FIX 704A: Respuesta vacía durante dictado activo → acknowledgment
            # FIX 751: Solo email_dictado_verbal indica dictado activo real.
            # 'telefono' in datos_proporcionados es PERMANENTE post-captura y causaba
            # acknowledgment incorrecto cuando cliente ya no dictaba nada.
            dictando = self.facts.get('email_dictado_verbal')
            if dictando and not self.facts.get('cliente_se_despide'):
                return (False, "Sí, adelante.")
            return (True, "")

        resp_lower = self._normalize(respuesta)

        # --- Regla 1: No pedir WhatsApp si "mismo número" ---
        if self.facts.get('mismo_numero'):
            pide_whatsapp = any(f in resp_lower for f in [
                'whatsapp del encargado', 'whatsapp de la encargada',
                'numero del encargado', 'numero de la encargada',
                'numero directo', 'contacto del encargado'
            ])
            if pide_whatsapp:
                return (False,
                        "Perfecto, entonces le envio el catalogo a este numero. "
                        "¿Me podria confirmar el nombre del encargado?")

        # --- Regla 2: No pedir dato rechazado ---
        if self.rechazos:
            if 'whatsapp' in self.rechazos and any(f in resp_lower for f in [
                'whatsapp', 'su whats', 'numero de whatsapp'
            ]):
                return (False,
                        "¿Me podria proporcionar un correo electronico o telefono fijo entonces?")

            if 'email' in self.rechazos and any(f in resp_lower for f in [
                'correo', 'email', 'correo electronico'
            ]):
                if 'whatsapp' not in self.rechazos:
                    return (False,
                            "¿Me podria dar su WhatsApp para enviarle el catalogo?")
                else:
                    return (False,
                            "Le envio el catalogo a este numero entonces. Muchas gracias por su tiempo.")

            if 'contacto' in self.rechazos and any(f in resp_lower for f in [
                'me da su', 'me podria dar', 'me proporcion', 'tiene donde anotar'
            ]):
                return (False,
                        "Entiendo, no se preocupe. Muchas gracias por su tiempo, que tenga excelente dia.")

        # --- Regla 3: No pedir encargado si ya dijeron que no está ---
        if self.facts.get('encargado_disponible') == False:
            if any(f in resp_lower for f in [
                'se encuentra el encargado', 'se encontrara el encargado',
                'esta el encargado', 'esta la encargada',
                'me comunica con el encargado'
            ]):
                return (False,
                        "¿Me podria proporcionar un WhatsApp o correo para enviarle el catalogo al encargado?")

        # --- Regla 4: No repetir pitch si ya se dio ---
        # FIX 704C: Excepción si cliente pidió re-pitch ("repitame", "que decia")
        cliente_pide_repetir = False
        if self.contexto_cliente:
            ultimo_ctx = self.contexto_cliente[-1] if self.contexto_cliente else ''
            cliente_pide_repetir = ultimo_ctx == 'pide_repetir'

        if self.facts.get('pitch_dado') and not cliente_pide_repetir:
            # Solo bloquear si es pitch COMPLETO (nioval + producto keywords)
            tiene_nioval = 'nioval' in resp_lower
            tiene_producto = any(p in resp_lower for p in [
                'catalogo', 'productos', 'ferretero', 'distribuidor',
                'linea de productos', 'marca'
            ])
            if tiene_nioval and tiene_producto:
                # Es pitch completo repetido - bloquear
                if self.facts.get('encargado_disponible') == False:
                    return (False,
                            "¿Me podria proporcionar un WhatsApp o correo para enviarle el catalogo?")
                elif not self.facts.get('es_encargado'):
                    return (False,
                            "¿Se encontrara el encargado o encargada de compras?")

        # --- Regla 5: No insistir si no autorizado ---
        if self.facts.get('cliente_no_autorizado'):
            if any(f in resp_lower for f in [
                'me da su', 'me podria dar', 'me proporcion',
                'numero del encargado', 'contacto del encargado'
            ]):
                return (False,
                        "Entiendo. ¿Le podria enviar el catalogo a este numero entonces?")

        # --- Regla 6: No pedir dato ya proporcionado ---
        if 'telefono' in self.datos_proporcionados:
            if any(f in resp_lower for f in [
                'cual es su numero', 'me da su numero', 'su telefono',
                'numero de telefono'
            ]):
                return (False,
                        "Perfecto, ya tengo su numero registrado. Le envio el catalogo entonces.")

        if 'email' in self.datos_proporcionados:
            if any(f in resp_lower for f in [
                'me da su correo', 'su email', 'correo electronico',
                'me podria dar un correo'
            ]):
                return (False,
                        "Perfecto, ya tengo su correo registrado. Le envio el catalogo a esa direccion.")

        # --- Regla 7 (FIX 704B): Callback sin hora → preguntar hora, no contacto ---
        if self.facts.get('callback_sin_hora') and not self.facts.get('hora_callback'):
            pide_contacto = any(f in resp_lower for f in [
                'whatsapp', 'correo', 'email', 'numero del encargado',
                'numero directo', 'me proporciona', 'me da su'
            ])
            if pide_contacto:
                return (False,
                        "¿A que hora me recomienda llamar para encontrar al encargado?")

        return (True, "")

    def get_summary(self):
        """Retorna resumen de memoria para debug/logging."""
        return {
            'facts': dict(self.facts),
            'rechazos': list(self.rechazos),
            'datos': dict(self.datos_proporcionados),
            'contexto': list(self.contexto_cliente)
        }
