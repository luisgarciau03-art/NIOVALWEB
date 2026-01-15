# -*- coding: utf-8 -*-
"""
Script para analizar logs de Railway y encontrar frases más frecuentes de Bruce
"""
import re
from collections import Counter
import sys

def extraer_frases_bruce(log_file):
    """Extrae todas las frases que Bruce dice de los logs"""

    frases = []

    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # Buscar líneas con "BRUCE DICE:"
            if "BRUCE DICE:" in line or "🤖 BRUCE DICE:" in line:
                # Extraer la frase entre comillas
                match = re.search(r'"([^"]+)"', line)
                if match:
                    frase = match.group(1)
                    # Limpiar la frase
                    frase = frase.strip()
                    if len(frase) > 10:  # Ignorar frases muy cortas
                        frases.append(frase)

    return frases

def normalizar_frase(frase):
    """Normaliza una frase para agrupación (elimina nombres, números específicos)"""

    # Eliminar números de teléfono/WhatsApp
    frase = re.sub(r'\d{10}', '[NUMERO]', frase)
    frase = re.sub(r'\d{3}\s+\d{3}\s+\d{4}', '[NUMERO]', frase)

    # Eliminar nombres propios (capitalizados seguidos de espacio)
    # Ejemplo: "Hola Carlos" -> "Hola [NOMBRE]"
    frase = re.sub(r'\b[A-Z][a-záéíóúñ]+\b(?!\s+[a-z])', '[NOMBRE]', frase)

    # Normalizar espacios
    frase = re.sub(r'\s+', ' ', frase)

    return frase.strip()

def analizar_frases(frases):
    """Analiza y cuenta frases más frecuentes"""

    # Normalizar todas las frases
    frases_normalizadas = [normalizar_frase(f) for f in frases]

    # Contar frecuencias
    contador = Counter(frases_normalizadas)

    return contador

def main():
    if len(sys.argv) < 2:
        print("\n" + "="*70)
        print("ANALIZADOR DE FRASES FRECUENTES - LOGS DE BRUCE")
        print("="*70 + "\n")
        print("Uso:")
        print("  python analizar_frases_frecuentes_logs.py <archivo_logs.txt>")
        print()
        print("Ejemplo:")
        print("  python analizar_frases_frecuentes_logs.py logs_completos.txt")
        print()
        print("Para descargar logs de Railway:")
        print("  railway logs > logs_completos.txt")
        print()
        return

    log_file = sys.argv[1]

    print("\n" + "="*70)
    print("ANALIZADOR DE FRASES FRECUENTES")
    print("="*70 + "\n")

    print(f"📂 Archivo: {log_file}")
    print("🔍 Buscando frases de Bruce...")

    # Extraer frases
    frases = extraer_frases_bruce(log_file)

    if not frases:
        print("\n❌ No se encontraron frases de Bruce en el log")
        print("   Verifica que el archivo contenga líneas con 'BRUCE DICE:'")
        return

    print(f"✅ Encontradas {len(frases)} frases totales")
    print()

    # Analizar
    contador = analizar_frases(frases)

    print("="*70)
    print("TOP 30 FRASES MÁS FRECUENTES")
    print("="*70 + "\n")

    # Mostrar top 30
    for i, (frase, count) in enumerate(contador.most_common(30), 1):
        # Truncar si es muy larga
        frase_display = frase if len(frase) <= 60 else frase[:57] + "..."

        # Calcular palabras
        num_palabras = len(frase.split())

        print(f"{i:2}. [{count:3}x] ({num_palabras:2}p) {frase_display}")

    print()
    print("="*70)
    print("ESTADÍSTICAS")
    print("="*70)
    print(f"\nFrases únicas: {len(contador)}")
    print(f"Frases totales: {len(frases)}")
    print(f"Tasa de reutilización: {(1 - len(contador)/len(frases))*100:.1f}%")
    print()

    # Calcular cuántas frases cubren el 80% de uso
    total = len(frases)
    acumulado = 0
    frases_80 = 0

    for frase, count in contador.most_common():
        acumulado += count
        frases_80 += 1
        if acumulado >= total * 0.8:
            break

    print(f"📊 Para cubrir el 80% de uso, necesitas cachear {frases_80} frases")
    print()

    # Generar recomendación de cachés
    print("="*70)
    print("FRASES RECOMENDADAS PARA CACHEAR (Top 20)")
    print("="*70)
    print()
    print("Copiar a generar_cache_frases_comunes.py:")
    print()
    print("FRASES_CRITICAS = {")

    for i, (frase, count) in enumerate(contador.most_common(20), 1):
        # Generar key
        palabras = frase.lower().split()[:4]
        key = "_".join(palabras).replace('[nombre]', 'nombre').replace('[numero]', 'numero')

        # Escapar comillas
        frase_escaped = frase.replace('"', '\\"')

        print(f'    "{key}_{i}": "{frase_escaped}",  # {count}x')

    print("}")
    print()

if __name__ == "__main__":
    main()
