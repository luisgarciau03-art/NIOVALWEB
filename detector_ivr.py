"""
FIX 202: Detector de Sistemas IVR/Contestadoras Automáticas
FIX 506: BRUCE1489/1495/1503 - Reducir falsos positivos

Este módulo detecta cuando Bruce está conversando con un sistema automatizado
(IVR, contestadora, menú telefónico) y permite terminar la llamada temprano
para ahorrar tiempo y créditos.

FIX 506 CAMBIOS:
- "bienvenido a" y "gracias por comunicarse" movidos a confianza MEDIA (no alta)
- Umbral para colgar inmediato aumentado de 0.7 a 0.85
- Detecciones sospechosas necesarias aumentadas de 2 a 3
- Requerir MÚLTIPLES indicadores para colgar (no solo una frase)

Uso:
    from detector_ivr import DetectorIVR

    detector = DetectorIVR()
    resultado = detector.analizar_respuesta("Digite uno para ventas", es_primera_respuesta=True)

    if resultado["accion"] == "colgar":
        print("IVR detectado, terminando llamada")
"""


class DetectorIVR:
    """
    Detector de sistemas IVR/contestadoras automáticas

    Analiza las respuestas del cliente para detectar patrones característicos
    de sistemas automatizados y decide si continuar o colgar la llamada.
    """

    # Patrones de IVR categorizados por tipo
    PATRONES_IVR = {
        "menu_numerico": [
            "digite", "marque", "presione", "pulse", "oprima", "teclee",
            "seleccione", "elija", "escoja"
        ],
        "extensiones": [
            "extensión", "extension", "interno", "número de empleado",
            "código de área", "codigo de area"
        ],
        "navegacion": [
            "menú", "menu", "opciones", "regresar al", "escuchar nuevamente",
            "volver al menú", "repetir las opciones", "para regresar"
        ],
        "espera": [
            "en espera", "orden de recepción", "orden de llegada", "será atendido",
            "próximo disponible", "tiempo estimado", "permanezca en la línea",
            "por favor espere", "aguarde un momento"
        ],
        "teclas": [
            "tecla", "botón", "boton", "opción", "opcion",
            "asterisco", "numeral", "gato"
        ],
        "departamentos": [
            "departamento de", "área de", "para hablar con",
            "si desea comunicarse", "para contactar"
        ]
    }

    # Números mencionados en contexto de menú
    NUMEROS_MENU = [
        "uno", "dos", "tres", "cuatro", "cinco",
        "seis", "siete", "ocho", "nueve",
        "cero", "asterisco", "gato", "numeral"
    ]

    # Frases típicas de IVR (alta confianza) - SOLO frases que NUNCA diría un humano
    FRASES_IVR_ALTA_CONFIANZA = [
        "marque el",
        "digite el",
        "presione el",
        "pulse el",
        "si conoce el número de extensión",
        "para escuchar nuevamente este menú",
        "su llamada será contestada",
        "permanezca en la línea",
        # FIX 752: BRUCE2327 - Patrones DEFINITIVOS de buzón de voz
        # "Grabe su mensaje. Marque la tecla gato cuando termine." = buzón 100%
        "grabe su mensaje", "grabe tu mensaje", "grabe un mensaje",
        "graba su mensaje", "graba tu mensaje", "graba un mensaje",
        "deje su mensaje", "deje tu mensaje", "deje un mensaje",
        "después del tono", "despues del tono",
        "marque la tecla gato", "tecla gato cuando termine",
        # FIX 905: BRUCE2584 - "La persona con la que intentas comunicarte no está disponible"
        "la persona con la que intentas comunicarte",
        "la persona con la que intenta comunicarse",
        "no esta disponible en este momento graba",
        "no se encuentra disponible deje",
        "puedes colgar cuando hayas terminado",
        # FIX 506: "bienvenido a" y "gracias por comunicarse" REMOVIDOS
        # porque negocios reales pueden usarlos como saludo
    ]

    # FIX 506: Frases de CONFIANZA MEDIA - pueden ser IVR o humano, requieren más contexto
    FRASES_IVR_MEDIA_CONFIANZA = [
        "bienvenido a",  # Negocio real puede decir "Bienvenido a Ferretería X"
        "ha llamado a",  # Puede ser saludo de negocio
        "gracias por comunicarse con",  # Puede ser despedida de persona real
        "gracias por llamar a",  # Similar
    ]

    def __init__(self):
        """
        Inicializa el detector de IVR
        """
        self.detecciones_sospechosas = 0
        self.max_detecciones = 3  # FIX 506: Aumentado de 2 a 3 para reducir falsos positivos
        self.historial_confianzas = []  # Para análisis de tendencias

    def analizar_respuesta(self, texto: str, es_primera_respuesta: bool = False) -> dict:
        """
        Analiza una respuesta del cliente para detectar IVR

        Args:
            texto: Texto de la respuesta del cliente
            es_primera_respuesta: True si es la primera respuesta en la llamada

        Returns:
            dict con:
                - es_ivr (bool): True si se detectó IVR
                - confianza (float): 0.0-1.0, qué tan seguro estamos
                - categorias (list): Categorías de IVR detectadas
                - palabras_ivr (int): Cantidad de palabras clave encontradas
                - numeros_menu (int): Cantidad de números de menú encontrados
                - accion (str): "continuar", "investigar", o "colgar"
                - detecciones_acumuladas (int): Total de detecciones sospechosas
                - razon (str): Explicación de por qué se detectó IVR
        """
        texto_lower = texto.lower().strip()
        palabras = texto_lower.split()

        # Inicializar contadores
        palabras_ivr = 0
        categorias_detectadas = []
        frases_alta_confianza = []
        frases_media_confianza = []  # FIX 506

        # === VERIFICACIÓN 1: Frases de alta confianza ===
        for frase in self.FRASES_IVR_ALTA_CONFIANZA:
            if frase in texto_lower:
                frases_alta_confianza.append(frase)

        # === FIX 506: Frases de confianza media (requieren más contexto) ===
        for frase in self.FRASES_IVR_MEDIA_CONFIANZA:
            if frase in texto_lower:
                frases_media_confianza.append(frase)

        # === VERIFICACIÓN 2: Patrones por categoría ===
        for categoria, patrones in self.PATRONES_IVR.items():
            for patron in patrones:
                if patron in texto_lower:
                    palabras_ivr += 1
                    if categoria not in categorias_detectadas:
                        categorias_detectadas.append(categoria)

        # === VERIFICACIÓN 3: Números de menú ===
        numeros_menu_detectados = 0
        for num in self.NUMEROS_MENU:
            # Contar cuántas veces aparece cada número
            numeros_menu_detectados += texto_lower.count(num)

        # === VERIFICACIÓN 4: Longitud excesiva ===
        longitud_palabras = len(palabras)

        # === CALCULAR CONFIANZA ===
        confianza = 0.0
        razones = []
        indicadores_ivr = 0  # FIX 506: Contador de indicadores diferentes

        # Factor 1: Frases de alta confianza (peso muy alto)
        if frases_alta_confianza:
            confianza += 0.5
            indicadores_ivr += 1
            razones.append(f"Frases IVR detectadas: {', '.join(frases_alta_confianza[:2])}")

        # FIX 506: Factor 1b - Frases de confianza media (peso menor, solo 0.2)
        elif frases_media_confianza:  # Solo si NO hay frases de alta confianza
            confianza += 0.2  # Menos peso que antes (era 0.5 cuando estaban juntas)
            razones.append(f"Frases IVR media confianza: {', '.join(frases_media_confianza[:2])}")

        # Factor 2: Palabras clave de IVR
        if palabras_ivr >= 3:
            confianza += 0.3
            indicadores_ivr += 1  # FIX 506
            razones.append(f"{palabras_ivr} palabras clave IVR")
        elif palabras_ivr >= 2:
            confianza += 0.2
            indicadores_ivr += 1  # FIX 506
            razones.append(f"{palabras_ivr} palabras clave IVR")
        elif palabras_ivr >= 1:
            confianza += 0.1

        # Factor 3: Números de menú (especialmente si hay múltiples)
        if numeros_menu_detectados >= 3:
            confianza += 0.25
            indicadores_ivr += 1  # FIX 506
            razones.append(f"{numeros_menu_detectados} números de menú")
        elif numeros_menu_detectados >= 2:
            confianza += 0.15
            indicadores_ivr += 1  # FIX 506
            razones.append(f"{numeros_menu_detectados} números de menú")
        elif numeros_menu_detectados >= 1:
            confianza += 0.05

        # Factor 4: Longitud excesiva (típico de IVR)
        if longitud_palabras > 50:
            confianza += 0.2
            razones.append(f"Respuesta muy larga ({longitud_palabras} palabras)")
        elif longitud_palabras > 35:
            confianza += 0.15
            razones.append(f"Respuesta larga ({longitud_palabras} palabras)")
        elif longitud_palabras > 25:
            confianza += 0.05

        # Factor 5: Primera respuesta muy larga (típico de saludo IVR)
        if es_primera_respuesta and longitud_palabras > 20:
            confianza += 0.15
            razones.append("Primera respuesta muy larga")

        # Factor 6: Múltiples categorías de IVR detectadas
        if len(categorias_detectadas) >= 3:
            confianza += 0.15
            razones.append(f"Múltiples categorías: {', '.join(categorias_detectadas)}")
        elif len(categorias_detectadas) >= 2:
            confianza += 0.1

        # === NORMALIZAR CONFIANZA (máximo 1.0) ===
        confianza = min(confianza, 1.0)

        # === GUARDAR EN HISTORIAL ===
        self.historial_confianzas.append(confianza)

        # === DETERMINAR ACCIÓN ===
        es_ivr = confianza >= 0.5
        accion = "continuar"

        # FIX 506: Aumentado umbral de 0.7 a 0.85, y requerir múltiples indicadores
        if confianza >= 0.85 and indicadores_ivr >= 2:
            # MUY Alta confianza + múltiples indicadores → Colgar inmediatamente
            accion = "colgar"
            self.detecciones_sospechosas = 999  # Forzar cuelgue
            razones.append(f"MUY ALTA CONFIANZA ({indicadores_ivr} indicadores) → Colgar")

        elif confianza >= 0.7 and indicadores_ivr >= 2:
            # FIX 506: Alta confianza PERO solo si hay 2+ indicadores diferentes
            # Antes colgaba con 0.7 y cualquier indicador (causaba falsos positivos)
            accion = "colgar"
            self.detecciones_sospechosas = 999
            razones.append(f"ALTA CONFIANZA ({indicadores_ivr} indicadores) → Colgar")

        elif confianza >= 0.5:
            # Confianza media → Incrementar contador
            self.detecciones_sospechosas += 1

            if self.detecciones_sospechosas >= self.max_detecciones:
                accion = "colgar"
                razones.append(f"Detecciones acumuladas: {self.detecciones_sospechosas} → Colgar")
            else:
                accion = "investigar"
                razones.append(f"Detección sospechosa #{self.detecciones_sospechosas} → Investigar")

        elif confianza >= 0.3:
            # Confianza baja → Investigar sin incrementar contador
            accion = "investigar"
            razones.append("Posible IVR → Investigar")

        else:
            # Confianza muy baja → Continuar normal
            accion = "continuar"

        # === CONSTRUIR RESULTADO ===
        resultado = {
            "es_ivr": es_ivr,
            "confianza": round(confianza, 2),
            "categorias": categorias_detectadas,
            "palabras_ivr": palabras_ivr,
            "numeros_menu": numeros_menu_detectados,
            "longitud_palabras": longitud_palabras,
            "frases_alta_confianza": frases_alta_confianza,
            "frases_media_confianza": frases_media_confianza,  # FIX 506
            "indicadores_ivr": indicadores_ivr,  # FIX 506: Cantidad de indicadores diferentes
            "accion": accion,
            "detecciones_acumuladas": self.detecciones_sospechosas,
            "razon": " | ".join(razones) if razones else "Respuesta normal"
        }

        return resultado

    def reset(self):
        """
        Reinicia el detector para una nueva llamada
        """
        self.detecciones_sospechosas = 0
        self.historial_confianzas = []

    def obtener_estadisticas(self) -> dict:
        """
        Obtiene estadísticas del detector en la llamada actual

        Returns:
            dict con estadísticas de la sesión
        """
        if not self.historial_confianzas:
            return {
                "total_respuestas": 0,
                "confianza_promedio": 0.0,
                "confianza_maxima": 0.0,
                "detecciones_sospechosas": 0
            }

        return {
            "total_respuestas": len(self.historial_confianzas),
            "confianza_promedio": round(sum(self.historial_confianzas) / len(self.historial_confianzas), 2),
            "confianza_maxima": round(max(self.historial_confianzas), 2),
            "detecciones_sospechosas": self.detecciones_sospechosas
        }


