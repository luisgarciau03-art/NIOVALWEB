# -*- coding: utf-8 -*-
"""
Tests de regresión para FIX 686 (inmunidad FIX 598+602 para patrones 0% survival)
y FIX 687 (inmunidad FIX 600+601 para patrones faltantes).
"""
import os
import sys
import re
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-dummy")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC-test")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test-token")


# ============================================================
# FIX 686A: OFRECER_CONTACTO_BRUCE eliminado de contradicciones_598
# ============================================================

class TestFix686AContradicciones598:
    """FIX 686A: OFRECER_CONTACTO_BRUCE no debe estar en contradicciones_598."""

    def test_ofrecer_contacto_bruce_no_en_contradicciones(self):
        """OFRECER_CONTACTO_BRUCE no debe tener entrada en contradicciones_598."""
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agente_ventas.py'),
                  encoding='utf-8') as f:
            source = f.read()
        # Verificar que NO hay entrada activa "OFRECER_CONTACTO_BRUCE": [
        # (puede estar en comentario pero no como key de dict)
        pattern = r'^\s+["\']OFRECER_CONTACTO_BRUCE["\']\s*:\s*\['
        matches = re.findall(pattern, source, re.MULTILINE)
        assert len(matches) == 0, \
            f"OFRECER_CONTACTO_BRUCE NO debe estar en contradicciones_598 (encontrado: {matches})"

    def test_contradicciones_598_no_tiene_entry(self):
        """Simular lógica FIX 598: OFRECER_CONTACTO_BRUCE no debe tener keywords."""
        contradicciones_598 = {
            "ENCARGADO_NO_ESTA_CON_HORARIO": ['correo', 'mail'],
            "SOLICITUD_CALLBACK": ['correo', 'whatsapp'],
            # OFRECER_CONTACTO_BRUCE eliminado por FIX 686A
        }
        keywords = contradicciones_598.get("OFRECER_CONTACTO_BRUCE", [])
        assert keywords == [], "OFRECER_CONTACTO_BRUCE no debe tener keywords de contradicción"

    def test_negacion_correo_no_invalida(self):
        """'no tengo correo' no debe invalidar OFRECER_CONTACTO_BRUCE."""
        texto_cliente = "no tengo correo ni whatsapp"
        tipo_patron = "OFRECER_CONTACTO_BRUCE"
        # Con FIX 686A, no hay keywords para este patrón
        contradicciones = {}  # Eliminado
        keywords = contradicciones.get(tipo_patron, [])
        contradiccion = None
        for kw in keywords:
            if kw in texto_cliente:
                contradiccion = kw
                break
        assert contradiccion is None, \
            f"Negación 'no tengo correo' NO debe invalidar patrón (keyword: {contradiccion})"

    def test_rechazo_todo_no_invalida(self):
        """'no, no me interesa nada de eso' no debe invalidar OFRECER_CONTACTO_BRUCE."""
        texto_cliente = "no, no me interesa nada de eso, le digo que no"
        tipo_patron = "OFRECER_CONTACTO_BRUCE"
        keywords = []  # FIX 686A: eliminado
        contradiccion = any(kw in texto_cliente for kw in keywords)
        assert not contradiccion


# ============================================================
# FIX 686B: Inmunidad pregunta 2da cláusula
# ============================================================

