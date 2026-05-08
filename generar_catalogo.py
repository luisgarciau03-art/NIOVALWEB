import openpyxl, json, os

path = r'C:\Users\PC 1\Cotizaciones\Noviembre\Lista de Precios Nioval 2025 2 TRI +  (1).xlsx'
wb = openpyxl.load_workbook(path, read_only=True)

def limpiar(nombre):
    if not nombre: return ''
    return str(nombre).strip()

catalogo = {'griferia': [], 'cerraduras': [], 'cintas': []}

ws = wb['Sheet1']
for r in list(ws.iter_rows(values_only=True))[1:]:
    if r[0] and str(r[0]).isdigit() and r[2]:
        nombre = limpiar(r[2])
        precio = round(float(r[3]), 2) if r[3] else None
        precio_iva = round(float(r[5]), 2) if len(r) > 5 and r[5] else None
        if nombre and precio:
            catalogo['griferia'].append({
                'sku': str(r[0]),
                'nombre': nombre,
                'precio': precio,
                'precio_iva': precio_iva
            })

ws = wb['Copy of Sheet1 2']
for r in list(ws.iter_rows(values_only=True)):
    if r[0] and str(r[0]).replace('.0', '').isdigit() and len(r) > 2 and r[2]:
        nombre = limpiar(r[2])
        precio = round(float(r[3]), 2) if len(r) > 3 and r[3] else None
        if nombre and precio:
            catalogo['cerraduras'].append({
                'sku': str(int(float(r[0]))),
                'nombre': nombre,
                'precio': precio
            })

ws = wb['Copy of Sheet1 1']
for r in list(ws.iter_rows(values_only=True)):
    if r[0] and str(r[0]).replace('.0', '').isdigit() and len(r) > 2 and r[2]:
        nombre = limpiar(r[2])
        precio = round(float(r[3]), 2) if len(r) > 3 and r[3] else None
        if nombre and precio:
            catalogo['cintas'].append({
                'sku': str(int(float(r[0]))),
                'nombre': nombre,
                'precio': precio
            })

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'catalogo_data.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(catalogo, f, ensure_ascii=False, indent=2)

for cat, prods in catalogo.items():
    print(f'{cat}: {len(prods)} productos')
    if prods:
        print(f'  Ejemplo: {prods[0]["nombre"]} | Precio: {prods[0]["precio"]}')

print('catalogo_data.json generado OK')
