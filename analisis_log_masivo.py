#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis de LOG masivo para detectar preguntas frecuentes
y generar caché automático de respuestas
"""

import re
from collections import Counter
import json

# LOG masivo proporcionado por el usuario
log_text = """
CLIENTE / BRUCE	MENSAJE
BRUCE	Mucho gusto, Jair. Soy Bruce W de NIOVAL. Queremos ofrecerles nuestros productos de ferretería. ¿Qué tipo de productos manejan más en su negocio y qué tamaño tiene?
CLIENTE	con Jair Zamora
BRUCE	Perfecto, ¿con quién tengo el gusto?
CLIENTE	Sí, soy yo, dígame.
BRUCE	Perfecto, ¿me lo podría comunicar por favor?
CLIENTE	Sí qué necesitaban
BRUCE	Hola, qué tal, muy buen día. Me comunico de la empresa NIOVAL con el fin de brindarles información de nuestros productos del ramo ferretero. ¿Se encuentra el encargado de compras?
CLIENTE	Qué es lo que se le ofrece?
BRUCE	Hola, qué tal, muy buen día. Me comunico de la empresa NIOVAL con el fin de brindarles información de nuestros productos del ramo ferretero. ¿Se encuentra el encargado de compras?
CLIENTE	Dígame qué necesita.
BRUCE	Hola, qué tal, muy buen día. Me comunico de la empresa NIOVAL con el fin de brindarles información de nuestros productos del ramo ferretero. ¿Se encuentra el encargado de compras?
CLIENTE	Qué marca, escala Disculpe la que manejan no la había escuchado.
CLIENTE	oc, Qué marcas reconocidas manejan
CLIENTE	oc, Qué marcas manejas
CLIENTE	OK Bueno mira Nosotros somos una ferretería mediana trabajamos Ahora sí lo que son con selladores silicón productos Pues también por ahí de ferretería brochas y demás no sé si ustedes lleguen a manejar silicones o algunos selladores.
CLIENTE	oc, Qué marca de selladores manejas
CLIENTE	Ok entonces ustedes manejan productos Truper el nio van
CLIENTE	Ok una pregunta, qué productos tú permanecen ustedes?
CLIENTE	Okay Por qué no se puede visitar su fábrica disculpe
CLIENTE	Ok hay manera de que pueda visitar su fábrica en Guadalajara
CLIENTE	De Don bueno En dónde está ubicada su fábrica disculpa?
CLIENTE	Sí también. Bueno, ustedes son distribuidores ustedes fabrican aquí en México o fabrican en algún otro lado o de dónde son sus productos?
CLIENTE	Oc Sí pero dónde están ubicados ustedes?
CLIENTE	Sí pero bueno, ustedes su marca es propia o manejan algunas otras marcas?
CLIENTE	Bueno, ustedes cómo se manejan tiene el maneja líneas de crédito o o qué nos pueden ofrecer?
CLIENTE	Sí este también en la línea de crédito Cómo la manejan o cómo sería el proceso para la línea de crédito para dar el alta.
CLIENTE	De dónde me hablas, perdón.
CLIENTE	Sí pero bueno, Qué productos, además de esos manejan.
CLIENTE	Claro, mándamelo al WhatsApp pero de chapas, Qué marcas manejan disculpan.
CLIENTE	Sí pero te pregunto usted manejan chapas ya que las chapas son interesantes para nosotros.
"""

# Extraer solo mensajes del CLIENTE
lineas = log_text.strip().split('\n')
preguntas_cliente = []

for linea in lineas:
    if linea.startswith('CLIENTE\t'):
        mensaje = linea.split('\t', 1)[1] if '\t' in linea else ''
        if mensaje and mensaje.strip():
            preguntas_cliente.append(mensaje.strip())

# Normalizar preguntas (minúsculas, sin puntuación)
def normalizar(texto):
    texto = texto.lower()
    texto = re.sub(r'[¿?¡!.,;]+', '', texto)
    texto = ' '.join(texto.split())
    return texto

preguntas_normalizadas = [normalizar(p) for p in preguntas_cliente if len(p) > 10]

# Detectar patrones frecuentes
patrones_detectados = {}

# Patrón 1: Preguntas sobre marcas
marcas_keywords = ['qué marca', 'que marca', 'cuál marca', 'cual marca', 'qué marcas', 'que marcas',
                   'marcas maneja', 'marcas tienen', 'marcas reconocidas', 'marca propia']
preguntas_marcas = [p for p in preguntas_normalizadas if any(kw in p for kw in marcas_keywords)]

# Patrón 2: Preguntas sobre ubicación
ubicacion_keywords = ['dónde está', 'donde esta', 'dónde están', 'donde estan', 'ubicado',
                      'ubicación', 'de dónde', 'de donde']
preguntas_ubicacion = [p for p in preguntas_normalizadas if any(kw in p for kw in ubicacion_keywords)]

# Patrón 3: Preguntas sobre productos
productos_keywords = ['qué productos', 'que productos', 'qué maneja', 'que maneja',
                      'qué vende', 'que vende', 'qué ofrece', 'que ofrece']
preguntas_productos = [p for p in preguntas_normalizadas if any(kw in p for kw in productos_keywords)]

# Patrón 4: Identificación
quien_keywords = ['quién', 'quien', 'con quién', 'con quien', 'su nombre', 'cómo se llama', 'como se llama']
preguntas_quien = [p for p in preguntas_normalizadas if any(kw in p for kw in quien_keywords)]

# Patrón 5: Necesidad
necesita_keywords = ['qué necesita', 'que necesita', 'qué necesitaban', 'que necesitaban',
                     'qué se le ofrece', 'que se le ofrece', 'dígame', 'digame']
preguntas_necesita = [p for p in preguntas_normalizadas if any(kw in p for kw in necesita_keywords)]

# Patrón 6: Crédito
credito_keywords = ['línea de crédito', 'linea de credito', 'crédito', 'credito', 'cómo se manejan', 'como se manejan']
preguntas_credito = [p for p in preguntas_normalizadas if any(kw in p for kw in credito_keywords)]

# Patrón 7: Chapas específicas
chapas_keywords = ['chapas', 'manejan chapas']
preguntas_chapas = [p for p in preguntas_normalizadas if any(kw in p for kw in chapas_keywords)]

# Patrón 8: Selladores/silicones
selladores_keywords = ['selladores', 'silicones', 'silicón', 'silicon']
preguntas_selladores = [p for p in preguntas_normalizadas if any(kw in p for kw in selladores_keywords)]

# Contar frecuencias
print("="*80)
print("ANÁLISIS DE PREGUNTAS FRECUENTES - LOG MASIVO")
print("="*80)
print(f"\nTotal de mensajes del cliente analizados: {len(preguntas_cliente)}")
print(f"Preguntas procesadas (>10 caracteres): {len(preguntas_normalizadas)}\n")

print("-"*80)
print("CATEGORÍAS DETECTADAS (ordenadas por frecuencia):")
print("-"*80)

categorias = {
    "Preguntas sobre MARCAS": preguntas_marcas,
    "Preguntas sobre QUÉ NECESITA/OFRECE": preguntas_necesita,
    "Preguntas sobre PRODUCTOS que manejan": preguntas_productos,
    "Preguntas sobre UBICACIÓN": preguntas_ubicacion,
    "Preguntas sobre IDENTIFICACIÓN (quién habla)": preguntas_quien,
    "Preguntas sobre CRÉDITO": preguntas_credito,
    "Preguntas sobre CHAPAS específicas": preguntas_chapas,
    "Preguntas sobre SELLADORES/SILICONES": preguntas_selladores,
}

for nombre, lista in sorted(categorias.items(), key=lambda x: len(x[1]), reverse=True):
    print(f"\n{nombre}: {len(lista)} veces")
    if lista:
        # Mostrar las 3 primeras como ejemplos
        for ej in lista[:3]:
            print(f"  - \"{ej}\"")
        if len(lista) > 3:
            print(f"  ... y {len(lista)-3} más")

# Generar JSON de caché sugerido
print("\n" + "="*80)
print("CACHÉ SUGERIDO PARA respuestas_cache.json:")
print("="*80)

cache_sugerido = {
    "que_marcas": {
        "patrones": [
            "qué marcas", "que marcas", "cuáles marcas", "cuales marcas",
            "qué marca", "que marca", "cuál marca", "cual marca",
            "marcas maneja", "marcas tienen", "marcas reconocidas",
            "marca propia", "de qué marca", "de que marca"
        ],
        "respuesta": "Manejamos la marca NIOVAL, que es nuestra marca propia. Al ser marca propia ofrecemos mejores precios. ¿Se encuentra el encargado de compras para platicarle más a detalle?"
    },

    "que_necesita": {
        "patrones": [
            "qué necesita", "que necesita", "qué necesitaban", "que necesitaban",
            "qué se le ofrece", "que se le ofrece", "qué ofrece", "que ofrece",
            "dígame", "digame", "qué necesito", "que necesito"
        ],
        "respuesta": "Mi nombre es Bruce W, le llamo de NIOVAL. Somos distribuidores especializados en productos de ferretería. Queremos ofrecerle información sobre nuestros productos. ¿Se encuentra el encargado de compras?"
    },

    "de_donde_habla": {
        "patrones": [
            "de dónde", "de donde", "dónde están", "donde están",
            "ubicados", "ubicación", "dónde está", "donde esta",
            "de qué ciudad", "de que ciudad", "de dónde son", "de donde son"
        ],
        "respuesta": "Estamos ubicados en Guadalajara, Jalisco, pero hacemos envíos a toda la República Mexicana. ¿Se encuentra el encargado de compras?"
    },

    "que_productos": {
        "patrones": [
            "qué productos", "que productos", "qué maneja", "que maneja",
            "qué vende", "que vende", "productos manejan", "qué ofrece", "que ofrece"
        ],
        "respuesta": "Distribuimos productos de ferretería: cinta para goteras, griferías, herramientas, candados y más de 15 categorías. ¿Se encuentra el encargado de compras?"
    },

    "linea_credito": {
        "patrones": [
            "línea de crédito", "linea de credito", "crédito", "credito",
            "cómo se manejan", "como se manejan", "qué nos pueden ofrecer", "que nos pueden ofrecer"
        ],
        "respuesta": "Sí, ofrecemos línea de crédito para clientes recurrentes. También aceptamos pago con tarjeta sin comisión y ofrecemos envío gratis desde cinco mil pesos. ¿Le gustaría que le envíe más información por WhatsApp?"
    },

    "selladores_silicones": {
        "patrones": [
            "selladores", "silicones", "silicón", "silicon",
            "manejan selladores", "manejan silicones"
        ],
        "respuesta": "Déjeme validarlo con mi compañero y le confirmo en el catálogo completo. Manejamos más de 15 categorías de ferretería. ¿Le envío el catálogo por WhatsApp para que vea todo lo disponible?"
    },

    "chapas": {
        "patrones": [
            "chapas", "manejan chapas", "qué chapas", "que chapas",
            "modelos de chapas"
        ],
        "respuesta": "Déjeme validarlo en nuestro catálogo actualizado. Contamos con varias opciones de chapas. ¿Le envío el catálogo completo por WhatsApp para que vea todos los modelos disponibles?"
    }
}

print(json.dumps(cache_sugerido, ensure_ascii=False, indent=2))

# Guardar en archivo
with open('cache_sugerido.json', 'w', encoding='utf-8') as f:
    json.dump(cache_sugerido, f, ensure_ascii=False, indent=2)

print("\n✅ Archivo generado: cache_sugerido.json")
print("\n📊 RESUMEN:")
print(f"  - {len(cache_sugerido)} categorías nuevas detectadas")
print(f"  - Total de {sum(len(v['patrones']) for v in cache_sugerido.values())} patrones únicos")
print(f"  - Cobertura estimada: ~{len(preguntas_normalizadas)} preguntas del LOG")