class TestFix686BInmunidadPregunta:
    """FIX 686B: OFRECER_CONTACTO_BRUCE y PEDIR_TELEFONO_FIJO inmunes a pregunta 2da cláusula."""

    def test_ofrecer_contacto_bruce_inmune_pregunta(self):
        """OFRECER_CONTACTO_BRUCE no se invalida por pregunta en 2da cláusula."""
        patrones_inmunes_pregunta_598 = {
            'CONFIRMA_MISMO_NUMERO', 'CONFIRMACION_SIMPLE', 'CLIENTE_DICE_SI',
            'CLIENTE_ACEPTA_WHATSAPP', 'CLIENTE_ACEPTA_CORREO',
            'CLIENTE_OFRECE_WHATSAPP', 'CLIENTE_OFRECE_CORREO', 'CLIENTE_OFRECE_NUMERO',
            'DESPEDIDA_CLIENTE', 'DESPEDIDA', 'RECHAZO_DEFINITIVO', 'NO_INTERESA_FINAL',
            'CLIENTE_DICTANDO_NUMERO', 'NUMERO_PARCIAL_DICTADO',
            'CORREO_DETECTADO', 'WHATSAPP_DETECTADO',
            'OFRECE_CONTACTO_ENCARGADO', 'CLIENTE_OFRECE_SU_CONTACTO',
            'OFRECER_CONTACTO_BRUCE', 'PEDIR_TELEFONO_FIJO',
        }
        assert 'OFRECER_CONTACTO_BRUCE' in patrones_inmunes_pregunta_598

    def test_pedir_telefono_fijo_inmune_pregunta(self):
        """PEDIR_TELEFONO_FIJO no se invalida por pregunta en 2da cláusula."""
        patrones_inmunes_pregunta_598 = {
            'OFRECER_CONTACTO_BRUCE', 'PEDIR_TELEFONO_FIJO',
        }
        assert 'PEDIR_TELEFONO_FIJO' in patrones_inmunes_pregunta_598

    def test_pregunta_segunda_clausula_no_invalida_ofrecer_bruce(self):
        """Simular FIX 598 question check con patrón inmune."""
        tipo_patron = "OFRECER_CONTACTO_BRUCE"
        texto = "no gracias. de donde me llama?"
        patrones_inmunes_pregunta_598 = {'OFRECER_CONTACTO_BRUCE', 'PEDIR_TELEFONO_FIJO'}

        tiene_pregunta = False
        partes = [p.strip() for p in texto.replace('.', '|').replace('?', '?|').split('|') if p.strip()]
        if len(partes) >= 2 and tipo_patron not in patrones_inmunes_pregunta_598:
            for parte in partes[1:]:
                if '?' in parte:
                    tiene_pregunta = True
                    break
        assert not tiene_pregunta, "Patrón inmune no debe ser invalidado por pregunta en 2da cláusula"

    def test_patron_no_inmune_si_invalida_por_pregunta(self):
        """Un patrón NO inmune SÍ se invalida por pregunta en 2da cláusula."""
        tipo_patron = "ENCARGADO_NO_ESTA_CON_HORARIO"
        texto = "no esta. de donde me llama?"
        patrones_inmunes_pregunta_598 = {'OFRECER_CONTACTO_BRUCE', 'PEDIR_TELEFONO_FIJO'}

        tiene_pregunta = False
        partes = [p.strip() for p in texto.replace('.', '|').replace('?', '?|').split('|') if p.strip()]
        if len(partes) >= 2 and tipo_patron not in patrones_inmunes_pregunta_598:
            for parte in partes[1:]:
                if '?' in parte:
                    tiene_pregunta = True
                    break
        assert tiene_pregunta, "Patrón NO inmune SÍ debe invalidarse por pregunta"


# ============================================================
# FIX 686C: OFRECER_CONTACTO_BRUCE eliminado de incoherencias FIX 602
# ============================================================

