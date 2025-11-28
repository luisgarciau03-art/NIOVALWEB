from flask import Flask, render_template, request, jsonify
import requests
import os

# Limpia cualquier variable previa y configura credenciales
os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "C:\\Users\\PC 1\\niovalclientes-firebase-adminsdk-fbsvc-30b99db631.json"
print("Ruta credencial Firestore utilizada:", os.environ["GOOGLE_APPLICATION_CREDENTIALS"])


from google.cloud import firestore
import gspread
from google.oauth2.service_account import Credentials

def get_productos_from_sheet():
    creds_path = r"C:\Users\PC 1\niovalclientes-a38cae49d183.json"
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    credentials = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(credentials)
    sheet_id = "1jnktXCAb0kjViqzoCbv1Y9xAD-PbNPJr2RhZrXhIeHE"
    worksheet = gc.open_by_key(sheet_id).worksheet('LP')  # Lee la hoja llamada 'LP'
    headers = [h for h in worksheet.row_values(1) if h]  # Solo encabezados no vacíos
    print("Encabezados de la hoja LP:", headers)
    records = worksheet.get_all_records(expected_headers=headers)
    # Filtrar productos sin SKU válido (no vacío, no None)
    productos_validos = [r for r in records if str(r.get('SKU', '')).strip()]
    print("Ejemplo de producto:", productos_validos[0] if productos_validos else None)
    print("SKUs obtenidos:", [p['SKU'] for p in productos_validos])
    return productos_validos


API_KEY = "AIzaSyAOVuqvMxNKVM6jYwwaVQnUhr_g0k8qrQw"



def login_firebase(email, password, api_key):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    data = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(url, json=data).json()
    return response


app = Flask(__name__)

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
                # Aquí uid SE PASA CORRECTAMENTE Y NUNCA QUEDARÁ VACÍO
                return render_template("panel.html", user=user_data, uid=uid)
            else:
                print("Mostrando welcome.html")
                return render_template("welcome.html", uid=uid)
        else:
            error = "Correo o contraseña incorrectos"
            print("Error de autenticación con Firebase.")
    return render_template("login.html", error=error)

@app.route("/pedidos", methods=["GET", "POST"])
def pedidos_panel():
    uid = request.args.get("uid")
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
        productos_json = request.form.get("productos_json")
        print("Pedido recibido:", productos_json)
        # ...guardar en Firestore...

    return render_template("pedidos.html", pedidos=pedidos, productos=productos, precio_esquema=precio_esquema)

@app.route("/cotizaciones")
def cotizaciones_panel():
    uid = request.args.get("uid")
    print("Panel de cotizaciones, uid recibido =", uid)
    if not uid:
        return "UID no proporcionado", 400
    cotizaciones = get_cotizaciones(uid)
    return render_template("cotizaciones.html", cotizaciones=cotizaciones)

if __name__ == "__main__":
    app.run(debug=True)