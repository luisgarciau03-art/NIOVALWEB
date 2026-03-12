from flask import Flask, render_template, request, jsonify, session
import requests
import os
import json
import base64
import tempfile

# --- RAILWAY: Inyectar service accounts desde env vars base64 ---
def _setup_service_account_file(env_var, fallback_filename):
    """Crea archivo temporal desde env var base64, o usa archivo local si existe."""
    b64 = os.environ.get(env_var)
    if b64:
        try:
            decoded = base64.b64decode(b64)
            tmp = tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False)
            tmp.write(decoded)
            tmp.close()
            print(f"[RAILWAY] {env_var} cargado desde env var -> {tmp.name}")
            return tmp.name
        except Exception as e:
            print(f"[ERROR] No se pudo decodificar {env_var}: {e}")
    if os.path.exists(fallback_filename):
        print(f"[LOCAL] Usando archivo local: {fallback_filename}")
        return fallback_filename
    print(f"[WARN] No se encontro {env_var} ni {fallback_filename}")
    return fallback_filename

FIRESTORE_CREDS_PATH = _setup_service_account_file(
    "FIRESTORE_SERVICE_ACCOUNT_B64",
    "niovalclientes-firebase-adminsdk-fbsvc-30b99db631.json"
)
SHEETS_CREDS_PATH = _setup_service_account_file(
    "SHEETS_SERVICE_ACCOUNT_B64",
    "niovalclientes-a38cae49d183.json"
)

os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = FIRESTORE_CREDS_PATH
print("Ruta credencial Firestore utilizada:", os.environ["GOOGLE_APPLICATION_CREDENTIALS"])


from google.cloud import firestore
import gspread
from google.oauth2.service_account import Credentials

def get_productos_from_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    credentials = Credentials.from_service_account_file(SHEETS_CREDS_PATH, scopes=scopes)
    gc = gspread.authorize(credentials)
    sheet_id = os.environ.get("PRODUCTOS_SHEET_ID", "1jnktXCAb0kjViqzoCbv1Y9xAD-PbNPJr2RhZrXhIeHE")
    worksheet = gc.open_by_key(sheet_id).worksheet('LP')  # Lee la hoja llamada 'LP'
    headers = [h for h in worksheet.row_values(1) if h]  # Solo encabezados no vacíos
    print("Encabezados de la hoja LP:", headers)
    records = worksheet.get_all_records(expected_headers=headers)
    # Filtrar productos sin SKU válido (no vacío, no None)
    productos_validos = [r for r in records if str(r.get('SKU', '')).strip()]
    print("Ejemplo de producto:", productos_validos[0] if productos_validos else None)
    print("SKUs obtenidos:", [p['SKU'] for p in productos_validos])
    return productos_validos


API_KEY = os.environ.get("FIREBASE_API_KEY", "AIzaSyAOVuqvMxNKVM6jYwwaVQnUhr_g0k8qrQw")



def login_firebase(email, password, api_key):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    data = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(url, json=data).json()
    return response


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "NIOVALWEB_SUPER_SECRET_KEY_2025")

# Ruta para obtener productos desde Google Sheets
@app.route("/productos")
def productos():
    productos = get_productos_from_sheet()
    return jsonify(productos)

def get_user_data(uid):
    db = firestore.Client()
    doc_ref = db.collection("usuarios").document(uid)
    doc = doc_ref.get()
    print(f"Buscando usuario en Firestore: {uid}")
    if doc.exists:
        print("Documento Firestore encontrado:", doc.to_dict())
        return doc.to_dict()
    else:
        print("Documento Firestore NO encontrado para UID:", uid)
        return None

def get_pedidos(uid):
    db = firestore.Client()
    pedidos_ref = db.collection("pedidos").where("uid", "==", uid)
    pedidos = [x.to_dict() for x in pedidos_ref.stream()]
    print(f"Pedidos para uid {uid}: {pedidos}")
    return pedidos

def get_cotizaciones(uid):
    db = firestore.Client()
    cotizaciones_ref = db.collection("cotizaciones").where("uid", "==", uid)
    cotizaciones = [x.to_dict() for x in cotizaciones_ref.stream()]
    print(f"Cotizaciones para uid {uid}: {cotizaciones}")
    return cotizaciones

@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        print("Request form:", request.form)
        email = request.form.get("email")
        password = request.form.get("password")
        print("Email:", email)
        print("Password:", password)
        resp = login_firebase(email, password, API_KEY)
        print("Response de Firebase:", resp)
        if resp.get("localId"):
            uid = resp["localId"]  # CRÍTICO: obtener UID correcto para todos los módulos
            print("Enviando a panel.html uid=", uid)
            user_data = get_user_data(uid)
            print("Datos usuario Firestore:", user_data)
            if user_data:
                session['uid'] = uid  # <--- Guardar uid en la sesión
                esquema_raw = user_data.get("Esquema", "Distribuidor")
                # Aquí uid SE PASA CORRECTAMENTE Y NUNCA QUEDARÁ VACÍO
                return render_template("panel.html", user=user_data, uid=uid, esquema_raw=esquema_raw)
            else:
                print("Mostrando welcome.html")
                return render_template("welcome.html", uid=uid)
        else:
            error = "Correo o contraseña incorrectos"
            print("Error de autenticación con Firebase.")
    return render_template("login.html", error=error)

