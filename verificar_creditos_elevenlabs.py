"""
FIX 200: Script de verificación y monitoreo de créditos ElevenLabs

Este script:
1. Verifica el balance actual de créditos
2. Muestra información detallada de la cuenta
3. Detecta si hay créditos suficientes para operar
4. Genera alertas si los créditos están bajos

Uso:
    python verificar_creditos_elevenlabs.py
"""

import os
import sys
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

# Cargar variables de entorno
load_dotenv()

# Thresholds de alertas
CREDITO_CRITICO = 500      # Menos de 500 créditos = CRÍTICO
CREDITO_BAJO = 2000        # Menos de 2000 créditos = ADVERTENCIA
CREDITO_OPTIMO = 5000      # Más de 5000 créditos = ÓPTIMO

# Estimación de consumo
CREDITOS_POR_PALABRA = 6.2  # Promedio según logs: 58 créditos / ~9 palabras
PALABRAS_POR_LLAMADA = 50   # Promedio de palabras por llamada completa
CREDITOS_POR_LLAMADA = int(PALABRAS_POR_LLAMADA * CREDITOS_POR_PALABRA)


def verificar_creditos():
    """
    Verifica el balance de créditos de ElevenLabs
    """
    try:
        print("\n" + "="*60)
        print("🔍 FIX 200: VERIFICACIÓN DE CRÉDITOS ELEVENLABS")
        print("="*60 + "\n")

        # Obtener API key
        api_key = os.getenv("ELEVENLABS_API_KEY")

        if not api_key:
            print("❌ ERROR: ELEVENLABS_API_KEY no está configurado en .env")
            return False

        # Inicializar cliente
        print("📡 Conectando con ElevenLabs API...")
        client = ElevenLabs(api_key=api_key)

        # Obtener información de la cuenta
        print("📊 Obteniendo información de la cuenta...\n")

        # Obtener subscription info
        subscription = client.user.get_subscription()

        print("-" * 60)
        print("💳 INFORMACIÓN DE LA CUENTA")
        print("-" * 60)

        # Character info (ElevenLabs usa "characters" como unidad)
        if hasattr(subscription, 'character_count'):
            caracteres_usados = subscription.character_count
            caracteres_limite = subscription.character_limit
            caracteres_restantes = caracteres_limite - caracteres_usados

            print(f"📝 Caracteres usados: {caracteres_usados:,}")
            print(f"📦 Límite de caracteres: {caracteres_limite:,}")
            print(f"✅ Caracteres restantes: {caracteres_restantes:,}")

            # Calcular porcentaje usado
            porcentaje_usado = (caracteres_usados / caracteres_limite * 100) if caracteres_limite > 0 else 0
            print(f"📊 Uso: {porcentaje_usado:.1f}%")

            # Estimación de llamadas restantes
            # Aproximadamente 1 carácter = 1 crédito en el sistema anterior
            # Una llamada promedio usa ~300 caracteres
            llamadas_restantes = caracteres_restantes // 300
            print(f"📞 Llamadas estimadas restantes: ~{llamadas_restantes:,}")

            print()

            # Estado del servicio
            print("-" * 60)
            print("🎯 ESTADO DEL SERVICIO")
            print("-" * 60)

            if caracteres_restantes < 10000:  # Menos de 10k caracteres = ~30 llamadas
                print("🚨 ESTADO: CRÍTICO")
                print("   ⚠️  Créditos MUY BAJOS")
                print("   ⚠️  Recargar INMEDIATAMENTE")
                print(f"   ⚠️  Solo quedan ~{llamadas_restantes} llamadas")
                status = "CRITICO"
            elif caracteres_restantes < 50000:  # Menos de 50k = ~160 llamadas
                print("⚠️  ESTADO: ADVERTENCIA")
                print("   📢 Créditos bajos")
                print("   📢 Considerar recarga pronto")
                print(f"   📢 Quedan ~{llamadas_restantes} llamadas")
                status = "ADVERTENCIA"
            else:
                print("✅ ESTADO: ÓPTIMO")
                print("   ✓ Créditos suficientes para operar")
                print(f"   ✓ Quedan ~{llamadas_restantes} llamadas")
                status = "OPTIMO"

            print()

        else:
            print("⚠️  No se pudo obtener información de caracteres")
            print("    (Puede ser un plan diferente o API actualizada)")

        # Información adicional
        if hasattr(subscription, 'tier'):
            print(f"📦 Plan: {subscription.tier}")

        if hasattr(subscription, 'next_character_count_reset_unix'):
            from datetime import datetime
            reset_date = datetime.fromtimestamp(subscription.next_character_count_reset_unix)
            print(f"🔄 Próximo reinicio: {reset_date.strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n" + "="*60)
        print("✅ VERIFICACIÓN COMPLETADA")
        print("="*60 + "\n")

        # Retornar si el estado es crítico
        if 'status' in locals() and status == "CRITICO":
            return False
        else:
            return True

    except Exception as e:
        print(f"\n❌ ERROR al verificar créditos: {str(e)}")
        print(f"   Tipo de error: {type(e).__name__}")

        # Mostrar traceback para debugging
        import traceback
        print("\n📋 Traceback completo:")
        traceback.print_exc()

        return False