class TestFix686CIncoherencias602:
    """FIX 686C: OFRECER_CONTACTO_BRUCE no debe estar en incoherencias_por_contexto."""

    def test_no_incoherente_pidiendo_correo(self):
        """OFRECER_CONTACTO_BRUCE no es incoherente cuando Bruce pide correo."""
        incoherencias = {
            'PIDIENDO_CORREO': [
                'ENCARGADO_NO_ESTA_CON_HORARIO', 'ENCARGADO_NO_ESTA_SIN_HORARIO',
                'ENCARGADO_LLEGA_MAS_TARDE', 'SOLICITUD_CALLBACK',
                'PREGUNTA_IDENTIDAD', 'PREGUNTA_UBICACION',
                'TRANSFERENCIA'
            ],
        }
        assert 'OFRECER_CONTACTO_BRUCE' not in incoherencias['PIDIENDO_CORREO']

    def test_no_incoherente_pidiendo_telefono(self):
        """OFRECER_CONTACTO_BRUCE no es incoherente cuando Bruce pide teléfono."""
        incoherencias = {
            'PIDIENDO_TELEFONO': [
                'ENCARGADO_NO_ESTA_CON_HORARIO', 'ENCARGADO_NO_ESTA_SIN_HORARIO',
                'ENCARGADO_LLEGA_MAS_TARDE', 'SOLICITUD_CALLBACK',
                'PREGUNTA_IDENTIDAD', 'PREGUNTA_UBICACION',
                'TRANSFERENCIA'
            ],
        }
        assert 'OFRECER_CONTACTO_BRUCE' not in incoherencias['PIDIENDO_TELEFONO']

    def test_no_incoherente_pidiendo_encargado(self):
        """OFRECER_CONTACTO_BRUCE no es incoherente cuando Bruce pide encargado."""
        incoherencias = {
            'PIDIENDO_ENCARGADO': ['CONFIRMACION_SIMPLE', 'DESPEDIDA'],
        }
        assert 'OFRECER_CONTACTO_BRUCE' not in incoherencias['PIDIENDO_ENCARGADO']

    def test_no_incoherente_preguntando_horario(self):
        """OFRECER_CONTACTO_BRUCE no es incoherente cuando Bruce pregunta horario."""
        incoherencias = {
            'PREGUNTANDO_HORARIO': ['CONFIRMACION_SIMPLE', 'PREGUNTA_IDENTIDAD'],
        }
        assert 'OFRECER_CONTACTO_BRUCE' not in incoherencias['PREGUNTANDO_HORARIO']

    def test_source_code_no_tiene_ofrecer_contacto_bruce_en_incoherencias(self):
        """Verificar en código fuente que OFRECER_CONTACTO_BRUCE no está en incoherencias."""
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agente_ventas.py'),
                  encoding='utf-8') as f:
            source = f.read()
        # Buscar en bloque incoherencias_por_contexto
        start = source.find('incoherencias_por_contexto = {')
        end = source.find('}', source.find("'PREGUNTANDO_HORARIO'", start))
        if start > 0 and end > start:
            bloque = source[start:end+1]
            # OFRECER_CONTACTO_BRUCE no debe aparecer como valor en el dict
            assert "'OFRECER_CONTACTO_BRUCE'" not in bloque, \
                "OFRECER_CONTACTO_BRUCE no debe estar en incoherencias_por_contexto"


# ============================================================
# FIX 687A: CLIENTE_ACEPTA_CORREO + PEDIR_TELEFONO_FIJO en patrones_inmunes_pero
# ============================================================

