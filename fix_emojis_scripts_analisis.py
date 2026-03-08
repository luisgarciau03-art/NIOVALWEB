"""
Script para eliminar TODOS los emojis de los 3 scripts de análisis
Soluciona errores UnicodeEncodeError en Windows para:
- analizar_encargado_masivo.py (FIX 404)
- auto_mejora_bruce.py (Análisis Google Sheets)
- analisis_log_masivo.py

Fecha: 2026-01-24
"""

import re
import os

def eliminar_emojis_de_archivo(ruta_archivo):
    """Elimina todos los emojis de un archivo usando regex comprehensivo"""

    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()

        contenido_original = contenido

        # Patrón regex para eliminar TODOS los emojis Unicode
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # símbolos & pictogramas
            "\U0001F680-\U0001F6FF"  # transporte & símbolos de mapa
            "\U0001F1E0-\U0001F1FF"  # banderas (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "\U0001F900-\U0001F9FF"  # emojis suplementarios
            "\U0001FA70-\U0001FAFF"  # símbolos extendidos
            "\U00002300-\U000023FF"  # símbolos técnicos varios
            "\U0001F000-\U0001F02F"  # piezas de Mahjong
            "\U0001F0A0-\U0001F0FF"  # cartas de juego
            "]+",
            flags=re.UNICODE
        )

        # Reemplazar todos los emojis por texto plano equivalente
        # (vacío para no cambiar el significado del código)
        contenido = emoji_pattern.sub('', contenido)

        # Contar cuántas líneas cambiaron
        lineas_originales = contenido_original.split('\n')
        lineas_nuevas = contenido.split('\n')

        cambios = sum(1 for o, n in zip(lineas_originales, lineas_nuevas) if o != n)

        # Guardar archivo corregido
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(contenido)

        # Retornar estadísticas sin imprimir
        return {
            'ok': True,
            'archivo': os.path.basename(ruta_archivo),
            'cambios': cambios,
            'bytes_antes': len(contenido_original),
            'bytes_despues': len(contenido),
            'bytes_eliminados': len(contenido_original) - len(contenido)
        }

    except Exception as e:
        return {
            'ok': False,
            'archivo': ruta_archivo,
            'error': str(e)
        }


def main():
    """Función principal"""

    print("\n" + "="*80)
    print("FIX ENCODING: ELIMINACION DE EMOJIS EN SCRIPTS DE ANALISIS")
    print("="*80)

    # Archivos a procesar
    archivos = [
        "analizar_encargado_masivo.py",
        "auto_mejora_bruce.py",
        "analisis_log_masivo.py"
    ]

    resultados = []

    for archivo in archivos:
        if os.path.exists(archivo):
            resultado = eliminar_emojis_de_archivo(archivo)
            resultados.append(resultado)
        else:
            resultados.append({
                'ok': False,
                'archivo': archivo,
                'error': 'Archivo no encontrado'
            })

    # Resumen final
    print("\n" + "="*80)
    print("RESUMEN FINAL")
    print("="*80)

    procesados = 0
    total_bytes_eliminados = 0

    for r in resultados:
        if r['ok']:
            procesados += 1
            total_bytes_eliminados += r['bytes_eliminados']
            print(f"\n[OK] {r['archivo']}")
            print(f"  - Lineas modificadas: {r['cambios']}")
            print(f"  - Bytes eliminados: {r['bytes_eliminados']}")
        else:
            print(f"\n[ERROR] {r['archivo']}")
            print(f"  - Error: {r['error']}")

    print("\n" + "="*80)
    print(f"Archivos procesados correctamente: {procesados}/{len(archivos)}")
    print(f"Total bytes eliminados (emojis): {total_bytes_eliminados}")

    if procesados == len(archivos):
        print("\n[EXITO] Todos los scripts estan listos para ejecucion")
        print("\nProximos pasos:")
        print("  1. Ejecutar: python analizar_encargado_masivo.py logs_railway_completo.txt")
        print("  2. Ejecutar: python auto_mejora_bruce.py")
        print("  3. Revisar analisis para validar FIX 404")
    else:
        print(f"\n[ADVERTENCIA] {len(archivos) - procesados} archivos no se procesaron")

    print("="*80)


if __name__ == "__main__":
    main()
