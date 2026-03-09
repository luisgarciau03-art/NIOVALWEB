"""
Script MAESTRO para eliminar TODOS los emojis de TODO el proyecto AgenteVentas
Soluciona UnicodeEncodeError en Windows para todos los archivos .py

Fecha: 2026-01-24
"""

import re
import os
import glob

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

        # Reemplazar todos los emojis
        contenido = emoji_pattern.sub('', contenido)

        # Solo guardar si hubo cambios
        if contenido != contenido_original:
            with open(ruta_archivo, 'w', encoding='utf-8') as f:
                f.write(contenido)

            lineas_originales = contenido_original.split('\n')
            lineas_nuevas = contenido.split('\n')
            cambios = sum(1 for o, n in zip(lineas_originales, lineas_nuevas) if o != n)

            return {
                'ok': True,
                'archivo': os.path.basename(ruta_archivo),
                'modificado': True,
                'cambios': cambios,
                'bytes_eliminados': len(contenido_original) - len(contenido)
            }
        else:
            return {
                'ok': True,
                'archivo': os.path.basename(ruta_archivo),
                'modificado': False,
                'cambios': 0,
                'bytes_eliminados': 0
            }

    except Exception as e:
        return {
            'ok': False,
            'archivo': os.path.basename(ruta_archivo),
            'error': str(e)
        }


def main():
    """Función principal"""

    print("\n" + "="*80)
    print("FIX ENCODING MAESTRO: ELIMINACION DE EMOJIS EN TODO EL PROYECTO")
    print("="*80)

    # Buscar todos los archivos .py en el directorio actual
    archivos_py = glob.glob("*.py")

    # Excluir este script mismo y scripts de test
    archivos_py = [f for f in archivos_py if not f.startswith("fix_emojis") and not f.startswith("test_fix")]

    print(f"\nArchivos Python encontrados: {len(archivos_py)}")

    # Categorizar archivos
    adaptadores = [f for f in archivos_py if 'adapter' in f or 'sheets' in f]
    scripts_analisis = [f for f in archivos_py if 'analiz' in f or 'auto_mejora' in f]
    core = [f for f in archivos_py if f in ['agente_ventas.py', 'servidor_llamadas.py']]
    otros = [f for f in archivos_py if f not in adaptadores + scripts_analisis + core]

    categorias = [
        ("CORE (agente + servidor)", core),
        ("ADAPTADORES (Google Sheets)", adaptadores),
        ("SCRIPTS DE ANALISIS", scripts_analisis),
        ("OTROS", otros)
    ]

    resultados_todos = []

    for nombre_cat, archivos in categorias:
        if not archivos:
            continue

        print(f"\n{'='*80}")
        print(f"{nombre_cat} ({len(archivos)} archivos)")
        print(f"{'='*80}")

        for archivo in archivos:
            resultado = eliminar_emojis_de_archivo(archivo)
            resultados_todos.append(resultado)

            if resultado['ok']:
                if resultado['modificado']:
                    print(f"  [MODIFICADO] {resultado['archivo']}: {resultado['cambios']} lineas, {resultado['bytes_eliminados']} bytes")
                # No imprimir los que ya estaban limpios para reducir ruido
            else:
                print(f"  [ERROR] {resultado['archivo']}: {resultado['error']}")

    # Resumen final
    print("\n" + "="*80)
    print("RESUMEN FINAL")
    print("="*80)

    modificados = [r for r in resultados_todos if r['ok'] and r['modificado']]
    limpios = [r for r in resultados_todos if r['ok'] and not r['modificado']]
    errores = [r for r in resultados_todos if not r['ok']]

    total_bytes_eliminados = sum(r['bytes_eliminados'] for r in modificados)

    print(f"\nArchivos modificados: {len(modificados)}")
    print(f"Archivos ya limpios: {len(limpios)}")
    print(f"Archivos con errores: {len(errores)}")
    print(f"Total bytes eliminados (emojis): {total_bytes_eliminados}")

    if modificados:
        print(f"\nArchivos corregidos:")
        for r in modificados:
            print(f"  - {r['archivo']}")

    if len(errores) == 0:
        print("\n[EXITO] Todo el proyecto esta libre de emojis")
        print("\nProximos pasos:")
        print("  1. Ejecutar: python auto_mejora_bruce.py")
        print("  2. Ejecutar: python analizar_encargado_masivo.py <archivo_log>")
        print("  3. Ejecutar tests de validacion")
    else:
        print(f"\n[ADVERTENCIA] {len(errores)} archivos tuvieron errores")

    print("="*80)


if __name__ == "__main__":
    main()
