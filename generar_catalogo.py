import openpyxl, json, os

path = r'C:\Users\PC 1\Cotizaciones\Noviembre\Lista de Precios Nioval 2025 2 TRI +  (1).xlsx'
wb = openpyxl.load_workbook(path, read_only=True)
ws = wb['Sheet1']
rows = list(ws.iter_rows(values_only=True))

# Orden importa: el primero que hace match gana
CATEGORIAS = [
    ('herramientas', ['matraca', 'dado', 'dados', 'taladro', 'puntas phillips', 'desarmador', 'grip con adaptador',
                      'juego de herramientas', 'kit de', 'llave tubo', 'llave angular', 'pistola de lavado',
                      'juego de dados', 'autocle', 'impacto de aire', 'herramientas mecanica', 'herramientas reparacion']),
    ('griferia',    ['grifo', 'mezclador', 'mezcladora', 'llave mezcladora', 'monomando', 'fregadero',
                     'lavabo', 'tarja', 'regadera', 'ppr', 'maneral', 'chapeton', 'chapetón',
                     'valvula', 'válvula', 'temporizadora', 'griferia', 'grifer']),
    ('cerraduras',  ['cerradura', 'candado', 'loto', 'chapa', 'gatillo', 'laton', 'niquel']),
    ('mochilas',    ['mochila', 'maletín', 'maletin porta', 'lonchera', 'cangurera',
                     'bolsa termica', 'bolsa térmica', 'neceser', 'organizador de maquillaje',
                     'organizador de viaje', 'portafolio para laptop']),
    ('cintas',      ['cinta', 'sticker', 'reflejante', 'adhesiv', 'nano tape', 'magnetica', 'antiderrapante']),
    ('mascotas',    ['perro', 'gato', 'mascota', 'comedero', 'bebedero', 'rampa para', 'escalera para mascota', 'tapete entrenador']),
    ('audio',       ['bocina', 'parlante', 'auricular', 'audifono', 'audifonos', 'speaker', 'subwoofer', 'radio', 'cable para bocina']),
    ('sillas',      ['silla giratoria', 'silla de escritorio', 'silla de oficina']),
    ('otros',       []),
]

def categorizar(nombre):
    n = nombre.lower()
    for cat, keywords in CATEGORIAS:
        for kw in keywords:
            if kw in n:
                return cat
    return 'otros'

catalogo = {cat: [] for cat, _ in CATEGORIAS}

for r in rows[1:]:
    sku = r[0]
    nombre = str(r[2]).strip().replace('\n', '') if r[2] else None
    precio = r[3]
    precio_iva = r[5] if len(r) > 5 else None

    if not sku or not nombre or not precio:
        continue
    try:
        float(precio)
    except (TypeError, ValueError):
        continue

    cat = categorizar(nombre)
    prod = {
        'sku': str(sku).strip(),
        'nombre': nombre,
        'precio': round(float(precio), 2),
    }
    if precio_iva:
        try:
            prod['precio_iva'] = round(float(precio_iva), 2)
        except (TypeError, ValueError):
            pass
    catalogo[cat].append(prod)

# Eliminar categorias vacias
catalogo = {k: v for k, v in catalogo.items() if v}

for cat, prods in catalogo.items():
    print(f'{cat}: {len(prods)} productos')

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'catalogo_data.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(catalogo, f, ensure_ascii=False, indent=2)
print(f'\nTotal: {sum(len(v) for v in catalogo.values())} productos')
