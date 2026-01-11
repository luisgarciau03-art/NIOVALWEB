"""
FIX 162A + FIX 163 + FIX 170: Generar audios de relleno con ElevenLabs
Genera audios para usar cuando ElevenLabs falla, cuando GPT tarda mucho,
o cuando cliente va a pasar al encargado
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

# URL del servidor en Railway
RAILWAY_URL = os.getenv("RAILWAY_URL", "https://nioval-webhook-server-production.up.railway.app")

# FIX 162A + FIX 163: Audios de relleno críticos
audios_relleno = [
    # FIX 162A: Audios para cuando ElevenLabs falla
    {
        "key": "dejeme_ver",
        "texto": "Déjeme ver...",
        "force": True
    },
    {
        "key": "un_momento",
        "texto": "Un momento por favor.",
        "force": True
    },
    {
        "key": "lo_reviso",
        "texto": "Lo reviso.",
        "force": True
    },
    {
        "key": "despedida_simple",
        "texto": "Muchas gracias. Que tenga un excelente día.",
        "force": True
    },

    # FIX 163: Audios para delays 5-8s (medios)
    {
        "key": "dejeme_ver_con_calma",
        "texto": "Déjeme ver eso con calma...",
        "force": True
    },
    {
        "key": "un_momento_lo_reviso",
        "texto": "Un momento, lo reviso...",
        "force": True
    },
    {
        "key": "permitame_verificar",
        "texto": "Permítame verificar...",
        "force": True
    },
    {
        "key": "dejeme_consultarlo",
        "texto": "Déjeme consultarlo...",
        "force": True
    },
    {
        "key": "un_segundito_verifico",
        "texto": "Un segundito, lo verifico...",
        "force": True
    },
    {
        "key": "dejeme_checar",
        "texto": "Déjeme checar eso...",
        "force": True
    },

    # FIX 163: Audios para delays >8s (largos)
    {
        "key": "reviso_toda_informacion",
        "texto": "Déjeme revisar bien toda la información...",
        "force": True
    },
    {
        "key": "verifico_detalles",
        "texto": "Un momento por favor, verifico los detalles...",
        "force": True
    },
    {
        "key": "consulto_con_cuidado",
        "texto": "Permítame consultar esto con cuidado...",
        "force": True
    },
    {
        "key": "veo_todos_detalles",
        "texto": "Déjeme ver todos los detalles...",
        "force": True
    },

    # FIX 170: Audio para cuando cliente va a pasar al encargado
    {
        "key": "claro_espero",
        "texto": "Claro, espero.",
        "force": True
    },
]

def main():
    print("=" * 70)
    print("GENERADOR DE AUDIOS DE RELLENO (FIX 162A + FIX 163 + FIX 170)")
    print("=" * 70)
    print()
    print(f"Audios a generar: {len(audios_relleno)}")
    print()

    for i, audio in enumerate(audios_relleno, 1):
        print(f"   {i}. {audio['key']}")
        print(f"      -> {audio['texto']}")
        print()

    # Generar audios usando el endpoint de Railway
    response = requests.post(
        f"{RAILWAY_URL}/generate-cache",
        json={"frases": audios_relleno},
        timeout=300  # 5 minutos timeout
    )

    if response.status_code == 200:
        result = response.json()
        print("OK - Audios generados exitosamente\n")
        print(f"Resultados:")
        print(f"   - Audios generados: {result.get('generated', 0)}")
        print(f"   - Total solicitados: {result.get('total_requested', 0)}")
        print(f"   - Errores: {len(result.get('errors', []) or [])}")

        if result.get('errors'):
            print(f"\nERROR - Errores:")
            for error in result['errors']:
                print(f"   - {error}")
    else:
        print(f"ERROR al generar audios: {response.status_code}")
        print(f"   Respuesta: {response.text}")

    print()
    print("=" * 70)

if __name__ == "__main__":
    main()
