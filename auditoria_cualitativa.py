#!/usr/bin/env python3
"""
Auditoría Cualitativa de Conversaciones Bruce W
================================================
Extrae conversaciones de logs Railway y evalúa:
- Calidad del saludo/pitch
- Fluidez conversacional
- Tasa de captura de contacto
- Manejo de objeciones
- Naturalidad del idioma
- Áreas de mejora en comportamiento

Uso:
    python auditoria_cualitativa.py LOGS/04_03PT1.txt [LOGS/04_03PT2.txt ...]
    python auditoria_cualitativa.py --combined logs_04_03_combined.txt
"""
import re
import sys
import os
from collections import defaultdict

# ----------------------------------------------
# Extractor de conversaciones
# ----------------------------------------------

def extraer_conversaciones(log_text):
    """Extrae lista de conversaciones del log."""
    convs = []

    # Dividir por sesión (cada llamada tiene un ID BRUCE único)
    bloques_raw = re.split(r'(?=\[\d{4}-\d{2}-\d{2}[^\]]+\]\s+ID BRUCE generado:)', log_text)

    for bloque in bloques_raw:
        bruce_match = re.search(r'ID BRUCE generado: (BRUCE\d+)', bloque)
        if not bruce_match:
            continue

        bruce_id = bruce_match.group(1)

        # Nombre del negocio
        nombre_match = re.search(
            r'(?:Nombre del negocio|negocio)[:\s]+([^\n\[]{3,60})',
            bloque, re.IGNORECASE
        )
        nombre = nombre_match.group(1).strip() if nombre_match else "Desconocido"

        # Resultado final
        wapp_match = re.search(r'WhatsApp synced: (\d+)', bloque)
        email_match = re.search(r'Email synced: ([\w.@+]+)', bloque)
        estado_match = re.search(
            r'fsm=(\w+)\s+→\s+estado=(\w+)',
            bloque.split('ID BRUCE generado')[-1]
        )

        # Extraer turnos de conversación
        # Formato real:
        #   [CLIENTE] BRUCE2548 - CLIENTE DIJO: "..."
        #   [BRUCE] BRUCE2548 DICE: "..."
        turnos = []
        for m in re.finditer(
            r'\[(CLIENTE|BRUCE)\]\s+BRUCE\d+(?:\s+-\s+CLIENTE)?\s+(?:DIJO|DICE):\s+"(.+?)"',
            bloque, re.DOTALL
        ):
            rol = m.group(1).lower()
            texto = m.group(2).strip().replace('\n', ' ')
            turnos.append((rol, texto))

        if turnos:
            convs.append({
                'id': bruce_id,
                'nombre': nombre,
                'turnos': turnos,
                'whatsapp': wapp_match.group(1) if wapp_match else None,
                'email': email_match.group(1) if email_match else None,
                'estado_final': estado_match.group(2) if estado_match else 'desconocido',
                'n_turnos': len([t for t in turnos if t[0] == 'cliente']),
            })

    return convs


# ----------------------------------------------
# Evaluadores cualitativos
# ----------------------------------------------

def evaluar_saludo(turnos):
    """¿Bruce se presenta correctamente en el primer turno?"""
    bruce_primero = next((t for r, t in turnos if r == 'bruce'), '')
    issues = []
    positivos = []

    if 'nioval' in bruce_primero.lower():
        positivos.append("Menciona NIOVAL en el saludo")
    else:
        issues.append("NO menciona NIOVAL en el primer turno")

    if 'encargado' in bruce_primero.lower() or 'compras' in bruce_primero.lower():
        positivos.append("Pregunta por encargado/compras")
    else:
        issues.append("No pregunta por encargado en el saludo")

    if len(bruce_primero) > 200:
        issues.append(f"Saludo muy largo ({len(bruce_primero)} chars) - puede sonar a script")
    elif len(bruce_primero) < 30:
        issues.append(f"Saludo muy corto ({len(bruce_primero)} chars) - puede sonar frío")
    else:
        positivos.append(f"Longitud de saludo adecuada ({len(bruce_primero)} chars)")

    return positivos, issues


def evaluar_objeciones(turnos):
    """¿Bruce maneja bien las objeciones?"""
    issues = []
    positivos = []

    for i, (rol, texto) in enumerate(turnos):
        if rol != 'cliente':
            continue

        texto_lower = texto.lower()

        # Rechazo de datos
        if any(p in texto_lower for p in ['no tengo whatsapp', 'no tengo correo', 'no tengo', 'no manejo']):
            # Ver siguiente respuesta de Bruce
            siguiente = next(((r, t) for r, t in turnos[i+1:] if r == 'bruce'), None)
            if siguiente:
                sig_lower = siguiente[1].lower()
                if any(p in sig_lower for p in ['correo', 'whatsapp', 'telefono', 'directo']):
                    positivos.append(f"Correcto pivot tras rechazo: '{texto[:50]}'")
                elif any(p in sig_lower for p in ['entiendo', 'claro', 'perfecto']):
                    issues.append(f"Solo acknowledges rechazo sin pivot: '{siguiente[1][:60]}'")

        # Cliente pide repetir/no entendió
        if any(p in texto_lower for p in ['no entendí', 'mande', 'perdón', 'cómo', 'qué dijo']):
            siguiente = next(((r, t) for r, t in turnos[i+1:] if r == 'bruce'), None)
            if siguiente and len(siguiente[1]) > 150:
                issues.append(f"Respuesta muy larga tras pedido de repetición ({len(siguiente[1])} chars)")

    return positivos, issues