# === PRUEBAS Y EJEMPLOS ===
if __name__ == "__main__":
    print("\n" + "="*70)
    print(" FIX 202: PRUEBAS DE DETECCIÓN DE IVR")
    print("="*70 + "\n")

    detector = DetectorIVR()

    # Test cases con respuestas reales de BRUCE459 y otros casos
    test_cases = [
        {
            "nombre": "Test 1: Menú IVR clásico",
            "texto": "Bienvenido a Grupo Acme. Para ventas marque uno, para servicio marque dos, para facturación marque tres.",
            "es_primera": True,
            "esperado": "colgar"
        },
        {
            "nombre": "Test 2: Solicitud de extensión (BRUCE459)",
            "texto": "dirigido a grupo gemsa si conoce el número de extensión márquelo ahora",
            "es_primera": True,
            "esperado": "colgar"
        },
        {
            "nombre": "Test 3: Instrucciones de menú (BRUCE459)",
            "texto": "digite uno para reparación de motores marque dos para ventas de equipos",
            "es_primera": False,
            "esperado": "colgar"
        },
        {
            "nombre": "Test 4: Mensaje de espera",
            "texto": "Su llamada será contestada en el orden en que fue recibida por favor permanezca en la línea",
            "es_primera": False,
            "esperado": "investigar o colgar"
        },
        {
            "nombre": "Test 5: Respuesta humana normal",
            "texto": "Bueno, dígame",
            "es_primera": True,
            "esperado": "continuar"
        },
        {
            "nombre": "Test 6: Respuesta humana con 'marque'",
            "texto": "Mire si quiere puede marcar después estamos ocupados",
            "es_primera": False,
            "esperado": "continuar"
        },
        {
            "nombre": "Test 7: Saludo humano normal",
            "texto": "Buenas tardes",
            "es_primera": True,
            "esperado": "continuar"
        },
        {
            "nombre": "Test 8: IVR con tecla gato (BRUCE459)",
            "texto": "para escuchar nuevamente este menú marque la tecla gato",
            "es_primera": False,
            "esperado": "colgar"
        }
    ]

    # Ejecutar tests
    for i, test in enumerate(test_cases, 1):
        print(f"\n{''*70}")
        print(f" {test['nombre']}")
        print(f"{''*70}")
        print(f"Texto: \"{test['texto']}\"")
        print(f"Primera respuesta: {test['es_primera']}")
        print(f"Acción esperada: {test['esperado']}")
        print()

        # Analizar
        resultado = detector.analizar_respuesta(test['texto'], test['es_primera'])

        # Mostrar resultado
        if resultado["es_ivr"]:
            emoji = ""
        elif resultado["confianza"] >= 0.3:
            emoji = ""
        else:
            emoji = ""

        print(f"{emoji} RESULTADO:")
        print(f"   IVR detectado: {resultado['es_ivr']}")
        print(f"   Confianza: {resultado['confianza']:.0%}")
        print(f"   Acción: {resultado['accion'].upper()}")
        print(f"   Razón: {resultado['razon']}")

        if resultado["categorias"]:
            print(f"   Categorías: {', '.join(resultado['categorias'])}")

        if resultado["frases_alta_confianza"]:
            print(f"   Frases IVR: {', '.join(resultado['frases_alta_confianza'][:3])}")

        print(f"   Palabras IVR: {resultado['palabras_ivr']} | Números menú: {resultado['numeros_menu']} | Longitud: {resultado['longitud_palabras']} palabras")

        # Verificar si cumple expectativa
        if resultado["accion"] == test["esperado"] or test["esperado"] in resultado["accion"]:
            print(f"\n    CORRECTO: Acción coincide con esperado")
        else:
            print(f"\n     REVISAR: Se esperaba '{test['esperado']}', se obtuvo '{resultado['accion']}'")

        # Reset detector para siguiente test
        detector.reset()

    # Estadísticas finales
    print("\n" + "="*70)
    print(" PRUEBAS COMPLETADAS")
    print("="*70 + "\n")