def test_generacion_audio():
    """
    Prueba de generación de audio para verificar que ElevenLabs funciona
    """
    try:
        print("\n" + "="*60)
        print("🧪 PRUEBA DE GENERACIÓN DE AUDIO")
        print("="*60 + "\n")

        api_key = os.getenv("ELEVENLABS_API_KEY")
        voice_id = os.getenv("ELEVENLABS_VOICE_ID")

        if not api_key or not voice_id:
            print("❌ ERROR: Faltan variables de entorno (ELEVENLABS_API_KEY o ELEVENLABS_VOICE_ID)")
            return False

        client = ElevenLabs(api_key=api_key)

        print("🎤 Generando audio de prueba...")
        print(f"   Voice ID: {voice_id}")
        print(f"   Texto: 'Hola, esta es una prueba de voz.'")

        # Generar audio de prueba (texto corto)
        audio_generator = client.text_to_speech.convert(
            voice_id=voice_id,
            text="Hola, esta es una prueba de voz.",
            model_id="eleven_multilingual_v2"
        )

        # Consumir el generador
        audio_bytes = b"".join(audio_generator)

        print(f"✅ Audio generado exitosamente ({len(audio_bytes)} bytes)")
        print("✅ ElevenLabs está funcionando correctamente")

        return True

    except Exception as e:
        print(f"\n❌ ERROR al generar audio de prueba: {str(e)}")
        print(f"   Tipo de error: {type(e).__name__}")

        if "quota_exceeded" in str(e).lower():
            print("\n🚨 PROBLEMA DETECTADO: QUOTA EXCEDIDA")
            print("   El error en los logs era correcto: sin créditos suficientes")
            print("   SOLUCIÓN: Recargar créditos en ElevenLabs")

        return False


def main():
    """
    Función principal
    """
    print("\n" + "="*60)
    print("🚀 INICIANDO DIAGNÓSTICO COMPLETO DE ELEVENLABS")
    print("="*60)

    # 1. Verificar créditos
    creditos_ok = verificar_creditos()

    # 2. Probar generación de audio
    audio_ok = test_generacion_audio()

    # 3. Resumen final
    print("\n" + "="*60)
    print("📊 RESUMEN FINAL")
    print("="*60)
    print(f"✓ Verificación de créditos: {'✅ OK' if creditos_ok else '❌ FALLÓ'}")
    print(f"✓ Generación de audio: {'✅ OK' if audio_ok else '❌ FALLÓ'}")

    if creditos_ok and audio_ok:
        print("\n✅ TODO ESTÁ FUNCIONANDO CORRECTAMENTE")
        print("   El sistema puede hacer llamadas sin problemas")
        sys.exit(0)
    else:
        print("\n❌ HAY PROBLEMAS QUE REQUIEREN ATENCIÓN")
        if not creditos_ok:
            print("   - Créditos bajos o críticos")
        if not audio_ok:
            print("   - No se puede generar audio (verificar API key, voice ID, o créditos)")
        sys.exit(1)


if __name__ == "__main__":
    main()
