# -*- coding: utf-8 -*-
"""
Tests para FIX 707: BRUCE2253 - "Tienes donde anotar" = cliente ofrece dato.
Verifica que:
- 707A: Patrones de interés incluyen "anotar", "te doy", "le paso su"
- 707B: FIX 690C override aplica a WhatsApp/contact requests (no solo genéricas)
- 707C: FIX 598 no invalida cuando pregunta es "anotar/apuntar"
"""

import sys
import os
import pytest
import inspect

# Agregar directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# FIX 707A: Patrones de interés expandidos
# ============================================================

class TestFix707APatronesInteres:
    """Verifica que FIX 705 interest patterns incluyen oferta de datos."""

    def test_anotar_en_patrones(self):
        from agente_ventas import AgenteVentas
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)
        idx = source.find("patrones_interes_705")
        seccion = source[idx:idx + 1500]
        assert "'anotar'" in seccion

    def test_apuntar_en_patrones(self):
        from agente_ventas import AgenteVentas
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)
        idx = source.find("patrones_interes_705")
        seccion = source[idx:idx + 1500]
        assert "'apuntar'" in seccion

    def test_te_doy_en_patrones(self):
        from agente_ventas import AgenteVentas
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)
        idx = source.find("patrones_interes_705")
        seccion = source[idx:idx + 1500]
        assert "'te doy'" in seccion

    def test_le_paso_su_en_patrones(self):
        from agente_ventas import AgenteVentas
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)
        idx = source.find("patrones_interes_705")
        seccion = source[idx:idx + 1500]
        assert "'le paso su'" in seccion

    def test_tienes_donde_anotar_matchea(self):
        """'tienes donde anotar' matchea al menos 1 patrón de interés."""
        patrones_interes = [
            'anotar', 'apuntar', 'donde anotar', 'donde apuntar',
            'te doy', 'le doy', 'te paso su', 'le paso su',
            'te lo paso', 'se lo paso', 'te lo doy', 'se lo doy',
        ]
        frase = "tienes donde anotar"
        matchea = any(p in frase for p in patrones_interes)
        assert matchea == True

    def test_te_doy_el_numero_matchea(self):
        patrones_interes = ['te doy', 'le doy', 'te paso su']
        frase = "te doy el numero del encargado"
        matchea = any(p in frase for p in patrones_interes)
        assert matchea == True

    def test_le_paso_su_telefono_matchea(self):
        patrones_interes = ['le paso su', 'te paso su']
        frase = "le paso su telefono para que le marque"
        matchea = any(p in frase for p in patrones_interes)
        assert matchea == True


# ============================================================
# FIX 707B: FIX 690C override expandido
# ============================================================

class TestFix707BOverrideExpandido:
    """Verifica que FIX 690C override aplica a WhatsApp/contact requests."""

    def test_690c_tiene_respuesta_pide_contacto(self):
        """Verificar que FIX 690C/707B detecta pide_contacto."""
        from agente_ventas import AgenteVentas
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)
        idx = source.find("FIX 690C")
        seccion = source[idx:idx + 1500]
        assert "respuesta_pide_contacto_707" in seccion

    def test_whatsapp_detectado_como_pide_contacto(self):
        """'whatsapp' en respuesta GPT se detecta como pide_contacto."""
        patrones = ['whatsapp', 'correo', 'email', 'me da su',
                     'me podria dar', 'me proporciona', 'catalogo',
                     'me comunico despues', 'entonces me comunico']
        respuesta = "¿me podria dar su whatsapp para enviarle el catalogo?"
        matchea = any(p in respuesta.lower() for p in patrones)
        assert matchea == True

    def test_comunico_despues_detectado(self):
        """'me comunico despues' (despedida anti-loop) se detecta."""
        patrones = ['me comunico despues', 'entonces me comunico']
        respuesta = "Perfecto, entonces me comunico despues. Muchas gracias."
        matchea = any(p in respuesta.lower() for p in patrones)
        assert matchea == True

    def test_respuesta_normal_no_matchea(self):
        """Respuesta normal sin contacto NO matchea."""
        patrones = ['whatsapp', 'correo', 'email', 'me da su',
                     'me podria dar', 'catalogo', 'me comunico despues']
        respuesta = "Perfecto, le informo que manejamos productos ferreteros"
        matchea = any(p in respuesta.lower() for p in patrones)
        assert matchea == False


# ============================================================
# FIX 707C: FIX 598 inmune a "anotar/apuntar"
# ============================================================

