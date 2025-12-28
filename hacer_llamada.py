"""
Script para hacer llamadas salientes con el agente Bruce W de ElevenLabs
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuración
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID", "tu-agent-id")


def hacer_llamada(telefono_destino: str, nombre_prospecto: str = ""):
    """
    Hace una llamada saliente usando el agente de ElevenLabs
    
    Args:
        telefono_destino: Número a llamar (formato: +52XXXXXXXXXX o +1XXXXXXXXXX)
        nombre_prospecto: Nombre del prospecto (opcional)
    """
    
    url = f"https://api.elevenlabs.io/v1/convai/conversation/initiate_call"
    
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "agent_id": ELEVENLABS_AGENT_ID,
        "phone_number": telefono_destino
    }
    
    print(f"\n📞 Iniciando llamada a {telefono_destino}...")
    if nombre_prospecto:
        print(f"   Prospecto: {nombre_prospecto}")
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Llamada iniciada exitosamente!")
            print(f"   Call ID: {data.get('call_id', 'N/A')}")
            return data
        else:
            print(f"❌ Error al iniciar llamada:")
            print(f"   Status: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def llamar_lista(lista_telefonos: list):
    """
    Llama a una lista de números
    
    Args:
        lista_telefonos: Lista de dicts con 'telefono' y 'nombre'
        Ejemplo: [
            {"telefono": "+52XXXXXXXXXX", "nombre": "Ferretería Los Pinos"},
            {"telefono": "+52YYYYYYYYYY", "nombre": "Ferretería El Martillo"}
        ]
    """
    print(f"\n🚀 Iniciando {len(lista_telefonos)} llamadas...\n")
    
    resultados = []
    
    for i, contacto in enumerate(lista_telefonos, 1):
        telefono = contacto.get("telefono")
        nombre = contacto.get("nombre", "")
        
        print(f"\n--- Llamada {i}/{len(lista_telefonos)} ---")
        resultado = hacer_llamada(telefono, nombre)
        
        resultados.append({
            "telefono": telefono,
            "nombre": nombre,
            "exitosa": resultado is not None
        })
        
        # Pausa entre llamadas (opcional)
        if i < len(lista_telefonos):
            import time
            print("\n⏳ Esperando 30 segundos antes de la siguiente llamada...")
            time.sleep(30)
    
    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE LLAMADAS")
    print("=" * 60)
    exitosas = sum(1 for r in resultados if r["exitosa"])
    print(f"Total: {len(resultados)}")
    print(f"Exitosas: {exitosas}")
    print(f"Fallidas: {len(resultados) - exitosas}")
    print("=" * 60 + "\n")
    
    return resultados


def menu_interactivo():
    """Menú interactivo para hacer llamadas"""
    print("\n" + "=" * 60)
    print("📞 SISTEMA DE LLAMADAS SALIENTES - NIOVAL")
    print("=" * 60)
    print("\nOpciones:")
    print("1. Llamar a un solo número")
    print("2. Llamar a múltiples números")
    print("3. Salir")
    
    while True:
        opcion = input("\nSelecciona una opción (1-3): ").strip()
        
        if opcion == "1":
            # Llamada individual
            print("\n--- LLAMADA INDIVIDUAL ---")
            telefono = input("Número de teléfono (ej: +521234567890): ").strip()
            nombre = input("Nombre del prospecto (opcional): ").strip()
            
            if telefono:
                hacer_llamada(telefono, nombre if nombre else "Cliente")
            else:
                print("❌ Debes ingresar un número de teléfono")
            
            continuar = input("\n¿Hacer otra llamada? (s/n): ").strip().lower()
            if continuar != 's':
                break
                
        elif opcion == "2":
            # Llamadas múltiples
            print("\n--- LLAMADAS MÚLTIPLES ---")
            cantidad = input("¿Cuántos números vas a llamar?: ").strip()
            
            try:
                cantidad = int(cantidad)
                lista = []
                
                for i in range(cantidad):
                    print(f"\n--- Número {i+1}/{cantidad} ---")
                    telefono = input(f"Teléfono {i+1} (ej: +521234567890): ").strip()
                    nombre = input(f"Nombre {i+1} (opcional): ").strip()
                    
                    if telefono:
                        lista.append({
                            "telefono": telefono,
                            "nombre": nombre if nombre else f"Cliente {i+1}"
                        })
                
                if lista:
                    confirmar = input(f"\n¿Llamar a {len(lista)} números? (s/n): ").strip().lower()
                    if confirmar == 's':
                        llamar_lista(lista)
                    else:
                        print("❌ Llamadas canceladas")
                else:
                    print("❌ No se agregaron números")
                    
            except ValueError:
                print("❌ Cantidad inválida")
            
            break
            
        elif opcion == "3":
            print("\n👋 ¡Hasta luego!")
            break
        else:
            print("❌ Opción inválida, intenta de nuevo")


if __name__ == "__main__":
    menu_interactivo()
