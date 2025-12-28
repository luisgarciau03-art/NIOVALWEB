"""
Script para ver la estructura completa del Google Spreadsheet
"""
from nioval_sheets_adapter import NiovalSheetsAdapter

try:
    print("=" * 80)
    print("ESTRUCTURA DEL GOOGLE SPREADSHEET")
    print("=" * 80)

    adapter = NiovalSheetsAdapter()

    # Obtener todas las filas (primeras 5 para ver estructura)
    datos = adapter.hoja_contactos.get_all_values()

    if datos and len(datos) > 0:
        # Encabezados (primera fila)
        encabezados = datos[0]

        print(f"\n📋 COLUMNAS ENCONTRADAS ({len(encabezados)} columnas):")
        print("-" * 80)

        letras = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        for i, encabezado in enumerate(encabezados):
            letra = letras[i] if i < len(letras) else f"[{i+1}]"
            print(f"{letra:3} | {encabezado}")

        print(f"\n📊 EJEMPLO DE DATOS (Fila 2):")
        print("-" * 80)
        if len(datos) > 1:
            fila_ejemplo = datos[1]
            for i, valor in enumerate(fila_ejemplo):
                letra = letras[i] if i < len(letras) else f"[{i+1}]"
                encabezado = encabezados[i] if i < len(encabezados) else "N/A"
                valor_mostrar = str(valor)[:60] if valor else "[VACÍO]"
                print(f"{letra:3} | {encabezado:20} | {valor_mostrar}")

        print("\n" + "=" * 80)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
