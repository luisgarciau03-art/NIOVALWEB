"""Tests para FIX 868A-868H - Reducción bugs replay masivo 450 llamadas.

FIX 868A: Variantes encargado ausente (salió, se fue, no ha llegado)
FIX 868B: Variantes área equivocada (taller mecánico, somos tienda de, sucursales)
FIX 868C: Exemption callback-question en INTERRUPCION
FIX 868D: _CONFIRMACION_DATO_862 extendido (pedir contacto para catálogo)
FIX 868E: Esperando transferencia exemption en CLIENTE_HABLA_ULTIMO
FIX 868F: Smart dedup PREGUNTA_REPETIDA (STT artifact)
FIX 868G: Normalización puntuación para no_esta check
FIX 868H: Skip INTERRUPCION cuando señal no-negocio detectada
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from bug_detector import ContentAnalyzer


# ============================================================
# FIX 868A: Variantes encargado ausente
# ============================================================
class TestFix868AEncargadoAusenteVariantes:
    """BRUCE2271/2130/2041: 'salió'/'se fue' = manager absent, not interruption."""

    def test_salio_no_interrumpe(self):
        conv = [
            ("bruce", "Buen día, ¿me podría comunicar con el encargado?"),
            ("cliente", "es que salió el encargado ahorita no se encuentra"),
            ("bruce", "Entiendo. ¿Me podría proporcionar su número de WhatsApp?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)

    def test_ya_salio_no_interrumpe(self):
        conv = [
            ("bruce", "¿Me comunica con el encargado?"),
            ("cliente", "es que ya salió a comer"),
            ("bruce", "¿Me podría dar un correo para enviarle la información?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)

    def test_se_fue_no_interrumpe(self):
        conv = [
            ("bruce", "¿Me podría comunicar con el encargado?"),
            ("cliente", "es que se fue y no ha regresado"),
            ("bruce", "Entiendo. ¿WhatsApp o correo para enviarle el catálogo?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)

    def test_no_ha_llegado_no_interrumpe(self):
        conv = [
            ("bruce", "¿Está el encargado?"),
            ("cliente", "es que no ha llegado todavía"),
            ("bruce", "¿Me podría dar su número de teléfono?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)

    def test_fue_a_comer_no_interrumpe(self):
        conv = [
            ("bruce", "¿Se encuentra el encargado?"),
            ("cliente", "es que fue a comer"),
            ("bruce", "¿Me podría dar un WhatsApp para enviarle información?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)


# ============================================================
# FIX 868B: Variantes área equivocada
# ============================================================
class TestFix868BAreaEquivocadaVariantes:
    """BRUCE1893/2016/1730/2474: taller mecánico, somos tiendas de, sucursales."""

    def test_taller_mecanico_despedida_apropiada(self):
        conv = [
            ("bruce", "Le llamo de parte de NIOVAL para ofrecerle nuestro catálogo de ferretería"),
            ("cliente", "es que es un taller mecánico, no es ferretería"),
            ("bruce", "Entiendo, disculpe la molestia. Que tenga buen día."),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)

    def test_somos_tiendas_de_no_interrupcion(self):
        conv = [
            ("bruce", "Le llamo de NIOVAL con catálogo de ferretería"),
            ("cliente", "es que somos tiendas de marca truper y solo vendemos eso"),
            ("bruce", "¿Le podría proporcionar su WhatsApp para enviarle el catálogo?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)

    def test_sucursales_no_interrupcion(self):
        conv = [
            ("bruce", "Le llamo de parte de NIOVAL"),
            ("cliente", "es que estás hablando a una de las sucursales"),
            ("bruce", "Entiendo, le pido disculpas. Que tenga buen día."),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)

    def test_nosotros_somos_las_no_interrupcion(self):
        conv = [
            ("bruce", "Le llamo de NIOVAL para ferretería"),
            ("cliente", "es que nosotros somos las tiendas, no compramos así"),
            ("bruce", "Entiendo, disculpe. Buen día."),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)


# ============================================================
# FIX 868C: Exemption callback-question
# ============================================================
class TestFix868CCallbackQuestion:
    """BRUCE2130: Bruce asks callback hour = not interruption."""

    def test_a_que_hora_no_interrumpe(self):
        conv = [
            ("bruce", "¿Está el encargado?"),
            ("cliente", "es que no ha llegado, viene más tarde"),
            ("bruce", "¿A qué hora me recomienda llamarle?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)

    def test_cuando_regresa_no_interrumpe(self):
        conv = [
            ("bruce", "¿Se encuentra el dueño?"),
            ("cliente", "es que salió hace rato"),
            ("bruce", "Entiendo, ¿cuándo regresa para poder llamarle?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)


# ============================================================
# FIX 868D: _CONFIRMACION_DATO_862 extendido
# ============================================================
class TestFix868DConfirmacionDato:
    """BRUCE2214: pedir contacto para catálogo = no es nueva oferta de catálogo."""

    def test_proporcionar_whatsapp_enviar_no_catalogo(self):
        texto = "¿Me podría proporcionar su WhatsApp para enviarle el catálogo?"
        assert ContentAnalyzer._CONFIRMACION_DATO_862.search(texto)

    def test_pasar_correo_mandar_catalogo(self):
        texto = "¿Me puede pasar su correo para mandarle la información?"
        assert ContentAnalyzer._CONFIRMACION_DATO_862.search(texto)

    def test_envio_catalogo_por(self):
        texto = "Le envío el catálogo por WhatsApp"
        assert ContentAnalyzer._CONFIRMACION_DATO_862.search(texto)

    def test_oferta_real_no_excluida(self):
        texto = "Contamos con un amplio catálogo de más de 20,000 productos"
        assert not ContentAnalyzer._CONFIRMACION_DATO_862.search(texto)


# ============================================================
# FIX 868E: Esperando transferencia exemption
# ============================================================
class TestFix868EEsperandoTransferencia:
    """BRUCE1817: Bruce in wait mode = client speaking last is expected."""

    def test_claro_espero_skip_cliente_habla_ultimo(self):
        conv = [
            ("bruce", "Buen día, ¿me podría comunicar con el encargado?"),
            ("cliente", "Sí, déjeme lo busco"),
            ("bruce", "Claro, espero."),
            ("cliente", "Ándele, ahorita se lo paso"),
        ]
        bugs = ContentAnalyzer._check_cliente_habla_ultimo(conv)
        assert not any(b["tipo"] == "CLIENTE_HABLA_ULTIMO" for b in bugs)

    def test_perfecto_espero_skip(self):
        conv = [
            ("bruce", "¿Está el encargado?"),
            ("cliente", "Sí, espere tantito"),
            ("bruce", "Perfecto, espero."),
            ("cliente", "Ya va a venir"),
        ]
        bugs = ContentAnalyzer._check_cliente_habla_ultimo(conv)
        assert not any(b["tipo"] == "CLIENTE_HABLA_ULTIMO" for b in bugs)

    def test_sin_espero_si_detecta(self):
        """FIX 892: CLIENTE_HABLA_ULTIMO desactivado (limitacion Twilio)."""
        conv = [
            ("bruce", "Buen día, le llamo de NIOVAL"),
            ("cliente", "Sí, dígame"),
            ("bruce", "Tenemos un catálogo de más de 20,000 productos"),
            ("cliente", "Ah ok, y qué productos manejan"),
        ]
        bugs = ContentAnalyzer._check_cliente_habla_ultimo(conv)
        assert not any(b["tipo"] == "CLIENTE_HABLA_ULTIMO" for b in bugs)


# ============================================================
# FIX 868F: Smart dedup PREGUNTA_REPETIDA (STT artifact)
# ============================================================
class TestFix868FSmartDedup:
    """BRUCE1885/1895: STT duplicates client → Bruce template repeats → false positive."""

    def test_stt_duplicate_skipped(self):
        """When client says same thing twice (STT artifact), skip Bruce repeat."""
        conv = [
            ("bruce", "¿Me podría dar su WhatsApp?"),
            ("cliente", "No se encuentra, mañana a las once"),
            ("bruce", "Entiendo, ¿le marco mañana entonces?"),
            ("cliente", "No se encuentra, mañana a las once"),
            ("bruce", "Entiendo, ¿le marco mañana entonces?"),
        ]
        respuestas = [t for r, t in conv if r == "bruce"]
        bugs = ContentAnalyzer._check_pregunta_repetida(respuestas, conv)
        assert not any(b["tipo"] == "PREGUNTA_REPETIDA" for b in bugs)

    def test_real_repeat_still_detected(self):
        """When client says different things, Bruce repeating IS a bug."""
        conv = [
            ("bruce", "¿Me podría dar su WhatsApp?"),
            ("cliente", "No tengo WhatsApp"),
            ("bruce", "¿Me podría dar su WhatsApp?"),
            ("cliente", "Ya le dije que no tengo"),
            ("bruce", "¿Me podría dar su WhatsApp?"),
        ]
        respuestas = [t for r, t in conv if r == "bruce"]
        bugs = ContentAnalyzer._check_pregunta_repetida(respuestas, conv)
        assert any(b["tipo"] == "PREGUNTA_REPETIDA" for b in bugs)

    def test_no_conv_still_works(self):
        """Without conv parameter, legacy behavior works."""
        respuestas = [
            "¿Me podría dar su WhatsApp?",
            "¿Me podría dar su WhatsApp?",
            "¿Me podría dar su WhatsApp?",
        ]
        bugs = ContentAnalyzer._check_pregunta_repetida(respuestas)
        assert any(b["tipo"] == "PREGUNTA_REPETIDA" for b in bugs)


# ============================================================
# FIX 868G: Normalización puntuación para no_esta check
# ============================================================
class TestFix868GNormalizacionPuntuacion:
    """BRUCE2474: 'No, está hablando' → comma broke 'no está' check."""

    def test_no_comma_esta_normalizado(self):
        conv = [
            ("bruce", "¿Me podría comunicar con el encargado?"),
            ("cliente", "es que no, está hablando por teléfono ahorita"),
            ("bruce", "¿Me podría dar su WhatsApp para enviarle el catálogo?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)


# ============================================================
# FIX 868H: Skip INTERRUPCION cuando no-negocio
# ============================================================
class TestFix868HSkipInterrupcionNoNegocio:
    """BRUCE2016/1730: no-negocio signal → skip INTERRUPCION (AREA_EQUIVOCADA handles)."""

    def test_somos_tiendas_que_skip_interrupcion(self):
        conv = [
            ("bruce", "Le llamo de NIOVAL con catálogo ferretero"),
            ("cliente", "es que somos tiendas que solo vendemos marca propia"),
            ("bruce", "¿Le podría proporcionar su WhatsApp para enviarle el catálogo?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)

    def test_no_es_ferreteria_skip_interrupcion(self):
        conv = [
            ("bruce", "Le llamo de NIOVAL"),
            ("cliente", "es que no es ferretería, aquí es un taller"),
            ("bruce", "Entiendo. ¿Le podría dar mi número por si necesita algo?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert not any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)

    def test_real_interrupcion_still_detected(self):
        """Regular interruption without no-negocio signal still detected."""
        conv = [
            ("bruce", "¿En qué le puedo ayudar?"),
            ("cliente", "es que estamos buscando proveedores porque"),
            ("bruce", "¡Excelente! ¿Me da su WhatsApp?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        assert any(b["tipo"] == "INTERRUPCION_CONVERSACIONAL" for b in bugs)
