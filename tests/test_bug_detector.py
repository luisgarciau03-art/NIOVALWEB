"""
Tests para bug_detector.py (FIX 632 + FIX 637).

Verifica los 3 niveles de deteccion:
- Bugs tecnicos (FIX 632): BRUCE_MUDO, LOOP, SILENCIO, etc.
- Errores de contenido (FIX 637): PREGUNTA_REPETIDA, DATO_IGNORADO, etc.
- Evaluacion GPT (FIX 637): Estructura del evaluador

Markers: @pytest.mark.bug_detector
"""

import sys
import os
import pytest

# Asegurar que el directorio del proyecto este en el path
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from bug_detector import (
    CallEventTracker, BugDetector, ContentAnalyzer,
    CRITICO, ALTO, MEDIO
)


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def tracker():
    """Tracker basico para una llamada."""
    return CallEventTracker("CA_test123", "BRUCE9999", "+526621234567")


@pytest.fixture
def tracker_con_conversacion():
    """Tracker con una conversacion tipica de Bruce."""
    t = CallEventTracker("CA_test456", "BRUCE2070", "+526629876543")
    t.emit("BRUCE_RESPONDE", {"texto": "Me comunico de la marca nioval, trabajamos productos ferreteros."})
    t.emit("CLIENTE_DICE", {"texto": "Ah si, que necesita?"})
    t.emit("BRUCE_RESPONDE", {"texto": "Le puedo enviar nuestro catalogo de productos, cual es su WhatsApp?"})
    t.emit("CLIENTE_DICE", {"texto": "Si, es el 6621234567"})
    t.emit("BRUCE_RESPONDE", {"texto": "Perfecto, le envio el catalogo. Muchas gracias por su tiempo."})
    return t


# ============================================================
# BUGS TECNICOS (FIX 632)
# ============================================================

class TestBugsTecnicos:
    """Tests para los 5 bugs tecnicos originales."""

    @pytest.mark.bug_detector
    def test_bruce_mudo(self, tracker):
        """TwiML enviado pero audio nunca fetcheado → BRUCE_MUDO."""
        tracker.emit("TWIML_ENVIADO")
        tracker.emit("TWIML_ENVIADO")
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        assert "BRUCE_MUDO" in tipos
        bug = next(b for b in bugs if b["tipo"] == "BRUCE_MUDO")
        assert bug["severidad"] == CRITICO
        assert bug["categoria"] == "tecnico"

    @pytest.mark.bug_detector
    def test_no_bruce_mudo_con_audio(self, tracker):
        """TwiML + audio fetch → NO es BRUCE_MUDO."""
        tracker.emit("TWIML_ENVIADO")
        tracker.emit("AUDIO_FETCH")
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        assert "BRUCE_MUDO" not in tipos

    @pytest.mark.bug_detector
    def test_loop_detectado(self, tracker):
        """Misma respuesta 3+ veces → LOOP."""
        for _ in range(4):
            tracker.emit("BRUCE_RESPONDE", {"texto": "Le puedo enviar nuestro catalogo de productos."})
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        assert "LOOP" in tipos

    @pytest.mark.bug_detector
    def test_no_loop_respuestas_diferentes(self, tracker):
        """Respuestas diferentes → NO es LOOP."""
        tracker.emit("BRUCE_RESPONDE", {"texto": "Le puedo enviar nuestro catalogo."})
        tracker.emit("BRUCE_RESPONDE", {"texto": "Cual es su WhatsApp?"})
        tracker.emit("BRUCE_RESPONDE", {"texto": "Perfecto, muchas gracias."})
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        assert "LOOP" not in tipos

    @pytest.mark.bug_detector
    def test_silencio_prolongado(self, tracker):
        """Cliente dice "Bueno?" 2+ veces → SILENCIO_PROLONGADO."""
        tracker.emit("CLIENTE_DICE", {"texto": "Bueno?"})
        tracker.emit("CLIENTE_DICE", {"texto": "Hola?"})
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        assert "SILENCIO_PROLONGADO" in tipos

    @pytest.mark.bug_detector
    def test_patron_invalidado_frecuente(self, tracker):
        """3+ patrones invalidados → PATRON_INVALIDADO_FRECUENTE."""
        for _ in range(4):
            tracker.emit("PATRON_INVALIDADO")
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        assert "PATRON_INVALIDADO_FRECUENTE" in tipos

    @pytest.mark.bug_detector
    def test_respuesta_vacia(self, tracker):
        """GPT vacio 2+ veces → RESPUESTA_VACIA."""
        tracker.emit("RESPUESTA_VACIA")
        tracker.emit("RESPUESTA_VACIA")
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        assert "RESPUESTA_VACIA" in tipos


