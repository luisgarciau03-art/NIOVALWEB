# -*- coding: utf-8 -*-
"""
FASE 2.1: GPT-4o-mini Intent Classifier

Clasificador de intenciones basado en GPT-4o-mini como fallback cuando
el pattern matching basado en regex (FIX 701) falla o es invalidado.

Arquitectura:
  - Input: transcripción cliente + último mensaje Bruce + estado conversación
  - Output: intent + confidence + acción sugerida
  - Cache en memoria: misma transcripción = mismo resultado
  - Costo: ~$0.0001 por clasificación (~$0.50-1.00/día)

Integración:
  - Si patron_detectado != None → usar patrón (rápido, sin costo)
  - Si patron_detectado == None → GPT-4o-mini clasifica (50-100ms extra)
  - NO reemplaza pattern matching, lo complementa
"""

import os
import time
import json

# Cache en memoria para evitar llamadas repetidas
_intent_cache = {}
_CACHE_MAX_SIZE = 500
_CACHE_TTL_S = 300  # 5 minutos

# Intenciones que el clasificador puede detectar
INTENTS = {
    'ENCARGADO_NO_ESTA': 'El encargado/dueño no está disponible ahora',
    'ACEPTA_CONTACTO': 'Cliente acepta dar WhatsApp, correo o teléfono',
    'RECHAZA_CONTACTO': 'Cliente no quiere dar datos de contacto',
    'VERIFICACION_CONEXION': 'Cliente verifica que la línea sigue activa (¿Bueno?, ¿Sí?, Mande)',
    'DESPEDIDA': 'Cliente quiere terminar la llamada',
    'TRANSFERENCIA': 'Cliente va a pasar la llamada a otra persona',
    'CALLBACK': 'Cliente sugiere llamar en otro momento',
    'PREGUNTA': 'Cliente pregunta sobre productos/empresa/Bruce',
    'DICTANDO_DATO': 'Cliente está dictando un número, correo o dato',
    'CONTINUACION': 'Cliente sigue hablando (frase incompleta)',
    'CONFIRMACION': 'Cliente confirma algo (sí, claro, ok, de acuerdo)',
    'RECHAZO': 'Cliente rechaza la propuesta (no me interesa, no gracias)',
    'OTRA_SUCURSAL': 'Cliente dice que no es la sucursal correcta o sugiere otra',
    'OFRECE_DATO': 'Cliente ofrece voluntariamente un dato (te paso su número, anote)',
    'CLIENTE_ES_ENCARGADO': 'La persona que contesta es el encargado/dueño',
    'SALUDO': 'Cliente saluda (hola, buenas tardes)',
    'AMBIGUO': 'No se puede determinar la intención con confianza',
}

_SYSTEM_PROMPT = """Eres un clasificador de intenciones para llamadas de ventas B2B de ferretería en México.

CONTEXTO: Bruce es un agente de ventas que llama a ferreterías para vender productos de la marca NIOVAL.
Las llamadas son en español mexicano coloquial.

MODISMOS MEXICANOS IMPORTANTES:
- "¿Sí, bueno?" / "¿Bueno?" = verificación de conexión telefónica (NO es interés)
- "No, joven" / "No, muchacho" = rechazo cortés (NO es agresión)
- "Oiga" / "Mire" = llamar la atención (NO es queja)
- "Ahí le encargo" = despedida informal
- "Qué cree" = introducción a información
- "Fíjese que" = introducción a explicación
- "Mande" / "¿Mande?" = "no escuché, repita" (NO es comando)
- "Ándale" / "Sale" = confirmación informal

INTENCIONES POSIBLES:
- ENCARGADO_NO_ESTA: El encargado no está disponible
- ACEPTA_CONTACTO: Cliente acepta dar WhatsApp/correo/teléfono
- RECHAZA_CONTACTO: Cliente no quiere dar datos
- VERIFICACION_CONEXION: "¿Bueno?", "¿Sí?", "Mande" = verifican línea activa
- DESPEDIDA: Cliente quiere terminar la llamada
- TRANSFERENCIA: Cliente va a pasar la llamada a otra persona ("espere un momento")
- CALLBACK: Cliente sugiere llamar en otro momento ("marque más tarde")
- PREGUNTA: Cliente pregunta sobre productos/empresa
- DICTANDO_DATO: Cliente está dictando un número/correo
- CONTINUACION: Frase incompleta, cliente sigue hablando
- CONFIRMACION: Cliente confirma ("sí", "claro", "ok")
- RECHAZO: No le interesa ("no me interesa", "no gracias")
- OTRA_SUCURSAL: No es la sucursal correcta
- OFRECE_DATO: Cliente ofrece dato voluntariamente ("te paso su número")
- CLIENTE_ES_ENCARGADO: La persona ES el encargado ("yo soy el encargado")
- SALUDO: Saludo ("hola", "buenas tardes")
- AMBIGUO: No se puede determinar

Responde SOLO en formato JSON:
{"intent": "NOMBRE_INTENT", "confidence": 0.0-1.0, "action": "descripción breve de acción sugerida"}"""

