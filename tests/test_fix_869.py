"""Tests para FIX 869A-869I - Eliminación 13 bugs restantes replay masivo 450 llamadas.

FIX 869A: Más variantes encargado ausente (no se quiso, no tiene hora)
FIX 869B: Quejas sobre la llamada (hablando mucho, ya no queremos)
FIX 869C: Identity re-statements excluidas de PREGUNTA_REPETIDA
FIX 869D: Callback cross-talk threshold skip en conversaciones largas
FIX 869E: AREA_EQUIVOCADA incomplete sentence + acknowledgment sin venta
FIX 869F: Pitch saludo corto exempt de PITCH_REPETIDO
FIX 869G: Identity Q ya respondida en turno previo skip PREGUNTA_IGNORADA
FIX 869H: Identity re-statements en _VERIFICATION_LOOP_EXEMPT
FIX 869I: Transfer acknowledged skip TRANSFER_IGNORADA
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import pytest
from bug_detector import ContentAnalyzer


# ============================================================
# FIX 869A: Más variantes encargado ausente
# ============================================================
class TestFix869AEncargadoAusenteExtendido:
    """BRUCE2446/1797: 'no se quiso'/'no tiene hora' = absent, not interruption."""

    def test_no_se_quiso_no_interrumpe(self):
        conv = [
            ("bruce", "Buen día, ¿me podría comunicar con el encargado?"),
            ("cliente", "es que no se quiso comunicar con usted"),
            ("bruce", "Entiendo, ¿me podría dar su WhatsApp para enviarle información?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)

    def test_no_quiso_no_interrumpe(self):
        conv = [
            ("bruce", "¿Está el encargado?"),
            ("cliente", "es que no quiso atenderle"),
            ("bruce", "¿Me podría dar un correo para enviarle el catálogo?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)

    def test_no_tiene_hora_no_interrumpe(self):
        conv = [
            ("bruce", "¿Se encuentra el encargado?"),
            ("cliente", "es que no tiene hora de entrar"),
            ("bruce", "¿Me podría dar su número de WhatsApp?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)

    def test_no_tiene_horario_no_interrumpe(self):
        conv = [
            ("bruce", "¿Se encuentra el dueño?"),
            ("cliente", "es que no tiene horario fijo"),
            ("bruce", "Entiendo, ¿me da un WhatsApp para contactarle?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)

    def test_no_quiere_no_interrumpe(self):
        conv = [
            ("bruce", "¿Me comunica con el encargado?"),
            ("cliente", "es que no quiere atender la llamada"),
            ("bruce", "¿Me podría dar su correo para enviarle información?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)


# ============================================================
# FIX 869B: Quejas sobre la llamada
# ============================================================
class TestFix869BQuejasLlamada:
    """BRUCE2096: 'hablando mucho' = complaint, not explanation needing continuation."""

    def test_hablando_mucho_no_interrumpe(self):
        conv = [
            ("bruce", "Le llamo de parte de NIOVAL con catálogo de ferretería"),
            ("cliente", "es que ya están hablando mucho y nosotros no necesitamos"),
            ("bruce", "¿Me podría dar su WhatsApp para enviarle el catálogo?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)

    def test_ya_no_queremos_no_interrumpe(self):
        conv = [
            ("bruce", "Tenemos más de 20,000 productos de ferretería"),
            ("cliente", "es que ya no queremos que nos llamen"),
            ("bruce", "¿Le podría dar su WhatsApp para enviarle información?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)

    def test_no_nos_interesa_no_interrumpe(self):
        conv = [
            ("bruce", "Le llamo de NIOVAL"),
            ("cliente", "es que no nos interesa, gracias"),
            ("bruce", "¿Me permite enviarle el catálogo por WhatsApp?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)

    def test_real_explanation_still_detected(self):
        """Regular explanations that Bruce interrupts should still be detected."""
        conv = [
            ("bruce", "¿En qué le puedo ayudar?"),
            ("cliente", "es que estamos buscando un proveedor de herramientas porque"),
            ("bruce", "¡Excelente! ¿Me da su WhatsApp?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)


# ============================================================
# FIX 869C: Identity re-statements en PREGUNTA_REPETIDA
# ============================================================
class TestFix869CIdentityRestatements:
    """BRUCE2477/2344/1975: identity re-statements not counted as repeated questions."""

    def test_mi_nombre_es_bruce_not_repeated(self):
        conv = [
            ("bruce", "Buen día, le llamo de NIOVAL, mi nombre es Bruce"),
            ("cliente", "¿Quién habla?"),
            ("bruce", "Mi nombre es Bruce, le llamo de parte de NIOVAL, ¿me podría dar su WhatsApp?"),
            ("cliente", "Ah ok"),
            ("bruce", "¿Me podría dar su número de WhatsApp para enviarle el catálogo?"),
        ]
        respuestas = [t for r, t in conv if r == "bruce"]
        bugs = ContentAnalyzer._check_pregunta_repetida(respuestas, conv)
        assert not any(b["tipo"] == "PREGUNTA_REPETIDA" for b in bugs)

    def test_soy_bruce_distribuidores_not_repeated(self):
        conv = [
            ("bruce", "Buen día, ¿me comunica con el encargado?"),
            ("cliente", "¿De dónde llama?"),
            ("bruce", "Somos distribuidores de productos ferreteros de Guadalajara, ¿me podría dar su correo?"),
            ("cliente", "¿Qué marca?"),
            ("bruce", "Le llamo de NIOVAL, ¿me podría proporcionar su correo electrónico?"),
        ]
        respuestas = [t for r, t in conv if r == "bruce"]
        bugs = ContentAnalyzer._check_pregunta_repetida(respuestas, conv)
        assert not any(b["tipo"] == "PREGUNTA_REPETIDA" for b in bugs)

    def test_real_repeated_question_still_detected(self):
        """Non-identity repeated questions should still be detected."""
        conv = [
            ("bruce", "¿Me podría dar su WhatsApp?"),
            ("cliente", "No tengo WhatsApp"),
            ("bruce", "¿Me podría dar su WhatsApp?"),
            ("cliente", "Ya le dije que no"),
            ("bruce", "¿Me podría dar su WhatsApp?"),
        ]
        respuestas = [t for r, t in conv if r == "bruce"]
        bugs = ContentAnalyzer._check_pregunta_repetida(respuestas, conv)
        assert any(b["tipo"] == "PREGUNTA_REPETIDA" for b in bugs)


# ============================================================
# FIX 869D: Callback cross-talk threshold
# ============================================================
class TestFix869DCallbackCrosstalk:
    """BRUCE2529: long conv with callback time cross-talk skips contact Q repeats."""

    def test_callback_crosstalk_long_conv_no_repeat(self):
        """18-turn conv with callback time mentions → contact Qs exempted."""
        conv = [
            ("bruce", "Buen día, ¿me comunica con el encargado?"),
            ("cliente", "No está, viene después de las tres"),
            ("bruce", "¿Me podría dar su WhatsApp para enviarle el catálogo?"),
            ("cliente", "No, mejor llame después de las tres"),
            ("bruce", "¿Me podría dar su correo entonces?"),
            ("cliente", "No, pueden marcar por la tarde"),
            ("bruce", "¿Me podría proporcionar su WhatsApp?"),
            ("cliente", "Que no, llame a las tres"),
            ("bruce", "¿Me da su número de WhatsApp?"),
            ("cliente", "No, por la tarde"),
            ("bruce", "¿Me proporciona su correo electrónico?"),
            ("cliente", "No, llame después de las tres"),
            ("bruce", "¿Me da su número de teléfono?"),
            ("cliente", "Sí, es el 3312345678"),
        ]
        respuestas = [t for r, t in conv if r == "bruce"]
        bugs = ContentAnalyzer._check_pregunta_repetida(respuestas, conv)
        assert not any(b["tipo"] == "PREGUNTA_REPETIDA" for b in bugs)

    def test_short_conv_still_detects_repeats(self):
        """Short conv without callback cross-talk → repeats detected normally."""
        conv = [
            ("bruce", "¿Me podría dar su WhatsApp?"),
            ("cliente", "No tengo"),
            ("bruce", "¿Me podría dar su WhatsApp?"),
            ("cliente", "Ya le dije que no"),
            ("bruce", "¿Me podría dar su WhatsApp?"),
        ]
        respuestas = [t for r, t in conv if r == "bruce"]
        bugs = ContentAnalyzer._check_pregunta_repetida(respuestas, conv)
        assert any(b["tipo"] == "PREGUNTA_REPETIDA" for b in bugs)


# ============================================================
# FIX 869E: AREA_EQUIVOCADA incomplete + acknowledgment
# ============================================================
class TestFix869EAreaEquivocada:
    """BRUCE2491/1897: incomplete sentence + Bruce acknowledges without selling."""

    def test_incomplete_sentence_skip(self):
        """Sentence ending with comma = incomplete, skip area_equivocada."""
        conv = [
            ("bruce", "Le llamo de NIOVAL con catálogo ferretero"),
            ("cliente", "es que está equivocado,"),
            ("bruce", "Disculpe, ¿me podría comunicar con la persona correcta?"),
        ]
        bugs = ContentAnalyzer._check_area_equivocada(conv)
        assert not any(b["tipo"] == "AREA_EQUIVOCADA" for b in bugs)

    def test_bruce_disculpe_no_venta(self):
        """Bruce says 'disculpe' without continuing to sell → not a bug."""
        conv = [
            ("bruce", "Le llamo de NIOVAL"),
            ("cliente", "aquí es una papelería, no ferretería"),
            ("bruce", "Disculpe la molestia, le paso la sucursal correcta."),
        ]
        bugs = ContentAnalyzer._check_area_equivocada(conv)
        assert not any(b["tipo"] == "AREA_EQUIVOCADA" for b in bugs)

    def test_bruce_entiendo_pero_vende_still_bug(self):
        """Bruce says 'entiendo' but keeps selling → still a bug."""
        conv = [
            ("bruce", "Le llamo de NIOVAL"),
            ("cliente", "esto no es ferretería, es taller mecánico"),
            ("bruce", "Entiendo, pero contamos con más de 20,000 productos. ¿Me da su WhatsApp?"),
        ]
        bugs = ContentAnalyzer._check_area_equivocada(conv)
        assert any(b["tipo"] == "AREA_EQUIVOCADA" for b in bugs)

    def test_sentence_ending_y_skip(self):
        """Sentence ending with ' y' = incomplete."""
        conv = [
            ("bruce", "Le llamo de NIOVAL"),
            ("cliente", "aquí no es ferretería y"),
            ("bruce", "Disculpe, que tenga buen día."),
        ]
        bugs = ContentAnalyzer._check_area_equivocada(conv)
        assert not any(b["tipo"] == "AREA_EQUIVOCADA" for b in bugs)


# ============================================================
# FIX 869F: Pitch saludo corto exempt
# ============================================================
class TestFix869FPitchSaludoExempt:
    """BRUCE2038: short greeting + FSM pitch = only 1 pitch, not repeated."""

    def test_short_greeting_plus_pitch_not_repeated(self):
        """First response is short greeting (<40 chars), second is pitch → 1 pitch."""
        respuestas = [
            "Hola, buen día",
            "Le llamo de parte de NIOVAL para ofrecerle nuestro catálogo de más de 20,000 productos de ferretería.",
            "¿Me podría dar su WhatsApp?",
        ]
        bugs = ContentAnalyzer._check_pitch_repetido(respuestas)
        assert not any(b["tipo"] == "PITCH_REPETIDO" for b in bugs)

    def test_first_response_is_pitch_still_counts(self):
        """When first response IS a pitch, it should count normally."""
        respuestas = [
            "Me comunico de NIOVAL, trabajamos productos ferreteros de Guadalajara.",
            "Me comunico de NIOVAL, somos distribuidores NIOVAL de productos ferreteros.",
            "¿Me da su WhatsApp?",
            "Le puedo enviar nuestro catalogo sin compromiso.",
        ]
        bugs = ContentAnalyzer._check_pitch_repetido(respuestas)
        assert any(b["tipo"] == "PITCH_REPETIDO" for b in bugs)

    def test_long_first_response_not_exempt(self):
        """First response >= 40 chars is not exempt even without pitch keywords."""
        respuestas = [
            "Buen día, le llamo para hablar con usted sobre una oportunidad interesante",
            "Me comunico de NIOVAL, trabajamos productos ferreteros de Guadalajara.",
            "Me comunico de NIOVAL, somos distribuidores NIOVAL de ferretería.",
            "Que tenga excelente dia.",
        ]
        bugs = ContentAnalyzer._check_pitch_repetido(respuestas)
        assert any(b["tipo"] == "PITCH_REPETIDO" for b in bugs)


# ============================================================
# FIX 869G: Identity Q ya respondida previamente
# ============================================================
class TestFix869GIdentityQRespondida:
    """BRUCE1914: identity Q already answered in earlier turn, skip PREGUNTA_IGNORADA."""

    def test_identity_q_answered_before_skip(self):
        """Client asks '¿quién habla?' twice, Bruce answered first time → skip second."""
        conv = [
            ("bruce", "Buen día, le llamo de NIOVAL"),
            ("cliente", "¿Quién habla?"),
            ("bruce", "Mi nombre es Bruce, de NIOVAL, distribuidores de ferretería"),
            ("cliente", "¿Quién habla?"),
            ("bruce", "¿Me podría dar su WhatsApp?"),
        ]
        bugs = ContentAnalyzer._check_pregunta_ignorada(conv)
        assert not any(b["tipo"] == "PREGUNTA_IGNORADA" for b in bugs)

    def test_identity_q_first_time_still_detected(self):
        """First time client asks '¿quién habla?' and Bruce gives pure ack → still a bug."""
        conv = [
            ("bruce", "Buen día, ¿se encuentra el encargado?"),
            ("cliente", "Sí, dígame"),
            ("cliente", "¿Quién habla?"),
            ("bruce", "Claro, sí."),
        ]
        bugs = ContentAnalyzer._check_pregunta_ignorada(conv)
        assert any(b["tipo"] == "PREGUNTA_IGNORADA" for b in bugs)

    def test_de_donde_llama_answered_skip(self):
        """'¿De dónde llama?' already answered → skip on repeat."""
        conv = [
            ("bruce", "Le llamo de parte de NIOVAL"),
            ("cliente", "¿De dónde llama?"),
            ("bruce", "De NIOVAL, somos distribuidores de ferretería de Guadalajara"),
            ("cliente", "¿De dónde me dicen que llaman?"),
            ("bruce", "¿Me da su correo para enviarle el catálogo?"),
        ]
        bugs = ContentAnalyzer._check_pregunta_ignorada(conv)
        assert not any(b["tipo"] == "PREGUNTA_IGNORADA" for b in bugs)


# ============================================================
# FIX 869H: Identity re-statements en LOOP exempt
# ============================================================
class TestFix869HVerificationLoopExempt:
    """BRUCE1975: identity re-statements should not count as LOOP.
    _VERIFICATION_LOOP_EXEMPT is local to analyze(), so we test the pattern directly."""

    _LOOP_EXEMPT = re.compile(
        r'(aqui estoy|aquí estoy|sigo aqui|sigo aquí|si.*estoy|me escucha|'
        r'mi nombre es|le llamo de.{0,10}nioval|soy bruce)',
        re.IGNORECASE
    )

    def test_mi_nombre_es_loop_exempt(self):
        assert self._LOOP_EXEMPT.search("Mi nombre es Bruce")

    def test_le_llamo_de_nioval_loop_exempt(self):
        assert self._LOOP_EXEMPT.search("Le llamo de NIOVAL")

    def test_soy_bruce_loop_exempt(self):
        assert self._LOOP_EXEMPT.search("Soy Bruce")

    def test_regular_text_not_exempt(self):
        assert not self._LOOP_EXEMPT.search("Me podría dar su WhatsApp")


# ============================================================
# FIX 869I: Transfer acknowledged skip TRANSFER_IGNORADA
# ============================================================
class TestFix869ITransferAcknowledged:
    """BRUCE1975: Bruce said 'espero' = transfer acknowledged, skip TRANSFER_IGNORADA."""

    def test_bruce_espero_skip_transfer_ignorada(self):
        """Bruce already said 'Claro, espero' → skip TRANSFER_IGNORADA."""
        conv = [
            ("bruce", "Buen día, ¿me comunica con el encargado?"),
            ("cliente", "Sí, permítame tantito"),
            ("bruce", "Claro, espero."),
            ("cliente", "Permítame un momento"),
            ("bruce", "¿Me podría dar su WhatsApp?"),
        ]
        bugs = ContentAnalyzer._check_transfer_ignorada(conv)
        assert not any(b["tipo"] == "TRANSFER_IGNORADA" for b in bugs)

    def test_no_espero_still_detects(self):
        """Without 'espero', transfer request ignored → still a bug."""
        conv = [
            ("bruce", "Buen día, le llamo de NIOVAL"),
            ("cliente", "Espere, le paso al encargado"),
            ("bruce", "¿Me podría dar su WhatsApp para enviarle el catálogo?"),
        ]
        bugs = ContentAnalyzer._check_transfer_ignorada(conv)
        assert any(b["tipo"] == "TRANSFER_IGNORADA" for b in bugs)

    def test_perfecto_espero_skip(self):
        """'Perfecto, espero' also counts as acknowledged."""
        conv = [
            ("bruce", "¿Está el encargado?"),
            ("cliente", "Sí, déjeme lo busco"),
            ("bruce", "Perfecto, espero."),
            ("cliente", "Permítame"),
            ("bruce", "¿Me da su número de WhatsApp?"),
        ]
        bugs = ContentAnalyzer._check_transfer_ignorada(conv)
        assert not any(b["tipo"] == "TRANSFER_IGNORADA" for b in bugs)
