"""
Script para analizar el contenido del TABLERO DE NIOVAL
"""
import pandas as pd
import sys

try:
    # Leer el archivo Excel
    df = pd.read_excel('TABLERO DE NIOVAL Yahir .xlsx')

    print("=" * 80)
    print("ANÁLISIS DEL TABLERO DE NIOVAL")
    print("=" * 80)

    print("\n COLUMNAS DISPONIBLES:")
    print("-" * 80)
    for i, col in enumerate(df.columns, 1):
        print(f"{i:2}. {col}")

    print(f"\n ESTADÍSTICAS:")
    print("-" * 80)
    print(f"Total de registros: {len(df)}")
    print(f"Total de columnas: {len(df.columns)}")

    # Analizar columnas con datos
    print("\n CONTENIDO DE COLUMNAS (primeras 3 filas):")
    print("-" * 80)

    # Mostrar primeras 3 filas de cada columna importante
    columnas_importantes = ['CONTACTO', 'RESPUESTA', 'PORCENTAJES', 'Domicilio',
                           'Estatus', 'Maps', 'Link', 'Horario']

    for col in columnas_importantes:
        if col in df.columns:
            print(f"\n {col}:")
            valores = df[col].head(3).tolist()
            for i, val in enumerate(valores, 1):
                val_str = str(val)[:100] if pd.notna(val) else "[VACÍO]"
                print(f"   Fila {i}: {val_str}")

            # Estadísticas de la columna
            no_vacios = df[col].notna().sum()
            print(f"   → Filas con datos: {no_vacios}/{len(df)} ({no_vacios/len(df)*100:.1f}%)")

    print("\n" + "=" * 80)
    print("EJEMPLOS DE REGISTROS COMPLETOS:")
    print("=" * 80)

    # Mostrar 2 registros completos
    print("\n REGISTRO 1:")
    print("-" * 80)
    if len(df) > 0:
        registro = df.iloc[0]
        for col in df.columns:
            valor = registro[col]
            valor_str = str(valor)[:150] if pd.notna(valor) else "[VACÍO]"
            print(f"{col:20}: {valor_str}")

    if len(df) > 1:
        print("\n REGISTRO 2:")
        print("-" * 80)
        registro = df.iloc[1]
        for col in df.columns:
            valor = registro[col]
            valor_str = str(valor)[:150] if pd.notna(valor) else "[VACÍO]"
            print(f"{col:20}: {valor_str}")

    print("\n" + "=" * 80)

except Exception as e:
    print(f" Error al leer el archivo: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
