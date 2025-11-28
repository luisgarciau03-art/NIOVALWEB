from flask import Flask, render_template, request
import requests
import os

# LIMPIA cualquier variable previa equivocada y fuerza el nuevo valor
os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "C:\\Users\\PC 1\\niovalclientes-firebase-adminsdk-fbsvc-30b99db631.json"
print("Ruta credencial Firestore utilizada:", os.environ["GOOGLE_APPLICATION_CREDENTIALS"])

from google.cloud import firestore

API_KEY = "AIzaSyAOVuqvMxNKVM6jYwwaVQnUhr_g0k8qrQw"

def login_firebase(email, password, api_key):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    data = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(url, json=data).json()
    return response

app = Flask(__name__)

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
            user_data = get_user_data(resp["localId"])
            print("Datos usuario Firestore:", user_data)
            if user_data:
                # Se pasa el uid correcto al panel.
                return render_template("panel.html", user=user_data, uid=resp["localId"])
            else:
                print("Mostrando welcome.html")
                return render_template("welcome.html", uid=resp['localId'])
        else:
            error = "Correo o contraseña incorrectos"
            print("Error de autenticación con Firebase.")
    return render_template("login.html", error=error)

@app.route("/pedidos")
def pedidos_panel():
    uid = request.args.get("uid")
    if not uid:
        return "UID no proporcionado", 400
    pedidos = get_pedidos(uid)
    return render_template("pedidos.html", pedidos=pedidos)

@app.route("/cotizaciones")
def cotizaciones_panel():
    uid = request.args.get("uid")
    if not uid:
        return "UID no proporcionado", 400
    cotizaciones = get_cotizaciones(uid)
    return render_template("cotizaciones.html", cotizaciones=cotizaciones)

if __name__ == "__main__":
    app.run(debug=True)