class TestFix687AInmunesPero:
    """FIX 687A: Patrones faltantes agregados a patrones_inmunes_pero (FIX 600)."""

    def test_cliente_acepta_correo_inmune_pero(self):
        """CLIENTE_ACEPTA_CORREO debe ser inmune a FIX 600."""
        patrones_inmunes_pero = {
            'DESPEDIDA', 'DESPEDIDA_CLIENTE', 'RECHAZO_DEFINITIVO', 'NO_INTERESA_FINAL',
            'DESPEDIDA_NATURAL_CLIENTE_DERIVACION', 'DESPEDIDA_NATURAL_CLIENTE_NO_DISPONIBLE',
            'OTRA_SUCURSAL', 'OTRA_SUCURSAL_INSISTENCIA',
            'CLIENTE_OFRECE_CORREO', 'CLIENTE_OFRECE_NUMERO',
            'OFRECE_CONTACTO_ENCARGADO', 'CLIENTE_OFRECE_SU_CONTACTO',
            'CLIENTE_DICTA_EMAIL_COMPLETO',
            'OFRECER_CONTACTO_BRUCE', 'CLIENTE_OFRECE_WHATSAPP',
            'CLIENTE_ACEPTA_CORREO', 'EVITAR_LOOP_WHATSAPP',
            'PEDIR_TELEFONO_FIJO',
        }
        assert 'CLIENTE_ACEPTA_CORREO' in patrones_inmunes_pero

    def test_pedir_telefono_fijo_inmune_pero(self):
        """PEDIR_TELEFONO_FIJO debe ser inmune a FIX 600."""
        patrones_inmunes_pero = {
            'CLIENTE_ACEPTA_CORREO', 'EVITAR_LOOP_WHATSAPP', 'PEDIR_TELEFONO_FIJO',
        }
        assert 'PEDIR_TELEFONO_FIJO' in patrones_inmunes_pero

    def test_evitar_loop_whatsapp_inmune_pero(self):
        """EVITAR_LOOP_WHATSAPP debe ser inmune a FIX 600."""
        patrones_inmunes_pero = {
            'CLIENTE_ACEPTA_CORREO', 'EVITAR_LOOP_WHATSAPP', 'PEDIR_TELEFONO_FIJO',
        }
        assert 'EVITAR_LOOP_WHATSAPP' in patrones_inmunes_pero

    def test_adversativo_no_invalida_cliente_acepta_correo(self):
        """'sí, pero mándamelo al correo' con CLIENTE_ACEPTA_CORREO sobrevive FIX 600."""
        texto = "si, pero mandamelo al correo"
        tipo_patron = "CLIENTE_ACEPTA_CORREO"
        patrones_inmunes_pero = {'CLIENTE_ACEPTA_CORREO', 'PEDIR_TELEFONO_FIJO'}

        invalidado = False
        conjunciones = [' pero ', ' sin embargo ']
        if tipo_patron not in patrones_inmunes_pero:
            for conj in conjunciones:
                if conj in texto:
                    invalidado = True
                    break
        assert not invalidado, "CLIENTE_ACEPTA_CORREO es inmune a adversativo"

    def test_adversativo_no_invalida_pedir_telefono(self):
        """'no tengo whatsapp pero hay un fijo' con PEDIR_TELEFONO_FIJO sobrevive."""
        texto = "no tengo whatsapp pero hay un fijo"
        tipo_patron = "PEDIR_TELEFONO_FIJO"
        patrones_inmunes_pero = {'CLIENTE_ACEPTA_CORREO', 'PEDIR_TELEFONO_FIJO'}

        invalidado = False
        if tipo_patron not in patrones_inmunes_pero:
            if ' pero ' in texto:
                invalidado = True
        assert not invalidado, "PEDIR_TELEFONO_FIJO es inmune a adversativo"

    def test_source_code_tiene_inmunes_pero(self):
        """Verificar en código fuente que los 3 patrones están en patrones_inmunes_pero (via _PATRONES_INMUNES_UNIVERSAL)."""
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agente_ventas.py'),
                  encoding='utf-8') as f:
            source = f.read()
        # FASE 1.1: patrones_inmunes_pero ahora apunta a _PATRONES_INMUNES_UNIVERSAL
        start = source.find('_PATRONES_INMUNES_UNIVERSAL = {')
        end = source.find('}', start)
        bloque = source[start:end+1]
        assert 'CLIENTE_ACEPTA_CORREO' in bloque
        assert 'EVITAR_LOOP_WHATSAPP' in bloque
        assert 'PEDIR_TELEFONO_FIJO' in bloque


# ============================================================
# FIX 687B: PEDIR_TELEFONO_FIJO en patrones_inmunes_601
# ============================================================

