"""
FIX 873: Bloquear re-pedido de WhatsApp si cliente ya rechazó en esta llamada.
BRUCE2549: Cliente dijo "No tengo WhatsApp" pero Bruce lo volvió a pedir turnos después.
"""
import re
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =========================================================
# Helpers compartidos
# =========================================================
def _make_history(*client_msgs):
    """Construye conversation_history con mensajes de cliente."""
    return [{"role": "user", "content": msg} for msg in client_msgs]


def _make_history_mixed(*pairs):
    """Construye historial alternando (role, content)."""
    return [{"role": role, "content": content} for role, content in pairs]


# Replicar regex FIX 873 para tests unitarios
_RECHAZA_WHATSAPP_873 = re.compile(
    r'(no\s+(?:tengo|tenemos|uso|usamos|manejo|manejamos|cuento\s+con|contamos\s+con|hay|tiene|tienen)\s+(?:whatsapp|watsapp|wats\b|wasa)|'
    r'(?:whatsapp|watsapp|wats\b|wasa)\s+no\b|'
    r'no[,.]?\s+(?:whatsapp|watsapp|wats\b|wasa)\s+no|'
    r'sin\s+(?:whatsapp|watsapp|wats\b|wasa)|'
    r'aqu[ií]\s+no\s+hay\s+(?:whatsapp|watsapp|wats\b|wasa))',
    re.IGNORECASE
)

_PIDE_WHATSAPP_873 = re.compile(r'whatsapp|wats?a?pp?', re.IGNORECASE)


# =========================================================
# Tests del regex _RECHAZA_WHATSAPP_873
# =========================================================
class TestFix873RegexRechazaWhatsapp:
    """El regex detecta variantes comunes de rechazo de WhatsApp."""

    @pytest.mark.parametrize("frase", [
        "no tengo whatsapp",
        "no tenemos whatsapp",
        "no uso whatsapp",
        "no usamos whatsapp",
        "no manejo whatsapp",
        "no manejamos whatsapp",
        "no cuento con whatsapp",
        "no contamos con whatsapp",
        "no hay whatsapp",
        "whatsapp no",
        "sin whatsapp",
        "aquí no hay whatsapp",
        "aqui no hay whatsapp",
        "no tengo watsapp",
        "no tengo wats",
        "WhatsApp no, no tengo",
    ])
    def test_detecta_rechazo_whatsapp(self, frase):
        assert _RECHAZA_WHATSAPP_873.search(frase), f"No detectó rechazo: '{frase}'"

    @pytest.mark.parametrize("frase", [
        "sí tengo whatsapp",
        "mi whatsapp es 3312345678",
        "por whatsapp me puede enviar",
        "claro, whatsapp está bien",
        "el whatsapp del encargado es...",
    ])
    def test_no_falso_positivo(self, frase):
        assert not _RECHAZA_WHATSAPP_873.search(frase), f"Falso positivo: '{frase}'"


# =========================================================
# Tests del regex _PIDE_WHATSAPP_873
# =========================================================
class TestFix873RegexPideWhatsapp:
    """El regex detecta cuando la respuesta de Bruce menciona WhatsApp."""

    @pytest.mark.parametrize("resp", [
        "¿Le envío el catálogo por WhatsApp?",
        "¿Me puede dar su número de WhatsApp?",
        "¿Cuál es su WhatsApp?",
        "Le mando el catálogo por watsapp",
    ])
    def test_detecta_pedido_whatsapp(self, resp):
        assert _PIDE_WHATSAPP_873.search(resp)

    def test_no_detecta_correo(self):
        resp = "¿Me puede dar su correo electrónico?"
        assert not _PIDE_WHATSAPP_873.search(resp)


# =========================================================
# Tests de integración: lógica del post-filter FIX 873
# =========================================================
def _simular_fix873(respuesta_bruce, history, lead_data=None):
    """
    Simula exactamente la lógica del post-filter FIX 873 en agente_ventas.py.
    Retorna (respuesta_final, flag_sin_whatsapp_seteado).
    """
    if lead_data is None:
        lead_data = {}

    _sin_whatsapp_antes = lead_data.get("sin_whatsapp", False)

    if _PIDE_WHATSAPP_873.search(respuesta_bruce) and not lead_data.get("sin_whatsapp"):
        _rechazo_previo = any(
            _RECHAZA_WHATSAPP_873.search(msg.get('content', ''))
            for msg in history
            if msg.get('role') == 'user'
        )
        if _rechazo_previo:
            lead_data["sin_whatsapp"] = True
            _ya_tiene_correo = lead_data.get('correo') or lead_data.get('email')
            if _ya_tiene_correo:
                respuesta_bruce = "Perfecto, le envío la información al correo que me proporcionó. Muchas gracias."
            else:
                respuesta_bruce = "Entendido. ¿Me puede dar un correo electrónico para enviarle el catálogo?"

    return respuesta_bruce, lead_data.get("sin_whatsapp", False)


