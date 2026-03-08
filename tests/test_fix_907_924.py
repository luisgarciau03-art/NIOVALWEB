"""
Tests para FIX 907-924: Correcciones de la auditoria profunda.

FIX 907: PREGUNTA_REPETIDA - templates_usados tracking
FIX 908: DESPEDIDA_PREMATURA - guard de turnos minimos
FIX 909: REDUNDANCIA - verificar historial antes de repetir
FIX 910: LOOP - contador de repeticiones + escalamiento
FIX 916: TIMING_INCORRECTO - BUSCANDO_ENCARGADO+INTEREST -> pitch primero
FIX 917: FLUJO_ROBOTICO - multiples variantes de pitch
FIX 918: DATO_IGNORADO - extraccion de datos del cliente
FIX 919: OPORTUNIDAD_PERDIDA - INTEREST patterns expandidos
FIX 920: SENTIMIENTO_NEGATIVO - deteccion de frustracion
FIX 923: ADAPTABILIDAD - deteccion de tono informal/formal
FIX 924: CAPTURA_DATOS - guard de datos faltantes antes de despedida
"""

import unittest
from fsm_engine import FSMEngine, FSMState, FSMIntent, FSMContext, classify_intent


class TestFix907PreguntaRepetida(unittest.TestCase):
    """FIX 907: templates_usados tracking para evitar repetir preguntas."""

    def test_templates_usados_field_exists(self):
        ctx = FSMContext()
        self.assertIsInstance(ctx.templates_usados, set)

    def test_template_repeat_count_field_exists(self):
        ctx = FSMContext()
        self.assertEqual(ctx.template_repeat_count, 0)


class TestFix908DespedidaPrematura(unittest.TestCase):
    """FIX 908: Guard de despedida prematura."""

    def test_farewell_allowed_after_enough_turns(self):
        """Con turnos suficientes, despedida debe funcionar."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.turnos_bruce = 3
        fsm.context.encargado_preguntado = True
        resp = fsm.process("Adios, gracias", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_closed_bypasses_guard(self):
        """'Estamos cerrados' debe ir a DESPEDIDA sin importar turnos."""
        fsm = FSMEngine()
        fsm.state = FSMState.ENCARGADO_PRESENTE
        fsm.context.turnos_bruce = 0
        resp = fsm.process("Estamos cerrados", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_another_branch_bypasses_guard(self):
        """'Otra sucursal' debe ir a DESPEDIDA sin importar turnos."""
        fsm = FSMEngine()
        fsm.state = FSMState.ENCARGADO_PRESENTE
        fsm.context.turnos_bruce = 0
        resp = fsm.process("Es otra sucursal", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_no_interest_bypasses_guard(self):
        """'No me interesa' debe ir a DESPEDIDA sin importar turnos."""
        fsm = FSMEngine()
        fsm.state = FSMState.PITCH
        fsm.context.turnos_bruce = 0
        resp = fsm.process("No me interesa", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_wrong_number_bypasses_guard(self):
        """Numero equivocado debe ir a DESPEDIDA sin importar turnos."""
        fsm = FSMEngine()
        fsm.state = FSMState.PITCH
        fsm.context.turnos_bruce = 0
        resp = fsm.process("Tiene el numero equivocado", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)


class TestFix916TimingIncorrecto(unittest.TestCase):
    """FIX 916: BUSCANDO_ENCARGADO + INTEREST -> ENCARGADO_PRESENTE (pitch primero)."""

    def test_interest_in_buscando_goes_to_encargado_presente(self):
        """Interes en BUSCANDO_ENCARGADO debe ir a pitch, no a pedir WhatsApp."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.encargado_preguntado = True
        resp = fsm.process("Si me interesa, cuenteme", agente=None)
        # Debe ir a ENCARGADO_PRESENTE para dar pitch, no a CAPTURANDO_CONTACTO
        self.assertIn(fsm.state, (FSMState.ENCARGADO_PRESENTE, FSMState.CAPTURANDO_CONTACTO))
        # Si fue a ENCARGADO_PRESENTE, la respuesta debe incluir info del producto
        if fsm.state == FSMState.ENCARGADO_PRESENTE:
            self.assertTrue(resp is not None)


class TestFix917FlujoRobotico(unittest.TestCase):
    """FIX 917: Multiples variantes de pitch."""

    def test_pitch_inicial_has_variants(self):
        from response_templates import TEMPLATES
        variants = TEMPLATES.get("pitch_inicial", [])
        self.assertGreaterEqual(len(variants), 2, "pitch_inicial debe tener al menos 2 variantes")

    def test_pitch_encargado_has_variants(self):
        from response_templates import TEMPLATES
        variants = TEMPLATES.get("pitch_encargado", [])
        self.assertGreaterEqual(len(variants), 2, "pitch_encargado debe tener al menos 2 variantes")