# ============================================================
# ERRORES DE CONTENIDO (FIX 637)
# ============================================================

class TestPreguntaRepetida:
    """FIX 637: Detectar cuando Bruce repite la misma pregunta."""

    @pytest.mark.bug_detector
    def test_pregunta_repetida_detectada(self, tracker):
        """Bruce pregunta lo mismo 2 veces → PREGUNTA_REPETIDA."""
        tracker.emit("BRUCE_RESPONDE", {"texto": "Me comunico de nioval. Cual es su numero de WhatsApp?"})
        tracker.emit("CLIENTE_DICE", {"texto": "No tengo ahorita"})
        tracker.emit("BRUCE_RESPONDE", {"texto": "Entiendo. Me podria dar su numero de WhatsApp?"})
        bugs = ContentAnalyzer.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        assert "PREGUNTA_REPETIDA" in tipos

    @pytest.mark.bug_detector
    def test_preguntas_diferentes_no_flag(self, tracker):
        """Preguntas distintas → NO flag."""
        tracker.emit("BRUCE_RESPONDE", {"texto": "Cual es su numero de WhatsApp?"})
        tracker.emit("CLIENTE_DICE", {"texto": "6621234567"})
        tracker.emit("BRUCE_RESPONDE", {"texto": "Y cual es su correo electronico?"})
        bugs = ContentAnalyzer.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        assert "PREGUNTA_REPETIDA" not in tipos


class TestDatoIgnorado:
    """FIX 637: Detectar cuando cliente da dato y Bruce lo ignora."""

    @pytest.mark.bug_detector
    def test_numero_ignorado(self, tracker):
        """Cliente da numero, Bruce pide numero de nuevo → DATO_IGNORADO."""
        tracker.emit("BRUCE_RESPONDE", {"texto": "Cual es su numero de WhatsApp?"})
        tracker.emit("CLIENTE_DICE", {"texto": "Es el 6629876543"})
        tracker.emit("BRUCE_RESPONDE", {"texto": "Me puede dar su numero de telefono?"})
        bugs = ContentAnalyzer.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        assert "DATO_IGNORADO" in tipos
        bug = next(b for b in bugs if b["tipo"] == "DATO_IGNORADO")
        assert bug["severidad"] == ALTO

    @pytest.mark.bug_detector
    def test_email_ignorado(self, tracker):
        """Cliente da email, Bruce pide email de nuevo → DATO_IGNORADO."""
        tracker.emit("BRUCE_RESPONDE", {"texto": "Cual es su correo?"})
        tracker.emit("CLIENTE_DICE", {"texto": "Es juan arroba gmail punto com"})
        tracker.emit("BRUCE_RESPONDE", {"texto": "Me puede dar su correo electronico?"})
        bugs = ContentAnalyzer.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        assert "DATO_IGNORADO" in tipos

    @pytest.mark.bug_detector
    def test_dato_no_ignorado_flujo_normal(self, tracker):
        """Cliente da numero, Bruce confirma → NO es DATO_IGNORADO."""
        tracker.emit("BRUCE_RESPONDE", {"texto": "Cual es su numero?"})
        tracker.emit("CLIENTE_DICE", {"texto": "Es el 6629876543"})
        tracker.emit("BRUCE_RESPONDE", {"texto": "Perfecto, le envio el catalogo. Gracias."})
        bugs = ContentAnalyzer.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        assert "DATO_IGNORADO" not in tipos


