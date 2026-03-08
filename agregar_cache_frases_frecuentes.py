# -*- coding: utf-8 -*-
"""
Script para agregar frases frecuentes de hoy al cache de audio
Analiza los logs del dia y genera cache para las frases mas usadas
"""
import requests
import os
import re
import sys
from collections import Counter
from datetime import datetime

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

RAILWAY_URL = "https://nioval-webhook-server-production.up.railway.app"
LOGS_DIR = r"C:\Users\PC 1\AgenteVentas\LOGS"

def analizar_logs_hoy():
    """Analiza los logs de hoy y encuentra frases frecuentes"""
    hoy = datetime.now().strftime("%d_%m")
    frases = []

    print(f"\n Analizando logs de hoy ({hoy})...")

    archivos_analizados = 0
    for archivo in os.listdir(LOGS_DIR):
        if archivo.startswith(hoy) and archivo.endswith('.txt'):
            filepath = os.path.join(LOGS_DIR, archivo)
            archivos_analizados += 1
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    contenido = f.read()
                    # Buscar frases que Bruce dice
                    matches = re.findall(r'BRUCE\d+ DICE: "([^"]+)"', contenido)
                    frases.extend(matches)
            except Exception as e:
                print(f"   Error leyendo {archivo}: {e}")

    print(f"   Archivos analizados: {archivos_analizados}")
    print(f"   Total frases encontradas: {len(frases)}")

    return Counter(frases)

def filtrar_frases_para_cache(contador, min_usos=2):
    """Filtra frases que vale la pena cachear"""
    frases_filtradas = []

    for frase, count in contador.most_common(50):
        if count < min_usos:
            continue

        # Ignorar frases muy cortas
        if len(frase) < 15:
            continue

        # Ignorar frases con datos especificos (numeros de telefono, nombres)
        if re.search(r'\d{10}', frase):
            continue

        # Generar key normalizada
        palabras = frase.lower().split()[:8]
        key = "_".join(palabras)
        key = re.sub(r'[^a-z0-9_]', '', key)
        key = key[:50]  # Limitar longitud

        frases_filtradas.append({
            "key": f"auto_{key}",
            "texto": frase,
            "usos": count,
            "force": False  # No sobrescribir si ya existe
        })

    return frases_filtradas

def generar_cache_en_railway(frases):
    """Envia frases a Railway para generar cache"""
    print(f"\n Enviando {len(frases)} frases a Railway para generar cache...")

    try:
        response = requests.post(
            f"{RAILWAY_URL}/generate-cache",
            json={"frases": frases},
            timeout=180  # 3 minutos timeout
        )

        if response.status_code == 200:
            result = response.json()
            return True, result
        else:
            return False, response.text

    except requests.Timeout:
        return False, "TIMEOUT: La generacion tardo mas de 3 minutos"
    except Exception as e:
        return False, str(e)

def main():
    print("\n" + "=" * 70)
    print("GENERADOR DE CACHE - FRASES FRECUENTES DEL DIA")
    print("=" * 70)

    # 1. Analizar logs
    contador = analizar_logs_hoy()

    if not contador:
        print("\n No se encontraron frases en los logs de hoy")
        return

    # 2. Filtrar frases (minimo 2 usos)
    frases_para_cache = filtrar_frases_para_cache(contador, min_usos=2)

    print(f"\n Frases a cachear (>=2 usos): {len(frases_para_cache)}")
    print("-" * 70)

    for i, frase in enumerate(frases_para_cache[:15], 1):
        texto_display = frase['texto'][:55] + "..." if len(frase['texto']) > 55 else frase['texto']
        print(f"   {i:2}. [{frase['usos']:2}x] {texto_display}")

    if not frases_para_cache:
        print("\n No hay frases nuevas para cachear")
        return

    print()
    respuesta = input("Generar cache para estas frases? (s/n): ")

    if respuesta.lower() != 's':
        print("Cancelado.")
        return

    # 3. Generar cache
    exito, resultado = generar_cache_en_railway(frases_para_cache)

    print("\n" + "=" * 70)
    if exito:
        print("CACHE GENERADO EXITOSAMENTE")
        print("=" * 70)
        print(f"\n{resultado.get('message', 'OK')}")
        print(f"Audios generados: {resultado.get('audios_generados', 'N/A')}")
        print(f"Audios existentes: {resultado.get('audios_existentes', 'N/A')}")
    else:
        print("ERROR AL GENERAR CACHE")
        print("=" * 70)
        print(f"\n{resultado}")

    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