def evaluar_naturalidad(turnos):
    """¿Bruce suena natural o robótico?"""
    issues = []
    positivos = []

    bruce_respuestas = [t for r, t in turnos if r == 'bruce']

    # Detectar fórmulas demasiado repetidas
    formulas = [
        ('entiendo', 3, "Usa 'Entiendo' demasiadas veces"),
        ('perfecto', 3, "Usa 'Perfecto' demasiadas veces"),
        ('le comento', 2, "Repite 'Le comento' varias veces"),
        ('muchas gracias', 3, "Repite 'Muchas gracias' varias veces"),
    ]

    for formula, umbral, mensaje in formulas:
        count = sum(1 for t in bruce_respuestas if formula in t.lower())
        if count >= umbral:
            issues.append(f"{mensaje} ({count}x)")

    # Respuestas muy largas (monólogos)
    monologos = [t for t in bruce_respuestas if len(t) > 250]
    if monologos:
        issues.append(f"{len(monologos)} respuesta(s) muy larga(s) (>250 chars) - puede interrumpir")
    else:
        positivos.append("Respuestas concisas (ninguna >250 chars)")

    # Respuestas muy cortas ante preguntas
    for i, (rol, texto) in enumerate(turnos):
        if rol != 'cliente' or '?' not in texto:
            continue
        sig = next(((r, t) for r, t in turnos[i+1:] if r == 'bruce'), None)
        if sig and len(sig[1]) < 15:
            issues.append(f"Respuesta muy corta a pregunta: '{texto[:40]}' → '{sig[1]}'")

    return positivos, issues


def evaluar_captura_contacto(conv):
    """¿Se capturó contacto? ¿Fue eficiente?"""
    positivos = []
    issues = []

    if conv['whatsapp'] or conv['email']:
        dato = conv['whatsapp'] or conv['email']
        positivos.append(f"Contacto capturado: {dato}")

        # ¿Cuántos turnos tomó?
        n_turnos = conv['n_turnos']
        if n_turnos <= 5:
            positivos.append(f"Captura eficiente ({n_turnos} turnos cliente)")
        elif n_turnos <= 10:
            positivos.append(f"Captura normal ({n_turnos} turnos cliente)")
        else:
            issues.append(f"Captura tardía - tomó {n_turnos} turnos del cliente")
    else:
        estado = conv['estado_final']
        if estado in ('despedida', 'no_interes', 'encargado_no_esta'):
            issues.append(f"Sin contacto capturado (estado: {estado})")
        else:
            issues.append(f"Sin contacto capturado (estado: {estado}) - posible oportunidad perdida")

    return positivos, issues


# ----------------------------------------------
# Análisis del prompt GPT
# ----------------------------------------------

def detectar_patrones_prompt(convs):
    """Analiza patrones de comportamiento GPT a mejorar en el prompt."""
    patrones = defaultdict(list)

    for conv in convs:
        turnos = conv['turnos']
        bruce_id = conv['id']

        for i, (rol, texto) in enumerate(turnos):
            if rol != 'bruce':
                continue
            texto_lower = texto.lower()

            # 1. Ofrece catálogo después de ya haber capturado contacto
            if 'catálogo' in texto_lower or 'catalogo' in texto_lower:
                if conv['whatsapp'] or conv['email']:
                    # Ver si ya tenía contacto antes de este turno
                    turnos_previos = turnos[:i]
                    had_contact_before = any(
                        'tengo el numero' in t.lower() or 'tengo el correo' in t.lower()
                        for _, t in turnos_previos if _ == 'bruce'
                    )
                    if had_contact_before:
                        patrones['CATALOGO_POST_CAPTURA'].append(f"{bruce_id}: '{texto[:60]}'")

            # 2. Bruce da información técnica que no le pidieron
            if any(p in texto_lower for p in ['categorias', 'herramientas', 'griferia', 'candados', 'cintas']):
                cliente_pregunto = i > 0 and '?' in turnos[i-1][1] if i > 0 else False
                if not cliente_pregunto and i > 2:  # No en el pitch inicial
                    patrones['INFO_NO_SOLICITADA'].append(f"{bruce_id}: '{texto[:60]}'")

            # 3. Bruce dice "Entiendo" como único contenido
            if texto_lower.strip().startswith('entiendo') and len(texto) < 30:
                patrones['ACK_VACIO'].append(f"{bruce_id}: '{texto}'")

            # 4. Pregunta por nombre cuando ya tiene el contacto
            if ('nombre' in texto_lower or 'cómo se llama' in texto_lower):
                if conv['whatsapp'] or conv['email']:
                    patrones['PREGUNTA_NOMBRE_INNECESARIA'].append(f"{bruce_id}: '{texto[:60]}'")

    return patrones