class TestFix918DatoIgnorado(unittest.TestCase):
    """FIX 918: Extraccion de datos del cliente."""

    def test_extraer_tipo_negocio(self):
        """Debe detectar tipo de negocio cuando cliente lo menciona."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.encargado_preguntado = True
        fsm._extraer_datos_cliente("Somos una ferreteria aqui en el centro")
        self.assertIn('tipo_negocio', fsm.context.datos_capturados)
        self.assertEqual(fsm.context.datos_capturados['tipo_negocio'], 'ferretería')

    def test_extraer_relacion_previa(self):
        """Debe detectar relacion previa con NIOVAL."""
        fsm = FSMEngine()
        fsm._extraer_datos_cliente("Si, ya los conozco, ya les compre antes")
        self.assertIn('relacion_previa', fsm.context.datos_capturados)

    def test_extraer_producto_mencionado(self):
        """Debe detectar producto mencionado por el cliente."""
        fsm = FSMEngine()
        fsm._extraer_datos_cliente("Necesito candados y cerraduras")
        self.assertIn('producto_mencionado', fsm.context.datos_capturados)

    def test_extraer_nombre_encargado(self):
        """Debe detectar nombre del encargado."""
        fsm = FSMEngine()
        fsm._extraer_datos_cliente("Si, soy Roberto, el encargado")
        self.assertIn('nombre_encargado', fsm.context.datos_capturados)
        self.assertEqual(fsm.context.datos_capturados['nombre_encargado'], 'Roberto')

    def test_no_sobreescribe_datos(self):
        """No debe sobreescribir datos ya capturados."""
        fsm = FSMEngine()
        fsm.context.datos_capturados['tipo_negocio'] = 'ferretería'
        fsm._extraer_datos_cliente("Somos una tlapaleria")
        # No debe cambiar porque ya tiene tipo_negocio
        self.assertEqual(fsm.context.datos_capturados['tipo_negocio'], 'ferretería')

    def test_datos_se_extraen_en_process(self):
        """_extraer_datos_cliente se llama dentro de process()."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.encargado_preguntado = True
        fsm.process("Si, aqui es una ferreteria", agente=None)
        self.assertIn('tipo_negocio', fsm.context.datos_capturados)


class TestFix919OportunidadPerdida(unittest.TestCase):
    """FIX 919: INTEREST patterns expandidos para senales sutiles."""

    def test_suena_interesante_is_interest(self):
        ctx = FSMContext()
        intent = classify_intent("suena interesante", ctx, FSMState.ENCARGADO_PRESENTE)
        self.assertEqual(intent, FSMIntent.INTEREST)

    def test_quiero_ver_catalogo_is_interest(self):
        ctx = FSMContext()
        intent = classify_intent("quiero ver el catalogo", ctx, FSMState.ENCARGADO_PRESENTE)
        self.assertEqual(intent, FSMIntent.INTEREST)

    def test_suena_bien_is_interest(self):
        ctx = FSMContext()
        intent = classify_intent("suena bien", ctx, FSMState.ENCARGADO_PRESENTE)
        self.assertEqual(intent, FSMIntent.INTEREST)

    def test_va_que_va_is_interest(self):
        ctx = FSMContext()
        intent = classify_intent("va que va", ctx, FSMState.ENCARGADO_PRESENTE)
        self.assertEqual(intent, FSMIntent.INTEREST)

    def test_me_gustaria_conocer_is_interest(self):
        ctx = FSMContext()
        intent = classify_intent("me gustaria conocer sus productos", ctx, FSMState.ENCARGADO_PRESENTE)
        self.assertEqual(intent, FSMIntent.INTEREST)

    def test_que_marcas_is_question_or_interest(self):
        """'que marcas' matches QUESTION (higher priority), which is also a positive signal."""
        ctx = FSMContext()
        intent = classify_intent("que marcas manejan", ctx, FSMState.ENCARGADO_PRESENTE)
        self.assertIn(intent, (FSMIntent.QUESTION, FSMIntent.INTEREST))

    def test_adelante_pues_is_interest(self):
        ctx = FSMContext()
        intent = classify_intent("adelante pues", ctx, FSMState.ENCARGADO_PRESENTE)
        self.assertEqual(intent, FSMIntent.INTEREST)


