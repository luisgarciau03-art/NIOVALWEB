"""
TEST FIX 614: BRUCE2029 - Tres Problemas Críticos

Problema #1: Negación "NO necesitaría esperar" no detectada
Problema #2: Repetición idéntica sin contexto
Problema #3: Pregunta del cliente interpretada como afirmación
"""

import re

def test_fix_614():
    print("\n" + "="*70)
    print("TEST FIX 614: BRUCE2029 - Deteccion de Negaciones y Preguntas")
    print("="*70)

    # Patrones de negación (copiados de agente_ventas.py línea ~2851)
    patrones_negacion = [
        r'cerrado', r'no\s+est[aá]', r'no\s+se\s+encuentra',
        r'no\s+hay', r'no\s+tenemos', r'no\s+puede',
        r'ocupado', r'no\s+disponible',
        r'no\s+(?:me|nos|le)?\s*interesa',
        r'ahorita\s+no\s+(?:me|nos|le)?\s*interesa',
        r'no\s+(?:estoy|estamos)\s+interesad[oa]',
        r'no\s+(?:necesito|necesitamos)',
        r'no\s+(?:gracias|thank)',
        r'no\s+(?:te|lo|la|le)\s+encuentr[oa]',
        r'no\s+(?:te|lo|la|le)\s+encuentr[oa]\s+ahorita',
        r'no,?\s*no,?\s*ahorita\s+no',
        r'no,?\s*no\s+est[aá]',
        r'no\s+est[aá]\s+ahorita',
        r'ahorita\s+no\s+est[aá]',
        r'(?:encargado|jefe|gerente).*(?:no\s+est[aá]|sali[oó]|se\s+fue)',
        r'(?:no\s+est[aá]|sali[oó]|se\s+fue).*(?:encargado|jefe|gerente)',
        r'ya\s+sali[oó]', r'se\s+fue', r'est[aá]\s+fuera',
        r'(?:entra|llega|viene|encuentra|est[aá])\s+(?:a\s+las?|hasta\s+las?)\s*\d',
        r'(?:entra|llega|viene|encuentra|est[aá])\s+(?:en\s+la\s+)?(?:tarde|mañana|noche)',
        r'hasta\s+las?\s*\d',
        r'(?:después|despues)\s+de\s+las?\s*\d',
        r'(?:m[aá]s\s+)?tarde',
        r'(?:en\s+)?(?:un\s+)?rato',
        r'(?:no\s+)?(?:tod[ao])?v[ií]a\s+no',
        # FIX 614: Nuevos patrones (CORREGIDOS)
        r'no\s+(?:necesit|pod|deber|quier|puedes?|puede)[a-záéíóúüñ]*\s+esperar',
        r'no\s+(?:necesit|pod|deber|quier)[a-záéíóúüñ]*\s+que\s+.*esperar',
    ]

    # Patrones de espera (copiados de agente_ventas.py línea ~2887)
    patrones_espera = [
        r'perm[ií]t[ae]me', r'perm[ií]tame',
        r'me\s+permite', r'me\s+permites',
        r'esp[eé]r[ae]me', r'espera',
        r'un\s+momento', r'un\s+segundito', r'un\s+segundo',
        r'dame\s+chance', r'd[ée]jame',
        r'aguanta', r'tantito',
    ]

    # Test cases
    test_cases = [
        {
            "frase": "No necesitaría esperar que vuelva.",
            "descripcion": "BRUCE2029 Problema #1: Negación con verbo modal",
            "esperado": {
                "detecta_espera": True,
                "detecta_negacion": True,  # FIX 614: Ahora SÍ debe detectar negación
                "es_pregunta": False,
                "resultado": "NO activar 'Claro, espero'"
            }
        },
        {
            "frase": "¿Necesitas esperar que vuelva?",
            "descripcion": "BRUCE2029 Problema #3: Pregunta con 'esperar'",
            "esperado": {
                "detecta_espera": True,
                "detecta_negacion": False,
                "es_pregunta": True,  # FIX 614: Detectar pregunta
                "resultado": "NO activar 'Claro, espero'"
            }
        },
        {
            "frase": "No podría esperar.",
            "descripcion": "FIX 614: Otra negación con verbo modal",
            "esperado": {
                "detecta_espera": True,
                "detecta_negacion": True,
                "es_pregunta": False,
                "resultado": "NO activar 'Claro, espero'"
            }
        },
        {
            "frase": "Espérame un momento.",
            "descripcion": "Caso válido: Cliente SÍ pide esperar",
            "esperado": {
                "detecta_espera": True,
                "detecta_negacion": False,
                "es_pregunta": False,
                "resultado": "SÍ activar 'Claro, espero'"
            }
        },
        {
            "frase": "Permítame un segundo.",
            "descripcion": "Caso válido: Cliente SÍ pide esperar",
            "esperado": {
                "detecta_espera": True,
                "detecta_negacion": False,
                "es_pregunta": False,
                "resultado": "SÍ activar 'Claro, espero'"
            }
        },
    ]

    # Ejecutar tests
    print()
    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        frase = test["frase"]
        esperado = test["esperado"]

        # Detectar espera
        detecta_espera = any(re.search(p, frase.lower()) for p in patrones_espera)

        # Detectar negación
        detecta_negacion = any(re.search(p, frase.lower()) for p in patrones_negacion)

        # Detectar pregunta
        es_pregunta = '¿' in frase or frase.strip().endswith('?')

        # Determinar resultado
        activar_espera = detecta_espera and not detecta_negacion and not es_pregunta

        print(f"\nTest #{i}: {test['descripcion']}")
        print(f"  Frase: \"{frase}\"")
        print(f"  Detecta espera: {detecta_espera} (esperado: {esperado['detecta_espera']})")
        print(f"  Detecta negacion: {detecta_negacion} (esperado: {esperado['detecta_negacion']})")
        print(f"  Es pregunta: {es_pregunta} (esperado: {esperado['es_pregunta']})")
        print(f"  Activar 'Claro, espero': {activar_espera}")
        print(f"  Resultado esperado: {esperado['resultado']}")

        # Verificar
        test_passed = (
            detecta_espera == esperado['detecta_espera'] and
            detecta_negacion == esperado['detecta_negacion'] and
            es_pregunta == esperado['es_pregunta']
        )

        if test_passed:
            print(f"  [OK] PASS")
            passed += 1
        else:
            print(f"  [FAIL] FAIL")
            failed += 1

    # Resumen
    print("\n" + "="*70)
    print(f"RESUMEN: {passed} PASS, {failed} FAIL")
    print("="*70)

    return failed == 0


if __name__ == "__main__":
    success = test_fix_614()
    exit(0 if success else 1)