# ----------------------------------------------
# Reporte
# ----------------------------------------------

def generar_reporte(convs):
    print("=" * 70)
    print("  AUDITORÍA CUALITATIVA - BRUCE W")
    print(f"  {len(convs)} conversaciones analizadas")
    print("=" * 70)

    stats = {
        'contacto_capturado': 0,
        'sin_contacto': 0,
        'total_issues': 0,
        'total_positivos': 0,
    }

    todas_issues = defaultdict(int)
    patrones_prompt = detectar_patrones_prompt(convs)

    for conv in convs:
        turnos = conv['turnos']
        print(f"\n{'-'*70}")
        print(f"  {conv['id']} | {conv['nombre']}")
        print(f"  Turnos: {conv['n_turnos']} cliente | Estado: {conv['estado_final']}")
        print(f"  Contacto: {conv['whatsapp'] or conv['email'] or 'NINGUNO'}")
        print(f"{'-'*70}")

        # Mostrar conversación
        print("\n  CONVERSACIÓN:")
        for rol, texto in turnos:
            prefix = "  🙋" if rol == 'cliente' else "  🤖"
            prefix = "  C:" if rol == 'cliente' else "  B:"
            print(f"  {prefix} {texto[:110]}")

        # Evaluaciones
        all_positivos = []
        all_issues = []

        for evaluador in [evaluar_saludo, evaluar_objeciones, evaluar_naturalidad]:
            pos, iss = evaluador(turnos)
            all_positivos.extend(pos)
            all_issues.extend(iss)

        pos, iss = evaluar_captura_contacto(conv)
        all_positivos.extend(pos)
        all_issues.extend(iss)

        if conv['whatsapp'] or conv['email']:
            stats['contacto_capturado'] += 1
        else:
            stats['sin_contacto'] += 1

        stats['total_issues'] += len(all_issues)
        stats['total_positivos'] += len(all_positivos)

        if all_issues:
            print("\n  ISSUES DETECTADOS:")
            for iss in all_issues:
                print(f"    ! {iss}")
                todas_issues[iss.split(':')[0]] += 1

        if all_positivos:
            print("\n  POSITIVOS:")
            for pos in all_positivos:
                print(f"    OK {pos}")

    # Resumen estadístico
    print(f"\n{'='*70}")
    print(f"  RESUMEN")
    print(f"{'='*70}")
    print(f"  Llamadas analizadas:     {len(convs)}")
    print(f"  Contacto capturado:      {stats['contacto_capturado']} ({stats['contacto_capturado']*100//len(convs) if convs else 0}%)")
    print(f"  Sin contacto:            {stats['sin_contacto']}")
    print(f"  Issues de calidad:       {stats['total_issues']}")
    print(f"  Aspectos positivos:      {stats['total_positivos']}")

    if patrones_prompt:
        print(f"\n  PATRONES A MEJORAR EN PROMPT GPT:")
        for patron, ejemplos in patrones_prompt.items():
            print(f"    [{patron}] ({len(ejemplos)}x)")
            for ej in ejemplos[:2]:
                print(f"      → {ej}")

    # Recomendaciones de mejora
    print(f"\n  RECOMENDACIONES PRIORITARIAS:")
    recs = []

    if stats['sin_contacto'] > len(convs) * 0.4:
        recs.append("Alta tasa de llamadas sin contacto - revisar estrategia de captura")

    if patrones_prompt.get('INFO_NO_SOLICITADA'):
        recs.append("Bruce da info de productos sin que le pregunten - simplificar pitch")

    if patrones_prompt.get('ACK_VACIO'):
        recs.append("Respuestas 'Entiendo' vacías - mejorar acknowledgments con continuación")

    if patrones_prompt.get('CATALOGO_POST_CAPTURA'):
        recs.append("Ofrece catálogo después de ya tenerlo - el prompt tiene lógica de re-oferta")

    if not recs:
        recs.append("Sin problemas sistémicos detectados en este batch")

    for i, rec in enumerate(recs, 1):
        print(f"    {i}. {rec}")

    print()


# ----------------------------------------------
# Main
# ----------------------------------------------

def main():
    args = sys.argv[1:]

    if not args:
        print("Uso: python auditoria_cualitativa.py LOGS/04_03PT1.txt [LOGS/04_03PT2.txt ...]")
        print("     python auditoria_cualitativa.py logs_04_03_combined.txt")
        sys.exit(1)

    # Leer todos los archivos
    log_combinado = ""
    for path in args:
        if not os.path.exists(path):
            # Intentar en carpeta LOGS
            alt = os.path.join('LOGS', path)
            if os.path.exists(alt):
                path = alt
            else:
                print(f"Archivo no encontrado: {path}")
                continue
        with open(path, encoding='utf-8', errors='replace') as f:
            log_combinado += f.read() + "\n"

    convs = extraer_conversaciones(log_combinado)

    if not convs:
        print("No se encontraron conversaciones en los logs.")
        sys.exit(1)

    generar_reporte(convs)


if __name__ == '__main__':
    main()