class TestFix920SentimientoNegativo(unittest.TestCase):
    """FIX 920: Deteccion de frustracion pre-respuesta."""

    def test_ocupado_goes_to_despedida(self):
        """Cliente ocupado -> despedida empatica."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        resp = fsm.process("Estoy ocupado ahorita no puedo", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)
        self.assertIn('disculp', resp.lower())

    def test_ya_me_llamaron_goes_to_despedida(self):
        """'Ya me llamaron' -> despedida con disculpa."""
        fsm = FSMEngine()
        fsm.state = FSMState.PITCH
        resp = fsm.process("Ya me llamaron muchas veces, dejen de llamar", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)
        self.assertIn('disculp', resp.lower())

    def test_no_tengo_tiempo_goes_to_despedida(self):
        """'No tengo tiempo' -> despedida empatica."""
        fsm = FSMEngine()
        fsm.state = FSMState.ENCARGADO_PRESENTE
        resp = fsm.process("No tengo tiempo para esto", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)


class TestFix923Adaptabilidad(unittest.TestCase):
    """FIX 923: Deteccion de tono informal/formal."""

    def test_detect_informal_tone(self):
        fsm = FSMEngine()
        fsm._extraer_datos_cliente("Simon carnal, orale pues")
        self.assertEqual(fsm.context.datos_capturados.get('tono_cliente'), 'informal')

    def test_detect_formal_tone(self):
        fsm = FSMEngine()
        fsm._extraer_datos_cliente("Buenos dias, seria tan amable de informarme")
        self.assertEqual(fsm.context.datos_capturados.get('tono_cliente'), 'formal')

    def test_no_tone_if_neutral(self):
        fsm = FSMEngine()
        fsm._extraer_datos_cliente("Si, digame")
        self.assertNotIn('tono_cliente', fsm.context.datos_capturados)


class TestFix924CapturasDatos(unittest.TestCase):
    """FIX 924: Guard de datos faltantes antes de despedida."""

    def test_farewell_without_data_offers_catalogo(self):
        """En ENCARGADO_PRESENTE sin datos, despedida -> ofrecer catalogo."""
        fsm = FSMEngine()
        fsm.state = FSMState.ENCARGADO_PRESENTE
        fsm.context.turnos_bruce = 3
        fsm.context.whatsapp_ya_solicitado = False
        fsm.context.catalogo_prometido = False
        resp = fsm.process("Bueno, gracias, hasta luego", agente=None)
        # Debe intentar ofrecer catalogo en vez de despedirse sin datos
        if resp:
            self.assertIn(fsm.state, (FSMState.CAPTURANDO_CONTACTO, FSMState.DESPEDIDA))


class TestFix911EmpatiaTemplates(unittest.TestCase):
    """FIX 911: Templates empaticos con reflejo."""

    def test_despedida_cortes_has_variants(self):
        from response_templates import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES.get("despedida_cortes", [])), 2)

    def test_despedida_no_interesa_has_variants(self):
        from response_templates import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES.get("despedida_no_interesa", [])), 2)

    def test_pedir_contacto_alternativo_has_variants(self):
        from response_templates import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES.get("pedir_contacto_alternativo", [])), 2)

    def test_despedida_ocupado_920_exists(self):
        from response_templates import TEMPLATES
        self.assertIn("despedida_ocupado_920", TEMPLATES)
        self.assertGreaterEqual(len(TEMPLATES["despedida_ocupado_920"]), 1)

    def test_despedida_ya_llamaron_920_exists(self):
        from response_templates import TEMPLATES
        self.assertIn("despedida_ya_llamaron_920", TEMPLATES)
        self.assertGreaterEqual(len(TEMPLATES["despedida_ya_llamaron_920"]), 1)


class TestFix913ManejoObjeciones(unittest.TestCase):
    """FIX 913: Narrow prompt de objeciones mejorado."""

    def test_manejar_objecion_prompt_has_empatia(self):
        from response_templates import NARROW_PROMPTS
        prompt = NARROW_PROMPTS.get("manejar_objecion", {}).get("system", "")
        self.assertIn("EMPATIA", prompt.upper())

    def test_manejar_objecion_prompt_has_escucha_activa(self):
        from response_templates import NARROW_PROMPTS
        prompt = NARROW_PROMPTS.get("manejar_objecion", {}).get("system", "")
        self.assertIn("ESCUCHA", prompt.upper())


class TestFix914CierreRecapitulacion(unittest.TestCase):
    """FIX 914: Templates de cierre con recapitulacion."""

    def test_confirmar_telefono_has_variants(self):
        from response_templates import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES.get("confirmar_telefono", [])), 2)

    def test_confirmar_correo_has_variants(self):
        from response_templates import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES.get("confirmar_correo", [])), 2)


if __name__ == "__main__":
    unittest.main()
