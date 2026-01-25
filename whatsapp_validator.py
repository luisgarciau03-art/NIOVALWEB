"""
Validador de Números de WhatsApp para NIOVAL
Verifica si un número tiene WhatsApp activo
"""

import requests
from typing import Dict, Optional
import os
from dotenv import load_dotenv
import time

load_dotenv()


class WhatsAppValidator:
    """
    Validador de números de WhatsApp usando diferentes métodos
    """

    def __init__(self, method: str = "twilio"):
        """
        Inicializa el validador

        Args:
            method: Método de validación ('twilio', 'evolution', 'manual')
        """
        self.method = method

        if method == "twilio":
            self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        elif method == "evolution":
            self.evolution_api_url = os.getenv("EVOLUTION_API_URL")
            self.evolution_api_key = os.getenv("EVOLUTION_API_KEY")

    def validar_whatsapp_twilio(self, numero: str) -> Dict:
        """
        Valida número usando Twilio Lookup API con verificación de WhatsApp

        Args:
            numero: Número en formato +52XXXXXXXXXX

        Returns:
            Dict con resultado de validación
        """
        try:
            from twilio.rest import Client

            client = Client(self.account_sid, self.auth_token)

            # Hacer lookup del número con Fields para obtener info de WhatsApp
            # Fields disponibles: carrier, caller_name, line_type_intelligence
            phone_number = client.lookups.v2.phone_numbers(numero).fetch(
                fields='line_type_intelligence'
            )

            # Verificar si tiene WhatsApp
            # line_type_intelligence contiene info sobre si es WhatsApp
            tiene_whatsapp = False
            carrier_name = None

            # Intentar obtener info de carrier/line type
            if hasattr(phone_number, 'line_type_intelligence'):
                line_type_info = phone_number.line_type_intelligence
                if line_type_info:
                    # Verificar si el tipo de línea indica WhatsApp o VoIP
                    line_type = line_type_info.get('type', '')
                    carrier_name = line_type_info.get('carrier_name', '')

                    # WhatsApp suele aparecer como 'voip' o 'mobile'
                    if line_type in ['voip', 'mobile']:
                        # Asumimos que tiene WhatsApp si es móvil válido en México
                        tiene_whatsapp = True

            # NOTA: El fallback automático para números mexicanos se desactivó
            # para evitar falsos positivos. Solo confiamos en la respuesta de Twilio.
            # Si Twilio no puede determinar si tiene WhatsApp, marcamos como False
            # y Bruce pedirá confirmación al cliente.

            # Nota informativa sobre limitaciones de Twilio Lookup
            nota = 'Validación con Twilio Lookup v2 - Solo confirma si es móvil/VoIP, no valida WhatsApp directamente'
            if tiene_whatsapp:
                nota += ' - Tipo de línea sugiere puede tener WhatsApp'
            else:
                nota += ' - No se pudo confirmar tipo de línea móvil/VoIP'

            resultado = {
                'numero': numero,
                'valido': True,
                'tiene_whatsapp': tiene_whatsapp,
                'formato_nacional': phone_number.national_format,
                'pais': phone_number.country_code,
                'operador': carrier_name,
                'metodo': 'twilio',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'nota': nota
            }

            return resultado

        except Exception as e:
            return {
                'numero': numero,
                'valido': False,
                'tiene_whatsapp': False,
                'error': str(e),
                'metodo': 'twilio',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }

    def validar_whatsapp_evolution(self, numero: str, instance_name: str = "NIOVAL") -> Dict:
        """
        Valida número usando Evolution API (WhatsApp Business API)

        Args:
            numero: Número en formato 52XXXXXXXXXX (sin +)
            instance_name: Nombre de la instancia de Evolution API

        Returns:
            Dict con resultado de validación
        """
        try:
            # Endpoint de Evolution API para verificar número
            url = f"{self.evolution_api_url}/chat/whatsappNumbers/{instance_name}"

            headers = {
                'apikey': self.evolution_api_key,
                'Content-Type': 'application/json'
            }

            # Payload con el número a verificar
            payload = {
                "numbers": [numero]
            }

            response = requests.post(url, json=payload, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Evolution API retorna lista de números con WhatsApp
                tiene_whatsapp = False
                if data and len(data) > 0:
                    # Si el número está en la respuesta, tiene WhatsApp
                    tiene_whatsapp = any(num.get('jid') == f"{numero}@s.whatsapp.net" for num in data)

                return {
                    'numero': numero,
                    'valido': True,
                    'tiene_whatsapp': tiene_whatsapp,
                    'jid': f"{numero}@s.whatsapp.net" if tiene_whatsapp else None,
                    'metodo': 'evolution_api',
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }
            else:
                return {
                    'numero': numero,
                    'valido': False,
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'metodo': 'evolution_api',
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }

        except Exception as e:
            return {
                'numero': numero,
                'valido': False,
                'error': str(e),
                'metodo': 'evolution_api',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }

    def validar_whatsapp_formato(self, numero: str) -> Dict:
        """
        Validación básica por formato (sin verificar si está activo)

        Args:
            numero: Número a validar

        Returns:
            Dict con validación básica
        """
        import re

        # Limpiar número
        numero_limpio = re.sub(r'[^\d+]', '', numero)

        # Validar formato México
        es_valido = False
        if numero_limpio.startswith('+52') and len(numero_limpio) == 13:
            es_valido = True
        elif numero_limpio.startswith('52') and len(numero_limpio) == 12:
            es_valido = True
            numero_limpio = '+' + numero_limpio
        elif len(numero_limpio) == 10:
            es_valido = True
            numero_limpio = '+52' + numero_limpio

        return {
            'numero': numero_limpio,
            'valido': es_valido,
            'tiene_whatsapp': None,  # No se puede verificar sin API
            'formato_correcto': es_valido,
            'metodo': 'formato',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'nota': 'Validación solo por formato, no verifica si tiene WhatsApp activo'
        }

    def validar(self, numero: str, **kwargs) -> Dict:
        """
        Valida un número usando el método configurado

        Args:
            numero: Número a validar
            **kwargs: Parámetros adicionales según método

        Returns:
            Dict con resultado de validación
        """
        if self.method == "twilio":
            return self.validar_whatsapp_twilio(numero)
        elif self.method == "evolution":
            instance = kwargs.get('instance_name', 'NIOVAL')
            return self.validar_whatsapp_evolution(numero, instance)
        else:
            return self.validar_whatsapp_formato(numero)

    def validar_batch(self, numeros: list, delay: float = 0.5) -> list:
        """
        Valida múltiples números con delay entre validaciones

        Args:
            numeros: Lista de números a validar
            delay: Segundos entre validaciones (para evitar rate limiting)

        Returns:
            Lista de resultados
        """
        resultados = []

        for idx, numero in enumerate(numeros):
            print(f"Validando {idx+1}/{len(numeros)}: {numero}")

            resultado = self.validar(numero)
            resultados.append(resultado)

            # Delay entre requests
            if idx < len(numeros) - 1:
                time.sleep(delay)

        return resultados


# Sistema de cache para validaciones
class WhatsAppValidatorCache:
    """Cache de validaciones para evitar validar números repetidos"""

    def __init__(self, validator: WhatsAppValidator):
        self.validator = validator
        self.cache = {}

    def validar(self, numero: str, **kwargs) -> Dict:
        """Valida usando cache"""

        # Revisar cache
        if numero in self.cache:
            resultado = self.cache[numero].copy()
            resultado['desde_cache'] = True
            print(f" Número {numero} encontrado en cache")
            return resultado

        # Validar y guardar en cache
        resultado = self.validator.validar(numero, **kwargs)
        self.cache[numero] = resultado

        return resultado

    def limpiar_cache(self):
        """Limpia el cache de validaciones"""
        self.cache.clear()
        print(" Cache limpiado")

    def obtener_estadisticas(self) -> Dict:
        """Obtiene estadísticas del cache"""
        total = len(self.cache)
        con_whatsapp = sum(1 for r in self.cache.values() if r.get('tiene_whatsapp'))

        return {
            'total_validados': total,
            'con_whatsapp': con_whatsapp,
            'sin_whatsapp': total - con_whatsapp,
            'porcentaje_whatsapp': (con_whatsapp / total * 100) if total > 0 else 0
        }


# Ejemplo de uso
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" VALIDADOR DE WHATSAPP - NIOVAL")
    print("=" * 60 + "\n")

    # Validador básico (por formato)
    print("--- Validación por FORMATO (sin verificar si está activo) ---")
    validator_formato = WhatsAppValidator(method="formato")

    numeros_prueba = [
        "+523312345678",
        "523312345678",
        "3312345678",
        "+52-33-1234-5678",
    ]

    for num in numeros_prueba:
        resultado = validator_formato.validar(num)
        print(f"\nNúmero: {num}")
        print(f"  Válido: {resultado['valido']}")
        print(f"  Formateado: {resultado['numero']}")
        print(f"  Método: {resultado['metodo']}")

    # Validador con cache
    print("\n\n--- Validación con CACHE ---")
    validator_cache = WhatsAppValidatorCache(validator_formato)

    # Primera validación
    print("\n1ra validación:")
    resultado1 = validator_cache.validar("+523312345678")
    print(f"Desde cache: {resultado1.get('desde_cache', False)}")

    # Segunda validación (desde cache)
    print("\n2da validación del mismo número:")
    resultado2 = validator_cache.validar("+523312345678")
    print(f"Desde cache: {resultado2.get('desde_cache', False)}")

    # Estadísticas
    print("\n--- Estadísticas del Cache ---")
    stats = validator_cache.obtener_estadisticas()
    for key, value in stats.items():
        print(f"{key}: {value}")

    print("\n" + "=" * 60)
    print(" CONFIGURACIÓN PARA VALIDACIÓN REAL:")
    print("=" * 60)
    print("""
Para validación REAL de WhatsApp (verificar si está activo):

OPCIÓN 1: Twilio Lookup API
  - Configura en .env:
    TWILIO_ACCOUNT_SID=tu_account_sid
    TWILIO_AUTH_TOKEN=tu_auth_token
  - Costo: ~$0.005 USD por consulta
  - Uso: validator = WhatsAppValidator(method="twilio")

OPCIÓN 2: Evolution API (Recomendado para WhatsApp Business)
  - Configura en .env:
    EVOLUTION_API_URL=http://tu-servidor:8080
    EVOLUTION_API_KEY=tu_api_key
  - Requiere: Servidor Evolution API configurado
  - Uso: validator = WhatsAppValidator(method="evolution")

OPCIÓN 3: Solo formato (actual, gratis pero no verifica actividad)
  - No requiere configuración
  - Solo valida formato del número
  - Uso: validator = WhatsAppValidator(method="formato")
    """)