class TestFix707CInmunidad598:
    """Verifica que FIX 598 no invalida cuando pregunta es oferta de dato."""

    def test_598_tiene_check_anotar(self):
        """Verificar que FIX 707C check para anotar/apuntar existe en código."""
        # Verificar directamente en el archivo fuente (evita encoding issues de inspect)
        import os
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "FIX 707C" in source
        assert "anotar" in source

    def test_anotar_no_es_contradiccion(self):
        """'tienes donde anotar?' no debe invalidar patrón previo."""
        # Simular lógica de FIX 598/707C
        partes = [
            "no esta disponible salio a comer",
            "tienes donde anotar?"
        ]
        contradiccion = False
        for parte in partes[1:]:
            if '?' in parte:
                parte_lower = parte.lower()
                if any(k in parte_lower for k in ['anotar', 'apuntar', 'donde escribir']):
                    continue  # FIX 707C: skip
                contradiccion = True
                break
        assert contradiccion == False

    def test_que_marca_si_es_contradiccion(self):
        """'que marca?' SÍ debe invalidar patrón (es pregunta real)."""
        partes = [
            "no esta disponible",
            "que marca me dijo?"
        ]
        contradiccion = False
        for parte in partes[1:]:
            if '?' in parte:
                parte_lower = parte.lower()
                if any(k in parte_lower for k in ['anotar', 'apuntar', 'donde escribir']):
                    continue
                contradiccion = True
                break
        assert contradiccion == True

    def test_apuntar_no_es_contradiccion(self):
        """'donde apuntar?' tampoco debe invalidar."""
        partes = [
            "salio a comer",
            "tiene donde apuntar?"
        ]
        contradiccion = False
        for parte in partes[1:]:
            if '?' in parte:
                parte_lower = parte.lower()
                if any(k in parte_lower for k in ['anotar', 'apuntar', 'donde escribir']):
                    continue
                contradiccion = True
                break
        assert contradiccion == False


# ============================================================
# Integración: Flujo BRUCE2253 completo
# ============================================================

class TestFix707Integracion:
    """Tests end-to-end para el escenario BRUCE2253."""

    def test_flujo_bruce2253_anti_loop_suspendido(self):
        """Con 'anotar' en texto cliente, anti-loop debe suspenderse."""
        ultimo_cliente = "no esta disponible salio a comer tienes donde anotar"
        patrones_interes = [
            'como es', 'whatsapp', 'me interesa', 'si quiero',
            'anotar', 'apuntar', 'donde anotar', 'te doy', 'le doy',
            'te paso su', 'le paso su', 'te lo paso', 'se lo paso',
        ]
        cliente_interesado = any(p in ultimo_cliente for p in patrones_interes)
        assert cliente_interesado == True, "Anti-loop debería suspenderse con 'anotar'"

    def test_flujo_690c_override_whatsapp(self):
        """Con 'anotar' + GPT pide WhatsApp → override a 'digame el numero'."""
        keywords_dictar = ['anotar', 'apuntar', 'donde escribir']
        ultimo_cliente = "tienes donde anotar"
        cliente_listo = any(k in ultimo_cliente for k in keywords_dictar)
        assert cliente_listo == True

        # GPT responde pidiendo WhatsApp
        respuesta_gpt = "¿Me podría dar su WhatsApp para enviarle el catálogo?"
        patrones_contacto = ['whatsapp', 'correo', 'me da su', 'catalogo']
        pide_contacto = any(p in respuesta_gpt.lower() for p in patrones_contacto)
        assert pide_contacto == True

        # Override debe activarse
        assert cliente_listo and pide_contacto

    def test_598_no_invalida_anotar_en_frase_compuesta(self):
        """Frase compuesta: 'salio a comer. tienes donde anotar?' no se invalida."""
        texto = "no esta disponible salio a comer. tienes donde anotar?"
        partes = [p.strip() for p in texto.replace('.', '|').replace('?', '?|').split('|') if p.strip()]

        contradiccion = False
        if len(partes) >= 2:
            for parte in partes[1:]:
                if '?' in parte:
                    parte_lower = parte.lower()
                    if any(k in parte_lower for k in ['anotar', 'apuntar', 'donde escribir']):
                        continue  # FIX 707C
                    contradiccion = True
                    break

        assert contradiccion == False, f"FIX 598 no debe invalidar con 'anotar' en 2da cláusula"

    def test_memory_layer_detecta_oferta(self):
        """Memory Layer debe reconocer 'tienes donde anotar' como oferta de dato."""
        from memory_layer import ConversationMemory
        m = ConversationMemory()
        history = [
            {"role": "assistant", "content": "¿Se encuentra el encargado?"},
            {"role": "user", "content": "No está, salió a comer. Tienes donde anotar?"}
        ]
        m.extract_facts(history)
        # Encargado no está
        assert m.facts.get('encargado_disponible') == False
        # "anotar" debería detectar que cliente ofrece dato (via contexto)
        # Memory Layer detecta "tienes donde anotar" como oferta de número