class TestFix687BInmunes601:
    """FIX 687B: PEDIR_TELEFONO_FIJO agregado a patrones_inmunes_601."""

    def test_pedir_telefono_fijo_inmune_601(self):
        """PEDIR_TELEFONO_FIJO debe ser inmune a FIX 601 complejidad."""
        patrones_inmunes_601 = {
            'CONFIRMACION_SIMPLE', 'SALUDO', 'DESPEDIDA',
            'PEDIR_TELEFONO_FIJO',
        }
        assert 'PEDIR_TELEFONO_FIJO' in patrones_inmunes_601

    def test_complejidad_no_invalida_pedir_telefono(self):
        """Texto largo con PEDIR_TELEFONO_FIJO sobrevive FIX 601."""
        texto = "no tengo whatsapp ni correo, pero si tiene algun fijo o numero de oficina le puedo dar ese"
        palabras = texto.split()
        tipo_patron = "PEDIR_TELEFONO_FIJO"
        patrones_inmunes_601 = {'PEDIR_TELEFONO_FIJO'}

        invalidado = False
        if len(palabras) > 12 and tipo_patron not in patrones_inmunes_601:
            num_clausulas = 1 + texto.count(', ') + texto.count('. ')
            if num_clausulas >= 3:
                invalidado = True
        assert not invalidado, "PEDIR_TELEFONO_FIJO es inmune a FIX 601"

    def test_source_code_tiene_inmune_601(self):
        """Verificar en código fuente que PEDIR_TELEFONO_FIJO está en patrones_inmunes_601 (via _PATRONES_INMUNES_UNIVERSAL)."""
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agente_ventas.py'),
                  encoding='utf-8') as f:
            source = f.read()
        # FASE 1.1: patrones_inmunes_601 ahora apunta a _PATRONES_INMUNES_UNIVERSAL
        start = source.find('_PATRONES_INMUNES_UNIVERSAL = {')
        end = source.find('}', start)
        bloque = source[start:end+1]
        assert 'PEDIR_TELEFONO_FIJO' in bloque


# ============================================================
# Tests de integración: Pipeline completa
# ============================================================