class TestOfertaPostDespedida:
    """FIX 637: Detectar cuando Bruce ofrece algo despues de despedirse."""

    @pytest.mark.bug_detector
    def test_oferta_despues_despedida(self, tracker):
        """Bruce se despide y luego ofrece catalogo → OFERTA_POST_DESPEDIDA."""
        tracker.emit("BRUCE_RESPONDE", {"texto": "Muchas gracias por su tiempo, que tenga excelente dia."})
        tracker.emit("CLIENTE_DICE", {"texto": "Igualmente"})
        tracker.emit("BRUCE_RESPONDE", {"texto": "Le puedo enviar nuestro catalogo de productos."})
        bugs = ContentAnalyzer.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        assert "OFERTA_POST_DESPEDIDA" in tipos

    @pytest.mark.bug_detector
    def test_despedida_normal_sin_oferta(self, tracker_con_conversacion):
        """Despedida normal sin oferta posterior → NO flag."""
        bugs = ContentAnalyzer.analyze(tracker_con_conversacion)
        tipos = [b["tipo"] for b in bugs]
        assert "OFERTA_POST_DESPEDIDA" not in tipos


class TestPitchRepetido:
    """FIX 637: Detectar cuando Bruce repite el pitch inicial."""

    @pytest.mark.bug_detector
    def test_pitch_repetido(self, tracker):
        """Bruce dice el pitch de nioval 2 veces → PITCH_REPETIDO."""
        tracker.emit("BRUCE_RESPONDE", {"texto": "Me comunico de la marca nioval, trabajamos productos ferreteros."})
        tracker.emit("CLIENTE_DICE", {"texto": "Ya me habia llamado"})
        tracker.emit("BRUCE_RESPONDE", {"texto": "Si, me comunico de la marca nioval, trabajamos productos ferreteros para su negocio."})
        bugs = ContentAnalyzer.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        assert "PITCH_REPETIDO" in tipos

    @pytest.mark.bug_detector
    def test_pitch_una_vez_ok(self, tracker):
        """Pitch dicho una sola vez → NO flag."""
        tracker.emit("BRUCE_RESPONDE", {"texto": "Me comunico de la marca nioval, trabajamos productos ferreteros."})
        tracker.emit("CLIENTE_DICE", {"texto": "Ok"})
        tracker.emit("BRUCE_RESPONDE", {"texto": "Le puedo enviar nuestro catalogo?"})
        bugs = ContentAnalyzer.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        assert "PITCH_REPETIDO" not in tipos


class TestCatalogoRepetido:
    """FIX 637: Detectar cuando Bruce ofrece catalogo 2+ veces."""

    @pytest.mark.bug_detector
    def test_catalogo_ofrecido_dos_veces(self, tracker):
        """Bruce ofrece catalogo 2 veces → CATALOGO_REPETIDO."""
        tracker.emit("BRUCE_RESPONDE", {"texto": "Le puedo enviar nuestro catalogo de productos."})
        tracker.emit("CLIENTE_DICE", {"texto": "Mmm no se"})
        tracker.emit("BRUCE_RESPONDE", {"texto": "Le envio el catalogo para que lo revise con calma."})
        bugs = ContentAnalyzer.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        assert "CATALOGO_REPETIDO" in tipos


# ============================================================
# TRACKER: CONVERSACION ORDENADA
# ============================================================

class TestConversacionOrdenada:
    """FIX 637: Verificar que el tracker mantiene conversacion en orden."""

    @pytest.mark.bug_detector
    def test_conversacion_interleaved(self, tracker):
        """Eventos se registran en orden correcto."""
        tracker.emit("BRUCE_RESPONDE", {"texto": "Hola"})
        tracker.emit("CLIENTE_DICE", {"texto": "Buenas"})
        tracker.emit("BRUCE_RESPONDE", {"texto": "Como esta?"})
        assert len(tracker.conversacion) == 3
        assert tracker.conversacion[0] == ("bruce", "Hola")
        assert tracker.conversacion[1] == ("cliente", "Buenas")
        assert tracker.conversacion[2] == ("bruce", "Como esta?")

    @pytest.mark.bug_detector
    def test_conversacion_y_listas_separadas(self, tracker):
        """Listas separadas y conversacion se mantienen sincronizadas."""
        tracker.emit("BRUCE_RESPONDE", {"texto": "A"})
        tracker.emit("CLIENTE_DICE", {"texto": "B"})
        tracker.emit("BRUCE_RESPONDE", {"texto": "C"})
        assert len(tracker.respuestas_bruce) == 2
        assert len(tracker.textos_cliente) == 1
        assert len(tracker.conversacion) == 3


