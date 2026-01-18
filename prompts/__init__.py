"""
Módulo para gestión de prompts del agente Bruce.

Los prompts se cargan desde archivos .txt para:
1. Reducir tamaño del código Python
2. Facilitar edición sin tocar código
3. Permitir versionado independiente
"""

import os

# Directorio de prompts
PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def cargar_prompt(nombre_archivo: str) -> str:
    """
    Carga un prompt desde archivo .txt

    Args:
        nombre_archivo: Nombre del archivo sin extensión (ej: "system_prompt")

    Returns:
        Contenido del prompt como string

    Raises:
        FileNotFoundError: Si el archivo no existe
    """
    ruta = os.path.join(PROMPTS_DIR, f"{nombre_archivo}.txt")

    if not os.path.exists(ruta):
        raise FileNotFoundError(f"Prompt no encontrado: {ruta}")

    with open(ruta, 'r', encoding='utf-8') as f:
        return f.read()


def cargar_prompt_con_variables(nombre_archivo: str, variables: dict) -> str:
    """
    Carga un prompt y reemplaza variables con formato {variable}

    Args:
        nombre_archivo: Nombre del archivo sin extensión
        variables: Dict con variables a reemplazar

    Returns:
        Prompt con variables reemplazadas

    Ejemplo:
        prompt = cargar_prompt_con_variables("saludo", {"nombre": "Juan"})
        # Si saludo.txt contiene "Hola {nombre}", retorna "Hola Juan"
    """
    contenido = cargar_prompt(nombre_archivo)

    for key, value in variables.items():
        contenido = contenido.replace(f"{{{key}}}", str(value))

    return contenido


def listar_prompts() -> list:
    """Lista todos los prompts disponibles"""
    archivos = os.listdir(PROMPTS_DIR)
    return [f.replace('.txt', '') for f in archivos if f.endswith('.txt')]


# Cache de prompts cargados
_cache_prompts = {}


def obtener_system_prompt() -> str:
    """
    Obtiene el SYSTEM_PROMPT principal de Bruce.
    Usa cache para evitar lecturas repetidas del disco.
    """
    if 'system_prompt' not in _cache_prompts:
        _cache_prompts['system_prompt'] = cargar_prompt('system_prompt')

    return _cache_prompts['system_prompt']


def limpiar_cache():
    """Limpia el cache de prompts (útil para recargar cambios)"""
    global _cache_prompts
    _cache_prompts = {}