_FEW_SHOT_EXAMPLES = [
    {"role": "user", "content": 'Cliente: "¿Sí, bueno?"\nÚltimo Bruce: (primer contacto)\nEstado: inicio'},
    {"role": "assistant", "content": '{"intent": "VERIFICACION_CONEXION", "confidence": 0.95, "action": "Dar saludo + pitch inicial"}'},
    {"role": "user", "content": 'Cliente: "No, no está, salió a comer"\nÚltimo Bruce: "¿Se encontrará el encargado de compras?"\nEstado: buscando_encargado'},
    {"role": "assistant", "content": '{"intent": "ENCARGADO_NO_ESTA", "confidence": 0.95, "action": "Preguntar horario de regreso o pedir callback"}'},
    {"role": "user", "content": 'Cliente: "Sí, mándamelo por WhatsApp"\nÚltimo Bruce: "¿Le puedo enviar el catálogo?"\nEstado: ofreciendo_catalogo'},
    {"role": "assistant", "content": '{"intent": "ACEPTA_CONTACTO", "confidence": 0.95, "action": "Pedir número de WhatsApp"}'},
    {"role": "user", "content": 'Cliente: "No, muchacho, no nos interesa"\nÚltimo Bruce: pitch de productos\nEstado: pitch'},
    {"role": "assistant", "content": '{"intent": "RECHAZO", "confidence": 0.90, "action": "Ofrecer enviar catálogo sin compromiso, despedida cortés"}'},
    {"role": "user", "content": 'Cliente: "Espéreme tantito, ahorita le paso"\nÚltimo Bruce: "¿Se encontrará el encargado?"\nEstado: buscando_encargado'},
    {"role": "assistant", "content": '{"intent": "TRANSFERENCIA", "confidence": 0.95, "action": "Esperar transferencia, modo ESPERANDO_TRANSFERENCIA"}'},
    {"role": "user", "content": 'Cliente: "Llámeme mañana como a las 10"\nÚltimo Bruce: "¿A qué hora lo puedo encontrar?"\nEstado: buscando_encargado'},
    {"role": "assistant", "content": '{"intent": "CALLBACK", "confidence": 0.95, "action": "Registrar callback mañana 10:00, confirmar y despedirse"}'},
    {"role": "user", "content": 'Cliente: "Tres tres uno dos"\nÚltimo Bruce: "¿Me da su WhatsApp?"\nEstado: capturando_contacto'},
    {"role": "assistant", "content": '{"intent": "DICTANDO_DATO", "confidence": 0.95, "action": "Continuar escuchando dígitos, no interrumpir"}'},
    {"role": "user", "content": 'Cliente: "Yo soy el encargado, dígame"\nÚltimo Bruce: "¿Se encontrará el encargado?"\nEstado: buscando_encargado'},
    {"role": "assistant", "content": '{"intent": "CLIENTE_ES_ENCARGADO", "confidence": 0.95, "action": "Dar pitch completo al encargado"}'},
]