class TestFix873Logica:
    """Tests de la lógica completa del post-filter FIX 873."""

    def test_bloquea_re_pedido_whatsapp_con_rechazo_previo(self):
        """CASO PRINCIPAL BRUCE2549: cliente rechazó → Bruce vuelve a pedir → debe bloquearse."""
        history = _make_history(
            "Buenos días",
            "No, no tengo whatsapp",
            "¿Qué productos venden?",
        )
        resp_bruce = "¿Le envío el catálogo por WhatsApp?"
        resultado, flag = _simular_fix873(resp_bruce, history)
        assert "correo" in resultado.lower()
        assert "whatsapp" not in resultado.lower()
        assert flag is True  # sin_whatsapp debe quedar en True

    def test_no_bloquea_sin_rechazo_previo(self):
        """Si cliente no rechazó WhatsApp, el pedido pasa normalmente."""
        history = _make_history(
            "Buenos días",
            "¿Qué productos venden?",
        )
        resp_bruce = "¿Le envío el catálogo por WhatsApp?"
        resultado, flag = _simular_fix873(resp_bruce, history)
        assert "whatsapp" in resultado.lower()
        assert flag is False

    def test_ya_tiene_correo_no_repide(self):
        """Si ya tiene correo capturado, confirma envío en lugar de pedir otro dato."""
        history = _make_history("No tengo whatsapp")
        resp_bruce = "¿Le envío el catálogo por WhatsApp?"
        lead = {"correo": "cliente@empresa.com"}
        resultado, flag = _simular_fix873(resp_bruce, history, lead)
        assert "correo" in resultado.lower()
        assert "proporcionó" in resultado.lower()
        assert "whatsapp" not in resultado.lower()

    def test_sin_whatsapp_ya_seteado_no_duplica(self):
        """Si lead_data ya tiene sin_whatsapp=True (FIX 516 lo seteó), FIX 873 no se activa."""
        history = _make_history("No tengo whatsapp")
        resp_bruce = "¿Le envío el catálogo por WhatsApp?"
        lead = {"sin_whatsapp": True}
        # Con sin_whatsapp ya True, el filtro FIX 516 (FILTRO 1B) ya lo manejó
        # FIX 873 no debe sobreescribir (condición: `not lead_data.get("sin_whatsapp")`)
        resultado, flag = _simular_fix873(resp_bruce, history, lead)
        # FIX 873 no actúa (FILTRO 1B ya lo manejó antes)
        assert resultado == "¿Le envío el catálogo por WhatsApp?"

    def test_variante_watsapp_detectada(self):
        """Variantes de escritura de WhatsApp también se detectan."""
        history = _make_history("no manejo watsapp")
        resp_bruce = "¿Me da su número de watsapp?"
        resultado, flag = _simular_fix873(resp_bruce, history)
        assert "correo" in resultado.lower()
        assert flag is True

    def test_rechazo_en_turno_antiguo_historico(self):
        """El rechazo puede estar en cualquier turno, no solo el último."""
        history = _make_history_mixed(
            ("user", "Buenos días"),
            ("assistant", "Le llamo de NIOVAL, ¿habla con el encargado?"),
            ("user", "No, no tengo whatsapp para eso"),
            ("assistant", "Entendido. ¿Me da un correo?"),
            ("user", "correo@empresa.com"),
            ("assistant", "Perfecto, le enviamos catálogo."),
            ("user", "¿Y qué más tienen?"),
        )
        resp_bruce = "¿También le puedo enviar ofertas por WhatsApp?"
        resultado, flag = _simular_fix873(resp_bruce, history)
        assert "correo" in resultado.lower()
        assert flag is True

    def test_respuesta_sin_whatsapp_pasa_intacta(self):
        """Respuesta que no menciona WhatsApp no se toca aunque haya rechazo."""
        history = _make_history("no tengo whatsapp")
        resp_bruce = "¿Le envío el catálogo por correo electrónico?"
        resultado, flag = _simular_fix873(resp_bruce, history)
        assert resultado == "¿Le envío el catálogo por correo electrónico?"
        assert flag is False  # sin_whatsapp solo se setea si el filtro actúa

    def test_no_modifica_historia_futura_por_error(self):
        """Si no hay rechazo previo, el lead_data no se modifica."""
        history = _make_history("Mi WhatsApp es 3312345678")
        resp_bruce = "¿Le envío el catálogo por WhatsApp?"
        lead = {}
        resultado, _ = _simular_fix873(resp_bruce, history, lead)
        assert "sin_whatsapp" not in lead


# =========================================================
# Tests de bug_detector: FIX 725 DATO_NEGADO_REINSISTIDO (sin cambios)
# =========================================================
class TestFix725DatoNegadoReinsistido:
    """Verifica que bug_detector sigue detectando el bug que FIX 873 previene."""

    def test_detecta_whatsapp_pedido_post_rechazo(self):
        from bug_detector import ContentAnalyzer
        # Nota: _check_dato_negado_reinsistido usa role="cliente"/"bruce" (minúsculas)
        conv = [
            ("cliente", "No tengo whatsapp"),
            ("bruce", "Entendido."),
            ("cliente", "¿Qué tienen de ofertas?"),
            ("bruce", "¿Le envío el catálogo por WhatsApp?"),
        ]
        bugs = ContentAnalyzer._check_dato_negado_reinsistido(conv)
        tipos = [b["tipo"] for b in bugs]
        assert "DATO_NEGADO_REINSISTIDO" in tipos

    def test_no_detecta_sin_reinsistencia(self):
        from bug_detector import ContentAnalyzer
        conv = [
            ("cliente", "No tengo whatsapp"),
            ("bruce", "Entendido. ¿Me da un correo?"),
            ("cliente", "correo@empresa.com"),
            ("bruce", "Perfecto, le envío información al correo."),
        ]
        bugs = ContentAnalyzer._check_dato_negado_reinsistido(conv)
        tipos = [b["tipo"] for b in bugs]
        assert "DATO_NEGADO_REINSISTIDO" not in tipos