# ============================================================
# GPT EVALUATOR: ESTRUCTURA (sin llamar GPT real)
# ============================================================

class TestGPTEvalStructure:
    """Verificar estructura del evaluador GPT sin hacer llamada real."""

    @pytest.mark.bug_detector
    def test_gpt_eval_no_ejecuta_con_pocos_turnos(self, tracker):
        """Con <3 turnos de Bruce, GPT eval no se ejecuta."""
        tracker.emit("BRUCE_RESPONDE", {"texto": "Hola"})
        tracker.emit("BRUCE_RESPONDE", {"texto": "Adios"})
        # _evaluar_con_gpt debe retornar [] con <3 turnos
        from bug_detector import _evaluar_con_gpt, GPT_EVAL_MIN_TURNOS
        assert len(tracker.respuestas_bruce) < GPT_EVAL_MIN_TURNOS
        resultado = _evaluar_con_gpt(tracker)
        assert resultado == []

    @pytest.mark.bug_detector
    def test_gpt_eval_prompt_exists(self):
        """El prompt de evaluacion GPT debe existir y contener instrucciones clave."""
        from bug_detector import _GPT_EVAL_PROMPT
        assert "NIOVAL" in _GPT_EVAL_PROMPT
        assert "RESPUESTA_INCORRECTA" in _GPT_EVAL_PROMPT
        assert "JSON" in _GPT_EVAL_PROMPT


# ============================================================
# BugDetector.analyze: INTEGRACION
# ============================================================

class TestBugDetectorIntegracion:
    """Verificar que analyze() combina bugs tecnicos + contenido."""

    @pytest.mark.bug_detector
    def test_multiples_tipos_de_bugs(self, tracker):
        """Una llamada puede tener bugs tecnicos Y de contenido."""
        # Bug tecnico: respuesta vacia
        tracker.emit("RESPUESTA_VACIA")
        tracker.emit("RESPUESTA_VACIA")
        # Bug contenido: pitch repetido
        tracker.emit("BRUCE_RESPONDE", {"texto": "Me comunico de la marca nioval, trabajamos productos ferreteros."})
        tracker.emit("BRUCE_RESPONDE", {"texto": "Somos la marca nioval, trabajamos productos ferreteros."})
        bugs = BugDetector.analyze(tracker)
        categorias = set(b.get("categoria") for b in bugs)
        assert "tecnico" in categorias
        assert "contenido" in categorias

    @pytest.mark.bug_detector
    def test_llamada_limpia_sin_bugs(self, tracker_con_conversacion):
        """Conversacion normal no debe generar bugs."""
        # Agregar TwiML y audio para evitar BRUCE_MUDO
        tracker_con_conversacion.emit("TWIML_ENVIADO")
        tracker_con_conversacion.emit("AUDIO_FETCH")
        bugs = BugDetector.analyze(tracker_con_conversacion)
        # Puede haber 0 bugs si la conversacion es limpia
        tipos_criticos = [b for b in bugs if b["severidad"] in (CRITICO, ALTO)]
        assert len(tipos_criticos) == 0

    @pytest.mark.bug_detector
    def test_categoria_siempre_presente(self, tracker):
        """Todos los bugs deben tener campo 'categoria'."""
        tracker.emit("TWIML_ENVIADO")  # BRUCE_MUDO
        tracker.emit("RESPUESTA_VACIA")
        tracker.emit("RESPUESTA_VACIA")
        bugs = BugDetector.analyze(tracker)
        for bug in bugs:
            assert "categoria" in bug
            assert bug["categoria"] in ("tecnico", "contenido", "gpt_eval")
