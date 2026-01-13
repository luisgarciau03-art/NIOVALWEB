"""
FIX 196: Regenerar audios con pronunciación incorrecta de "ferretería" y "grifería"

PROBLEMA REPORTADO:
- "ferretería" se pronuncia como "ferRRETERRIA" (doble R excesiva)
- "grifería" se pronuncia como "grifeRRIA" (doble R incorrecta)

CAUSA:
- Audios en caché generados sin aplicar corregir_pronunciacion()
- La función corregir_pronunciacion() existe pero NO se aplicó al pre-caché

SOLUCIÓN:
1. Identificar audios con estos términos
2. Eliminar archivos viejos del caché
3. Regenerar con corrección de pronunciación aplicada
"""

import os
import sys
import hashlib
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
ELEVENLABS_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Adam (voz de Bruce)
AUDIO_CACHE_DIR = "audio_cache"

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)


def corregir_pronunciacion(texto):
    """Aplica correcciones fonéticas para mejorar pronunciación"""
    correcciones = {
        # Palabras problemáticas con RR
        "ferreteros": "fe-rre-te-ros",
        "ferretería": "fe-rre-te-rí-a",
        "ferreterías": "fe-rre-te-rí-as",
        "tapagoteras": "ta-pa-go-te-ras",
        "grifería": "gri-fe-rí-a",
        "griferías": "gri-fe-rí-as",
    }

    texto_corregido = texto
    for original, reemplazo in correcciones.items():
        texto_corregido = texto_corregido.replace(original, reemplazo)

    return texto_corregido


def generar_audio_id(texto):
    """Genera ID único para el audio basado en el texto"""
    return hashlib.md5(texto.encode('utf-8')).hexdigest()[:12]


def regenerar_audio(key, texto, motivo):
    """Regenera un audio específico con pronunciación corregida"""
    print(f"\n{'='*80}")
    print(f"🔧 REGENERANDO: {key}")
    print(f"📝 Texto original: {texto}")

    # Aplicar corrección de pronunciación
    texto_corregido = corregir_pronunciacion(texto)
    print(f"✅ Texto corregido: {texto_corregido}")
    print(f"📌 Motivo: {motivo}")

    # Verificar que realmente cambió
    if texto == texto_corregido:
        print(f"⚠️ ADVERTENCIA: No hubo cambios en el texto - verificar correcciones")

    try:
        # Buscar archivo viejo en caché
        archivos_cache = os.listdir(AUDIO_CACHE_DIR)
        archivos_relacionados = [
            f for f in archivos_cache
            if key in f or texto[:30].lower().replace(" ", "_") in f.lower()
        ]

        if archivos_relacionados:
            print(f"🗑️ Archivos viejos encontrados: {archivos_relacionados}")
            for archivo_viejo in archivos_relacionados:
                ruta_vieja = os.path.join(AUDIO_CACHE_DIR, archivo_viejo)
                # Renombrar en vez de eliminar (backup)
                backup_name = archivo_viejo.replace('.mp3', '.OLD.mp3')
                backup_path = os.path.join(AUDIO_CACHE_DIR, backup_name)
                os.rename(ruta_vieja, backup_path)
                print(f"   ✅ Respaldo creado: {backup_name}")

        # Generar nuevo audio con ElevenLabs
        print(f"🎙️ Generando nuevo audio con ElevenLabs...")
        audio_generator = elevenlabs_client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=texto_corregido,
            model_id="eleven_multilingual_v2",  # Mejor acento mexicano
            output_format="mp3_44100_128"
        )

        # Guardar audio nuevo
        audio_id = generar_audio_id(texto)
        nuevo_nombre = f"{key}_{audio_id}.mp3"
        nueva_ruta = os.path.join(AUDIO_CACHE_DIR, nuevo_nombre)

        with open(nueva_ruta, 'wb') as f:
            for chunk in audio_generator:
                if chunk:
                    f.write(chunk)

        print(f"✅ Audio regenerado exitosamente: {nuevo_nombre}")
        print(f"📂 Ruta: {nueva_ruta}")

        return True

    except Exception as e:
        print(f"❌ ERROR al regenerar audio: {str(e)}")
        return False


def main():
    """Regenerar todos los audios con problemas de pronunciación"""
    print("=" * 80)
    print("FIX 196: REGENERAR AUDIOS CON PRONUNCIACIÓN INCORRECTA")
    print("=" * 80)
    print()

    if not ELEVENLABS_API_KEY:
        print("❌ ERROR: Variable ELEVENLABS_API_KEY no configurada")
        print("   Ejecutar: $env:ELEVENLABS_API_KEY='tu_api_key'")
        return

    # Audios identificados con problemas
    audios_a_regenerar = {
        # Respuestas en caché (respuestas_cache)
        "respuesta_cache_que_vende": {
            "texto": "Distribuimos productos de ferretería: cinta para goteras, griferías, herramientas, candados y más categorías. ¿Se encuentra el encargado de compras?",
            "motivo": "Contiene 'ferretería' y 'griferías' con pronunciación incorrecta"
        },
        "respuesta_cache_quien_habla": {
            "texto": "Mi nombre es Bruce W, soy asesor de ventas de NIOVAL. Quisiera brindar información al encargado de compras sobre nuestros productos ferreteros. ¿Me lo puede comunicar por favor?",
            "motivo": "Contiene 'ferreteros' con pronunciación incorrecta"
        },

        # Saludos iniciales (frases_comunes)
        "saludo_inicial": {
            "texto": "Hola, que tal, buen dia, me comunico de la marca nioval, queria brindar informacion de nuestros productos ferreteros, ¿Se encuentra el encargado o encargada de compras?",
            "motivo": "Saludo inicial con 'ferreteros' pronunciado incorrectamente"
        },
        "saludo_inicial_encargado": {
            "texto": "Hola, que tal, buen dia, me comunico de la marca nioval, queria brindar informacion de nuestros productos ferreteros, ¿Con quién tengo el gusto?",
            "motivo": "Saludo alternativo con 'ferreteros' pronunciado incorrectamente"
        },
    }

    print(f"📋 Total de audios a regenerar: {len(audios_a_regenerar)}")
    print()

    exitos = 0
    fallos = 0

    for key, datos in audios_a_regenerar.items():
        if regenerar_audio(key, datos["texto"], datos["motivo"]):
            exitos += 1
        else:
            fallos += 1

    print("\n" + "=" * 80)
    print("📊 RESUMEN")
    print("=" * 80)
    print(f"✅ Audios regenerados exitosamente: {exitos}")
    print(f"❌ Audios con errores: {fallos}")
    print(f"📂 Ubicación: {os.path.abspath(AUDIO_CACHE_DIR)}")
    print()

    if fallos == 0:
        print("🎉 COMPLETADO - Todos los audios regenerados con pronunciación correcta")
        print()
        print("📌 PRÓXIMOS PASOS:")
        print("   1. Verificar audios regenerados escuchándolos manualmente")
        print("   2. Desplegar a Railway (git push)")
        print("   3. Hacer llamada de prueba y verificar pronunciación")
        print("   4. Si OK, eliminar archivos .OLD.mp3 del caché")
    else:
        print("⚠️ ADVERTENCIA - Algunos audios no se regeneraron correctamente")
        print("   Revisar errores arriba y reintentar")


if __name__ == "__main__":
    main()