@app.route("/pedidos", methods=["GET", "POST"])
def pedidos_panel():
    # Permitir obtener uid tanto por GET (args) como por POST (form)
    print("request.args:", dict(request.args))
    print("request.form:", dict(request.form))
    print("request.json:", request.get_json(silent=True))
    uid = session.get("uid") or request.args.get("uid") or request.form.get("uid")
    if not uid and request.is_json:
        data = request.get_json()
        if data:
            uid = data.get("uid")
    print("Panel de pedidos, uid recibido =", uid)
    if not uid:
        return "UID no proporcionado", 400

    # Obtener productos desde Google Sheets
    productos = get_productos_from_sheet()
    print("Productos enviados a la plantilla:", productos)

    # Obtener esquema de usuario desde Firestore
    user_data = get_user_data(uid)
    esquema_raw = user_data.get("Esquema", "Distribuidor") if user_data else "Distribuidor"
    print(f"Valor crudo de esquema Firestore: {esquema_raw}")
    esquema = str(esquema_raw).strip().lower()
    esquema_map = {
        "distribuidor": "Distribuidor",
        "mayorista": "Mayorista",
        "acuerdo": "Acuerdo"
    }
    precio_esquema = esquema_map.get(esquema, "Distribuidor")
    print(f"Esquema normalizado: {esquema} | Columna de precio: {precio_esquema}")

    pedidos = get_pedidos(uid)

    # Procesar formulario POST para guardar pedido (solo estructura, no guardado aún)
    if request.method == "POST":
        import json
        valor_crudo = request.form.get("productos_json", "")
        print("Valor crudo productos_json:", valor_crudo)
        productos = json.loads(valor_crudo or "[]")
        print("Pedido recibido:", productos)
        # Obtener datos de usuario
        user_data = get_user_data(uid)
        nombre = user_data.get('nombre', '') if user_data else ''
        esquema = user_data.get('Esquema', '') if user_data else ''
        metodo_pago = user_data.get('Metodo De Pago', '') if user_data else ''

        # --- INTEGRACIÓN FLUJO PRINCIPAL script45t.py ---
        try:
            from script45t import extraer_datos_cotizacion, export_pdf_rango, insertar_fila_ventas, guardar_productos_en_bd
            print("[LOG] INICIO integración script45t.py")
            # Preparar productos para hoja BD
            productos_bd = []
            for p in productos:
                print("[LOG] Producto recibido:", p)
                prod = {
                    'SKU': p.get('sku', ''),
                    'Nombre': (p.get('producto') or {}).get('Nombre', ''),
                    'Cantidad': p.get('cantidad', ''),
                    'Precio': (p.get('producto') or {}).get(precio_esquema, '')
                }
                productos_bd.append(prod)
            print("[LOG] Productos BD construidos:", productos_bd)
            print("[LOG] Guardando productos en hoja BD...")
            guardar_productos_en_bd(productos_bd, nombre, esquema, metodo_pago)
            print("[LOG] Productos guardados en hoja BD.")

            print("[LOG] Extrayendo datos de cotización...")
            # Se espera que extraer_datos_cotizacion retorne:
            # pdf_path, pdf_filename, drive_url, nombre_cliente, esquema, monto, num_factura
            pdf_path, pdf_filename, drive_url, nombre_cliente, esquema, monto, num_factura = extraer_datos_cotizacion()
            print(f"[LOG] Datos cotización: nombre_cliente={nombre_cliente}, num_factura={num_factura}, monto={monto}, esquema={esquema}, pdf_path={pdf_path}, pdf_filename={pdf_filename}, drive_url={drive_url}")

            # Obtener mes actual
            from datetime import datetime
            mes_actual = datetime.now().strftime('%B')

            if pdf_path:
                print("[LOG] Insertando fila en hoja Ventas...")
                insertar_fila_ventas(drive_url or "", nombre_cliente, monto, num_factura, esquema, mes_actual)
                print("[LOG] Fila insertada en hoja Ventas.")
            mensaje = "¡Pedido procesado y registrado en hoja BD y Ventas!"
            print("[LOG] FIN integración script45t.py")
        except Exception as e:
            import traceback
            print("[ERROR] Error en integración con script45t.py:", e)
            print(traceback.format_exc())
            mensaje = f"Error al procesar pedido: {e}"

        esquema_raw = user_data.get("Esquema", "Distribuidor") if user_data else "Distribuidor"
        return render_template("panel.html", user=user_data, uid=uid, mensaje=mensaje, esquema_raw=esquema_raw)

    return render_template("pedidos.html", pedidos=pedidos, productos=productos, precio_esquema=precio_esquema, uid=uid)

@app.route("/cotizaciones")
def cotizaciones_panel():
    uid = request.args.get("uid")
    print("Panel de cotizaciones, uid recibido =", uid)
    if not uid:
        return "UID no proporcionado", 400
    cotizaciones = get_cotizaciones(uid)
    return render_template("cotizaciones.html", cotizaciones=cotizaciones)

@app.route('/upload_to_drive')
def upload_to_drive():
    if 'credentials' not in session:
        return redirect('authorize')
    credentials = google.oauth2.credentials.Credentials(
        **session['credentials']
    )
    # Obtener nombre y num_factura de la sesión o por parámetros
    nombre_cliente = session.get('nombre_cliente', 'cliente')
    num_factura = session.get('num_factura', 'factura')
    pdf_filename = f"{nombre_cliente}-{num_factura}.pdf"
    pdf_path = session.get('pdf_path', pdf_filename)  # Ruta real del PDF generado
    drive_service = googleapiclient.discovery.build('drive', 'v3', credentials=credentials)
    file_metadata = {'name': pdf_filename}
    media = googleapiclient.http.MediaFileUpload(pdf_path, mimetype='application/pdf')
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id,webViewLink').execute()
    session['credentials'] = credentials_to_dict(credentials)
    return f"Archivo subido. ID: {file.get('id')}, Link: {file.get('webViewLink')}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)