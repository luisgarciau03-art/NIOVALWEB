# -*- coding: utf-8 -*-
"""
Descarga logs de Railway usando la API GraphQL
No requiere Railway CLI - solo necesitas tu API Token
"""
import requests
import os
from datetime import datetime

# Configuración
RAILWAY_API_URL = "https://backboard.railway.app/graphql/v2"
CARPETA_LOGS = "C:\\Users\\PC 1\\AgenteVentas\\LOGS"

def obtener_token():
    """Obtiene el token de Railway desde variable de entorno o archivo"""
    # Primero buscar en variable de entorno
    token = os.environ.get("RAILWAY_TOKEN")
    if token:
        return token

    # Buscar en archivo .railway_token
    token_file = os.path.join(os.path.dirname(__file__), ".railway_token")
    if os.path.exists(token_file):
        with open(token_file, 'r') as f:
            return f.read().strip()

    return None

def guardar_token(token):
    """Guarda el token en archivo local"""
    token_file = os.path.join(os.path.dirname(__file__), ".railway_token")
    with open(token_file, 'w') as f:
        f.write(token)
    print(f"   Token guardado en: {token_file}")

def obtener_proyecto_y_servicio(token):
    """Obtiene el ID del proyecto y servicio de Railway"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Query para obtener proyectos
    query = """
    query {
        me {
            projects {
                edges {
                    node {
                        id
                        name
                        services {
                            edges {
                                node {
                                    id
                                    name
                                }
                            }
                        }
                        environments {
                            edges {
                                node {
                                    id
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """

    response = requests.post(
        RAILWAY_API_URL,
        headers=headers,
        json={"query": query}
    )

    if response.status_code != 200:
        print(f"   Error al obtener proyectos: {response.status_code}")
        print(f"   {response.text}")
        return None, None, None

    data = response.json()

    if "errors" in data:
        print(f"   Error: {data['errors']}")
        return None, None, None

    # Buscar proyecto nioval
    projects = data.get("data", {}).get("me", {}).get("projects", {}).get("edges", [])

    for proj in projects:
        project = proj["node"]
        if "nioval" in project["name"].lower():
            project_id = project["id"]
            project_name = project["name"]

            # Obtener servicio
            services = project.get("services", {}).get("edges", [])
            service_id = services[0]["node"]["id"] if services else None

            # Obtener environment (producción)
            environments = project.get("environments", {}).get("edges", [])
            env_id = None
            for env in environments:
                if "production" in env["node"]["name"].lower():
                    env_id = env["node"]["id"]
                    break
            if not env_id and environments:
                env_id = environments[0]["node"]["id"]

            print(f"   Proyecto: {project_name}")
            return project_id, service_id, env_id

    print("   No se encontró proyecto 'nioval'")
    return None, None, None

def descargar_logs(token, project_id, service_id, env_id, limite=500):
    """Descarga logs del servicio usando la API de Railway"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Query para obtener logs
    # Nota: La API de Railway usa deploymentLogs, no logs directos
    query = """
    query($projectId: String!, $environmentId: String!, $serviceId: String!, $limit: Int!) {
        deploymentLogs(
            projectId: $projectId
            environmentId: $environmentId
            serviceId: $serviceId
            limit: $limit
        ) {
            timestamp
            message
        }
    }
    """

    variables = {
        "projectId": project_id,
        "environmentId": env_id,
        "serviceId": service_id,
        "limit": limite
    }

    response = requests.post(
        RAILWAY_API_URL,
        headers=headers,
        json={"query": query, "variables": variables}
    )

    if response.status_code != 200:
        print(f"   Error al descargar logs: {response.status_code}")
        return None

    data = response.json()

    if "errors" in data:
        # Intentar con query alternativa
        return descargar_logs_alternativo(token, project_id, service_id, env_id, limite)

    logs_data = data.get("data", {}).get("deploymentLogs", [])

    if not logs_data:
        return descargar_logs_alternativo(token, project_id, service_id, env_id, limite)

    # Formatear logs
    logs_text = ""
    for log in logs_data:
        timestamp = log.get("timestamp", "")
        message = log.get("message", "")
        logs_text += f"{timestamp} {message}\n"

    return logs_text

def descargar_logs_alternativo(token, project_id, service_id, env_id, limite):
    """Intenta descargar logs con query alternativa"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Query alternativa - obtener deployment activo primero
    query_deployment = """
    query($projectId: String!, $environmentId: String!, $serviceId: String!) {
        deployments(
            projectId: $projectId
            environmentId: $environmentId
            serviceId: $serviceId
            first: 1
        ) {
            edges {
                node {
                    id
                    status
                }
            }
        }
    }
    """

    variables = {
        "projectId": project_id,
        "environmentId": env_id,
        "serviceId": service_id
    }

    response = requests.post(
        RAILWAY_API_URL,
        headers=headers,
        json={"query": query_deployment, "variables": variables}
    )

    if response.status_code != 200:
        print(f"   Error obteniendo deployment: {response.status_code}")
        return None

    data = response.json()

    if "errors" in data:
        print(f"   Error: {data['errors'][0].get('message', data['errors'])}")
        print("\n   La API de Railway tiene limitaciones para logs.")
        print("   Usa el método manual: python descargar_logs_web.py")
        return None

    deployments = data.get("data", {}).get("deployments", {}).get("edges", [])

    if not deployments:
        print("   No se encontraron deployments")
        return None

    deployment_id = deployments[0]["node"]["id"]

    # Ahora obtener logs del deployment
    query_logs = """
    query($deploymentId: String!, $limit: Int!) {
        deploymentLogs(deploymentId: $deploymentId, limit: $limit) {
            timestamp
            message
        }
    }
    """

    response = requests.post(
        RAILWAY_API_URL,
        headers=headers,
        json={"query": query_logs, "variables": {"deploymentId": deployment_id, "limit": limite}}
    )

    if response.status_code != 200:
        return None

    data = response.json()

    if "errors" in data:
        print(f"   La API no permite acceso a logs directamente.")
        print("   Usa: python descargar_logs_web.py")
        return None

    logs_data = data.get("data", {}).get("deploymentLogs", [])

    logs_text = ""
    for log in logs_data:
        timestamp = log.get("timestamp", "")
        message = log.get("message", "")
        logs_text += f"{timestamp} {message}\n"

    return logs_text

def main():
    print("\n" + "="*70)
    print("   DESCARGADOR DE LOGS - RAILWAY API")
    print("="*70 + "\n")

    # Crear carpeta si no existe
    os.makedirs(CARPETA_LOGS, exist_ok=True)

    # Obtener token
    token = obtener_token()

    if not token:
        print("   No se encontró token de Railway.")
        print("\n   PASOS PARA OBTENER TU TOKEN:")
        print("   1. Ve a: https://railway.app/account/tokens")
        print("   2. Crea un nuevo token")
        print("   3. Copia el token")
        print("")

        token = input("   Pega tu token aquí: ").strip()

        if not token:
            print("\n   Cancelado.")
            return

        guardar_token(token)

    print(f"\n   Buscando proyecto...")

    # Obtener IDs
    project_id, service_id, env_id = obtener_proyecto_y_servicio(token)

    if not project_id:
        print("\n   No se pudo encontrar el proyecto.")
        print("   Verifica que el token tenga permisos correctos.")
        return

    print(f"\n   Descargando logs...")

    # Descargar logs
    logs = descargar_logs(token, project_id, service_id, env_id, limite=500)

    if not logs:
        print("\n   No se pudieron descargar los logs via API.")
        print("\n   ALTERNATIVA: Usa el método manual")
        print("      python descargar_logs_web.py")
        return

    # Guardar logs
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"logs_railway_{timestamp}.txt"
    filepath = os.path.join(CARPETA_LOGS, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(logs)

    print(f"\n   Logs guardados en: {filepath}")
    print(f"   Tamaño: {len(logs)} caracteres")

    # Preguntar si analizar
    print("\n" + "="*70)
    respuesta = input("   ¿Analizar logs ahora? (s/n): ").strip().lower()

    if respuesta in ['s', 'si', 'y', 'yes', '']:
        os.system(f'python analizar_logs_railway.py "{filepath}"')

if __name__ == "__main__":
    main()
