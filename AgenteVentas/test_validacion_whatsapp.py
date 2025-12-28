"""
Test de validación de WhatsApp con Twilio
"""

import sys
import io

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from whatsapp_validator import WhatsAppValidator

print("\n" + "=" * 60)
print("🧪 TEST - VALIDACIÓN DE WHATSAPP CON TWILIO")
print("=" * 60 + "\n")

# Números de prueba
numeros_prueba = [
    "+5219377958829",  # Tu número de Twilio (probablemente no tiene WhatsApp)
    "+526621234567",   # Número mexicano de ejemplo
]

try:
    # Inicializar validador con método Twilio
    print("📱 Inicializando validador con Twilio Lookup API...")
    validator = WhatsAppValidator(method="twilio")

    for numero in numeros_prueba:
        print(f"\n{'─'*60}")
        print(f"📞 Validando: {numero}")
        print(f"{'─'*60}")

        resultado = validator.validar(numero)

        print(f"\n✅ Resultado:")
        print(f"   Número: {resultado.get('numero')}")
        print(f"   Válido: {resultado.get('valido')}")
        print(f"   🟢 Tiene WhatsApp: {resultado.get('tiene_whatsapp')}")
        print(f"   País: {resultado.get('pais')}")
        print(f"   Operador: {resultado.get('operador')}")
        print(f"   Formato nacional: {resultado.get('formato_nacional')}")

        if 'nota' in resultado:
            print(f"   ℹ️  {resultado.get('nota')}")

        if 'error' in resultado:
            print(f"   ❌ Error: {resultado.get('error')}")

    print("\n" + "=" * 60)
    print("✅ TEST COMPLETADO")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n")