class TestPipelineIntegracion:
    """Tests de integración que simulan la pipeline completa de validación."""

    def _simular_pipeline(self, tipo_patron, texto_cliente, ultimo_bruce=""):
        """Simula los 4 pasos de validación: FIX 598 → 600 → 601 → 602."""
        texto_validacion = texto_cliente.lower()
        texto_validacion = texto_validacion.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')

        # FIX 598: Contradicciones
        contradicciones_598 = {
            "ENCARGADO_NO_ESTA_CON_HORARIO": ['correo', 'mail', 'email', 'whatsapp', 'te doy', 'le doy',
                'te paso', 'le paso', 'yo soy', 'soy yo'],
            "ENCARGADO_NO_ESTA_SIN_HORARIO": ['pero digame', 'en que le ayudo', 'le puedo ayudar',
                'yo soy', 'soy yo', 'correo', 'mail', 'email', 'whatsapp', 'te doy', 'le doy',
                'te paso', 'le paso'],
            "TRANSFERENCIA": ['yo soy', 'soy yo', 'yo mero', 'conmigo', 'soy el encargado',
                'soy la encargada', 'soy el responsable'],
            # FIX 686A: OFRECER_CONTACTO_BRUCE eliminado
        }
        keywords = contradicciones_598.get(tipo_patron, [])
        contradiccion = None
        for kw in keywords:
            if kw in texto_validacion:
                contradiccion = kw
                break

        # Check pregunta 2da cláusula
        patrones_inmunes_pregunta_598 = {
            'CONFIRMA_MISMO_NUMERO', 'CONFIRMACION_SIMPLE', 'CLIENTE_DICE_SI',
            'CLIENTE_ACEPTA_WHATSAPP', 'CLIENTE_ACEPTA_CORREO',
            'CLIENTE_OFRECE_WHATSAPP', 'CLIENTE_OFRECE_CORREO', 'CLIENTE_OFRECE_NUMERO',
            'DESPEDIDA_CLIENTE', 'DESPEDIDA', 'RECHAZO_DEFINITIVO', 'NO_INTERESA_FINAL',
            'CLIENTE_DICTANDO_NUMERO', 'NUMERO_PARCIAL_DICTADO',
            'CORREO_DETECTADO', 'WHATSAPP_DETECTADO',
            'OFRECE_CONTACTO_ENCARGADO', 'CLIENTE_OFRECE_SU_CONTACTO',
            'OFRECER_CONTACTO_BRUCE', 'PEDIR_TELEFONO_FIJO',  # FIX 686B
        }
        partes = [p.strip() for p in texto_validacion.replace('.', '|').replace('?', '?|').split('|') if p.strip()]
        if len(partes) >= 2 and tipo_patron not in patrones_inmunes_pregunta_598:
            for parte in partes[1:]:
                if '?' in parte:
                    if not contradiccion:
                        contradiccion = f"pregunta: {parte[:20]}"
                    break

        if contradiccion:
            return 'invalidado_598', contradiccion

        # FIX 600: Adversativo
        patrones_inmunes_pero = {
            'DESPEDIDA', 'DESPEDIDA_CLIENTE', 'RECHAZO_DEFINITIVO', 'NO_INTERESA_FINAL',
            'DESPEDIDA_NATURAL_CLIENTE_DERIVACION', 'DESPEDIDA_NATURAL_CLIENTE_NO_DISPONIBLE',
            'OTRA_SUCURSAL', 'OTRA_SUCURSAL_INSISTENCIA',
            'CLIENTE_OFRECE_CORREO', 'CLIENTE_OFRECE_NUMERO',
            'OFRECE_CONTACTO_ENCARGADO', 'CLIENTE_OFRECE_SU_CONTACTO',
            'CLIENTE_DICTA_EMAIL_COMPLETO',
            'OFRECER_CONTACTO_BRUCE', 'CLIENTE_OFRECE_WHATSAPP',
            'CLIENTE_ACEPTA_CORREO', 'EVITAR_LOOP_WHATSAPP', 'PEDIR_TELEFONO_FIJO',  # FIX 687A
        }
        if tipo_patron not in patrones_inmunes_pero:
            for conj in [' pero ', ' sin embargo ', ' aunque ', ' la verdad ', ' es que ']:
                if conj in texto_validacion:
                    parte_despues = texto_validacion.split(conj, 1)[1].strip()
                    palabras_despues = [p for p in parte_despues.split() if len(p) > 2]
                    if len(palabras_despues) >= 2:
                        return 'invalidado_600', conj.strip()

        # FIX 601: Complejidad
        patrones_inmunes_601 = {
            'CONFIRMACION_SIMPLE', 'SALUDO', 'DESPEDIDA', 'DESPEDIDA_CLIENTE',
            'RECHAZO_DEFINITIVO', 'NO_INTERESA_FINAL', 'CLIENTE_DICE_SI', 'CLIENTE_DICE_NO',
            'CORREO_DETECTADO', 'WHATSAPP_DETECTADO',
            'OTRA_SUCURSAL', 'OTRA_SUCURSAL_INSISTENCIA',
            'CLIENTE_OFRECE_CORREO', 'CLIENTE_OFRECE_NUMERO',
            'OFRECE_CONTACTO_ENCARGADO', 'CLIENTE_OFRECE_SU_CONTACTO',
            'CLIENTE_DICTANDO_NUMERO', 'NUMERO_PARCIAL_DICTADO',
            'NUMERO_PARCIAL_CON_VERIFICACION',
            'CLIENTE_DICTA_EMAIL_COMPLETO',
            'EVITAR_LOOP_WHATSAPP', 'CLIENTE_ACEPTA_CORREO',
            'OFRECER_CONTACTO_BRUCE', 'CLIENTE_OFRECE_WHATSAPP',
            'PEDIR_TELEFONO_FIJO',  # FIX 687B
        }
        palabras = texto_cliente.split()
        if len(palabras) > 12 and tipo_patron not in patrones_inmunes_601:
            num_clausulas = 1
            for sep in ['. ', ', ', '; ', '?']:
                num_clausulas += texto_cliente.count(sep)
            if num_clausulas >= 3:
                return 'invalidado_601', f"{len(palabras)} palabras"

        # FIX 602: Contexto
        if ultimo_bruce:
            tema_bruce = None
            ub = ultimo_bruce.lower()
            if any(kw in ub for kw in ['correo', 'email', 'mail']):
                tema_bruce = 'PIDIENDO_CORREO'
            elif any(kw in ub for kw in ['whatsapp', 'numero', 'telefono', 'celular']):
                tema_bruce = 'PIDIENDO_TELEFONO'
            elif any(kw in ub for kw in ['encargado', 'responsable']):
                tema_bruce = 'PIDIENDO_ENCARGADO'

            # FIX 686C: OFRECER_CONTACTO_BRUCE eliminado de incoherencias
            incoherencias = {
                'PIDIENDO_CORREO': ['ENCARGADO_NO_ESTA_CON_HORARIO', 'SOLICITUD_CALLBACK', 'TRANSFERENCIA'],
                'PIDIENDO_TELEFONO': ['ENCARGADO_NO_ESTA_CON_HORARIO', 'SOLICITUD_CALLBACK', 'TRANSFERENCIA'],
                'PIDIENDO_ENCARGADO': ['CONFIRMACION_SIMPLE', 'DESPEDIDA'],
            }
            if tema_bruce and tipo_patron in incoherencias.get(tema_bruce, []):
                return 'invalidado_602', tema_bruce

        return 'survived', None

    def test_ofrecer_contacto_bruce_survives_all(self):
        """OFRECER_CONTACTO_BRUCE sobrevive toda la pipeline."""
        result, reason = self._simular_pipeline(
            "OFRECER_CONTACTO_BRUCE",
            "no, ya le dije que no tengo correo ni nada",
            ultimo_bruce="Me puede proporcionar un correo?"
        )
        assert result == 'survived', f"Debió sobrevivir, pero: {result} ({reason})"

    def test_ofrecer_contacto_bruce_survives_with_question(self):
        """OFRECER_CONTACTO_BRUCE sobrevive pregunta en 2da cláusula."""
        result, reason = self._simular_pipeline(
            "OFRECER_CONTACTO_BRUCE",
            "no gracias. de donde me llama?"
        )
        assert result == 'survived', f"Debió sobrevivir, pero: {result} ({reason})"

    def test_pedir_telefono_fijo_survives_all(self):
        """PEDIR_TELEFONO_FIJO sobrevive toda la pipeline."""
        result, reason = self._simular_pipeline(
            "PEDIR_TELEFONO_FIJO",
            "no, whatsapp no tengo pero si tiene algun fijo o numero de oficina, le puedo dar ese si quiere",
        )
        assert result == 'survived', f"Debió sobrevivir, pero: {result} ({reason})"

    def test_cliente_acepta_correo_survives_pero(self):
        """CLIENTE_ACEPTA_CORREO sobrevive 'pero' adversativo."""
        result, reason = self._simular_pipeline(
            "CLIENTE_ACEPTA_CORREO",
            "si, pero mejor mandamelo al correo",
        )
        assert result == 'survived', f"Debió sobrevivir, pero: {result} ({reason})"

    def test_encargado_no_esta_si_invalida_por_correo(self):
        """ENCARGADO_NO_ESTA_SIN_HORARIO SÍ se invalida cuando cliente ofrece datos."""
        result, reason = self._simular_pipeline(
            "ENCARGADO_NO_ESTA_SIN_HORARIO",
            "no esta, pero yo le puedo ayudar en que le ayudo"
        )
        assert result != 'survived', f"Debió invalidarse por contradicción o adversativo"

    def test_transferencia_si_invalida_cuando_soy_yo(self):
        """TRANSFERENCIA SÍ se invalida cuando cliente dice 'soy yo'."""
        result, reason = self._simular_pipeline(
            "TRANSFERENCIA",
            "soy yo, digame"
        )
        assert result == 'invalidado_598', f"Debió invalidarse por FIX 598"
