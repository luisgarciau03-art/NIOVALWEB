#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditoría Profunda de Logs Pre-FIX 653
Analiza si FIX 648-653 cubre TODAS las variantes de bugs detectados
"""

import re
import sys
from collections import defaultdict

ARCHIVOS_LOGS = [
    'C:\\Users\\PC 1\\AgenteVentas\\LOGS\\11_02PT11.txt',
    'C:\\Users\\PC 1\\AgenteVentas\\LOGS\\11_02PT12.txt'
]

# Bugs que FIX 648-653 debe eliminar
BUGS_TARGET = {
    'BRUCE2112': 'CLIENTE_HABLA_ULTIMO',
    'BRUCE2111': 'CLIENTE_HABLA_ULTIMO',
    'BRUCE2108': 'GPT_OPORTUNIDAD_PERDIDA',
    'BRUCE2106': 'GPT_LOGICA_ROTA + GPT_FUERA_DE_TEMA',
    'BRUCE2104': 'GPT_LOGICA_ROTA',
    'BRUCE2100': 'GPT_FUERA_DE_TEMA',
    'BRUCE2097': 'GPT_TONO_INADECUADO',
    'BRUCE2096': 'GPT_TONO_INADECUADO',
    'BRUCE2094': 'GPT_FUERA_DE_TEMA',
    'BRUCE2093': 'GPT_RESPUESTA_INCORRECTA'
}

def extraer_conversacion(archivo, bruce_id):
    """Extrae conversación completa de un BRUCE ID"""
    try:
        with open(archivo, 'r', encoding='utf-8', errors='ignore') as f:
            contenido = f.read()
    except FileNotFoundError:
        return None

    if bruce_id not in contenido:
        return None

    lineas = contenido.split('\n')

    # Encontrar línea con BRUCE ID
    inicio_idx = None
    for i, linea in enumerate(lineas):
        if bruce_id in linea:
            inicio_idx = i
            break

    if inicio_idx is None:
        return None

    # Buscar hacia atrás para encontrar inicio (webhook-voz o Iniciando saludo)
    inicio_real = max(0, inicio_idx - 200)
    for i in range(inicio_idx, inicio_real, -1):
        if 'webhook-voz' in lineas[i] or 'Iniciando saludo' in lineas[i]:
            inicio_real = i
            break

    # Extraer hasta 100 líneas después
    fin_idx = min(len(lineas), inicio_idx + 100)
    conversacion = '\n'.join(lineas[inicio_real:fin_idx])

    return conversacion

def analizar_cliente_habla_ultimo(conversacion, bruce_id):
    """Analiza BRUCE2112, BRUCE2111 - Cliente habla último"""
    print(f"\n{'='*80}")
    print(f"BRUCE {bruce_id}: CLIENTE_HABLA_ULTIMO")
    print(f"{'='*80}")

    # Extraer último mensaje del cliente
    mensajes_cliente = re.findall(r'CLIENTE[^:]*:\s*(.+)', conversacion)
    if not mensajes_cliente:
        print("  ⚠️ No se encontraron mensajes del cliente")
        return

    ultimo_cliente = mensajes_cliente[-1].strip()
    print(f"  Último mensaje cliente: \"{ultimo_cliente}\"")

    # Verificar si FIX 648 lo cubre
    patrones_fix648 = [
        "no hay ahorita", "no hay en esta hora", "no hay nadie",
        "tienes que hablar a", "tiene que llamar a", "contacta a",
        "habla a la sucursal", "marca a la sucursal",
        "no hay encargado", "no tenemos encargado",
        "solo soy yo", "yo nada mas", "yo solo", "estoy solo", "estoy sola"
    ]

    ultimo_lower = ultimo_cliente.lower()
    matcheado = False
    for patron in patrones_fix648:
        if patron in ultimo_lower:
            print(f"  ✅ CUBIERTO por FIX 648: Pattern '{patron}'")
            matcheado = True
            break

    if not matcheado:
        print(f"  ❌ NO CUBIERTO: Necesita agregar pattern")
        print(f"     Sugerencia: Agregar \"{ultimo_cliente.lower()}\" a FIX 648")

    return matcheado

def analizar_gpt_tono_inadecuado(conversacion, bruce_id):
    """Analiza BRUCE2097, BRUCE2096 - Timeout GPT"""
    print(f"\n{'='*80}")
    print(f"BRUCE {bruce_id}: GPT_TONO_INADECUADO")
    print(f"{'='*80}")

    # Buscar mensajes de "problemas técnicos"
    if 'problemas técnicos' in conversacion or 'problemas tecn' in conversacion.lower():
        print("  ✅ TIMEOUT GPT detectado")

        # Verificar si tiene el mensaje viejo
        if 'Lo siento, estoy teniendo problemas técnicos' in conversacion:
            print("  📋 Mensaje viejo encontrado (será reemplazado por FIX 651)")
            return True
        else:
            print("  ⚠️ Mensaje diferente de timeout")
            return False

    print("  ❌ No se encontró timeout GPT en este caso")
    return False

def analizar_gpt_logica_rota(conversacion, bruce_id):
    """Analiza BRUCE2106, BRUCE2104 - Pidió dato ya proporcionado"""
    print(f"\n{'='*80}")
    print(f"BRUCE {bruce_id}: GPT_LOGICA_ROTA")
    print(f"{'='*80}")

    # Buscar turnos Bruce
    turnos_bruce = re.findall(r'BRUCE[^:]*:\s*(.+)', conversacion)
    turnos_cliente = re.findall(r'CLIENTE[^:]*:\s*(.+)', conversacion)

    print(f"  Turnos Bruce: {len(turnos_bruce)}")
    print(f"  Turnos Cliente: {len(turnos_cliente)}")

    # Buscar patrones indirectos en mensajes cliente
    patrones_indirectos = [
        r'llame al \d+',
        r'puede marcar al \d+',
        r'el número es \d+',
        r'contacte al \d+',
        r'te paso (?:el|su) \d+'
    ]

    for i, turno_cliente in enumerate(turnos_cliente):
        for patron in patrones_indirectos:
            if re.search(patron, turno_cliente.lower()):
                print(f"  📞 Turno {i+1} cliente dio número INDIRECTO: \"{turno_cliente}\"")
                print(f"     Pattern: {patron}")
                print(f"  ✅ CUBIERTO por FIX 649 (formas indirectas)")
                return True

    print("  ⚠️ No se encontró forma indirecta clara")
    return False

def analizar_gpt_oportunidad_perdida(conversacion, bruce_id):
    """Analiza BRUCE2108 - No pidió contacto alternativo"""
    print(f"\n{'='*80}")
    print(f"BRUCE {bruce_id}: GPT_OPORTUNIDAD_PERDIDA")
    print(f"{'='*80}")

    # Buscar si cliente dijo que encargado no está
    patrones_no_esta = [
        'no está', 'no esta', 'no se encuentra',
        'no puede', 'no esta disponible', 'no está disponible'
    ]

    conversacion_lower = conversacion.lower()
    encargado_no_disponible = any(p in conversacion_lower for p in patrones_no_esta)

    if encargado_no_disponible:
        print("  📋 Encargado NO DISPONIBLE detectado")

        # Verificar si Bruce pidió contacto alternativo
        pidio_contacto = any(p in conversacion_lower for p in ['whatsapp', 'correo', 'teléfono', 'telefono', 'número', 'numero'])

        if pidio_contacto:
            print("  ✅ Bruce SÍ pidió contacto alternativo")
        else:
            print("  ❌ Bruce NO pidió contacto (será corregido por FIX 652 regla #5)")
            return True

    return False

def main():
    print("="*80)
    print(" AUDITORÍA PROFUNDA - FIX 648-653 Coverage Analysis")
    print("="*80)
    print("\nAnaliza si FIX 648-653 cubre TODAS las variantes de bugs detectados\n")

    resultados = defaultdict(lambda: {'cubierto': 0, 'no_cubierto': 0})

    for bug_id, bug_tipo in BUGS_TARGET.items():
        conversacion = None

        for archivo in ARCHIVOS_LOGS:
            conversacion = extraer_conversacion(archivo, bug_id)
            if conversacion:
                break

        if not conversacion:
            print(f"\n⚠️ {bug_id} no encontrado en logs")
            continue

        # Analizar según tipo
        if 'CLIENTE_HABLA_ULTIMO' in bug_tipo:
            cubierto = analizar_cliente_habla_ultimo(conversacion, bug_id)
        elif 'GPT_TONO_INADECUADO' in bug_tipo:
            cubierto = analizar_gpt_tono_inadecuado(conversacion, bug_id)
        elif 'GPT_LOGICA_ROTA' in bug_tipo:
            cubierto = analizar_gpt_logica_rota(conversacion, bug_id)
        elif 'GPT_OPORTUNIDAD_PERDIDA' in bug_tipo:
            cubierto = analizar_gpt_oportunidad_perdida(conversacion, bug_id)
        else:
            cubierto = False

        tipo_principal = bug_tipo.split(' + ')[0]  # Solo primer tipo
        if cubierto:
            resultados[tipo_principal]['cubierto'] += 1
        else:
            resultados[tipo_principal]['no_cubierto'] += 1

    # Resumen
    print(f"\n{'='*80}")
    print(" RESUMEN DE COBERTURA")
    print(f"{'='*80}\n")

    for tipo, stats in resultados.items():
        total = stats['cubierto'] + stats['no_cubierto']
        cobertura = stats['cubierto'] / total * 100 if total > 0 else 0
        print(f"{tipo}:")
        print(f"  Cubiertos: {stats['cubierto']}/{total} ({cobertura:.1f}%)")
        print(f"  No cubiertos: {stats['no_cubierto']}/{total}")
        print()

if __name__ == '__main__':
    main()