def classify_intent(transcripcion_cliente, ultimo_bruce="", estado="", call_sid=""):
    """
    Clasifica la intención del cliente usando GPT-4o-mini.

    Args:
        transcripcion_cliente: Texto del cliente
        ultimo_bruce: Último mensaje de Bruce
        estado: Estado actual de la conversación
        call_sid: ID de la llamada (para logging)

    Returns:
        dict con {intent, confidence, action} o None si falla
    """
    if not transcripcion_cliente or not transcripcion_cliente.strip():
        return None

    # Cache check
    cache_key = f"{transcripcion_cliente.strip().lower()}|{ultimo_bruce[:50]}|{estado}"
    now = time.time()
    if cache_key in _intent_cache:
        cached_time, cached_result = _intent_cache[cache_key]
        if now - cached_time < _CACHE_TTL_S:
            print(f"   [GPT_INTENT] Cache hit: {cached_result.get('intent', 'N/A')}")
            return cached_result

    # Build user message
    user_msg = f'Cliente: "{transcripcion_cliente.strip()}"\n'
    if ultimo_bruce:
        user_msg += f'Último Bruce: "{ultimo_bruce[:100]}"\n'
    if estado:
        user_msg += f'Estado: {estado}'

    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            print(f"   [GPT_INTENT] ERROR: No OPENAI_API_KEY")
            return None

        client = OpenAI(api_key=api_key)

        messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
        messages.extend(_FEW_SHOT_EXAMPLES)
        messages.append({"role": "user", "content": user_msg})

        t0 = time.time()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,
            max_tokens=100,
            timeout=3.0,  # Max 3s para no bloquear
        )
        elapsed = time.time() - t0

        raw = response.choices[0].message.content.strip()
        # Parse JSON
        result = json.loads(raw)

        # Validate
        if 'intent' not in result or result['intent'] not in INTENTS:
            print(f"   [GPT_INTENT] Invalid intent: {result.get('intent', 'N/A')}")
            result['intent'] = 'AMBIGUO'
            result['confidence'] = 0.3

        print(f"   [GPT_INTENT] {result['intent']} ({result.get('confidence', 0):.0%}) [{elapsed*1000:.0f}ms]")
        if call_sid:
            print(f"   [GPT_INTENT] Action: {result.get('action', 'N/A')}")

        # Cache
        if len(_intent_cache) >= _CACHE_MAX_SIZE:
            # Evict oldest
            oldest_key = min(_intent_cache, key=lambda k: _intent_cache[k][0])
            del _intent_cache[oldest_key]
        _intent_cache[cache_key] = (now, result)

        return result

    except json.JSONDecodeError as e:
        print(f"   [GPT_INTENT] JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"   [GPT_INTENT] Error: {e}")
        return None


def intent_to_pattern_type(intent):
    """
    Mapea un intent del GPT classifier a un tipo de patrón del sistema existente.
    Permite integración gradual sin cambiar el flujo existente.
    """
    mapping = {
        'ENCARGADO_NO_ESTA': 'ENCARGADO_NO_ESTA_SIN_HORARIO',
        'ACEPTA_CONTACTO': 'CLIENTE_ACEPTA_WHATSAPP',
        'RECHAZA_CONTACTO': 'RECHAZO_DEFINITIVO',
        'VERIFICACION_CONEXION': 'VERIFICACION_CONEXION',
        'DESPEDIDA': 'DESPEDIDA_CLIENTE',
        'TRANSFERENCIA': 'TRANSFERENCIA',
        'CALLBACK': 'SOLICITUD_CALLBACK',
        'PREGUNTA': 'PREGUNTA_MARCAS',
        'DICTANDO_DATO': 'CLIENTE_DICTANDO_NUMERO',
        'CONTINUACION': None,  # No mapea - dejar que GPT principal maneje
        'CONFIRMACION': 'CONFIRMACION_SIMPLE',
        'RECHAZO': 'NO_INTERESA_FINAL',
        'OTRA_SUCURSAL': 'OTRA_SUCURSAL',
        'OFRECE_DATO': 'CLIENTE_OFRECE_NUMERO',
        'CLIENTE_ES_ENCARGADO': 'CLIENTE_ES_ENCARGADO',
        'SALUDO': 'SALUDO',
        'AMBIGUO': None,  # No mapea - dejar que GPT principal maneje
    }
    return mapping.get(intent)
