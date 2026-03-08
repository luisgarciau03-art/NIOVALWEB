# Estructura Modular - AgenteVentas

## Nueva Estructura de Carpetas

```
AgenteVentas/
├── config/                    # Configuración centralizada
│   └── __init__.py           # Variables de entorno, clientes API
│
├── utils/                     # Utilidades comunes
│   ├── __init__.py
│   ├── google_auth.py        # Autenticación Google (elimina duplicación)
│   └── phone_formatter.py    # Normalización de teléfonos mexicanos
│
├── adapters/                  # Adaptadores de servicios externos
│   ├── __init__.py
│   └── google_sheets/
│       ├── __init__.py
│       └── base.py           # Clase base para adapters de Sheets
│
├── prompts/                   # Prompts del agente (archivos .txt)
│   ├── __init__.py           # Funciones para cargar prompts
│   ├── README.md
│   └── system_prompt.txt     # SYSTEM_PROMPT de Bruce (extraer de agente_ventas.py)
│
├── core/                      # (Futuro) Lógica central
│   └── ...
│
├── server/                    # (Futuro) Componentes del servidor
│   ├── routes/
│   └── handlers/
│
└── [archivos actuales]        # Mantienen compatibilidad
    ├── agente_ventas.py
    ├── servidor_llamadas.py
    ├── nioval_sheets_adapter.py
    └── ...
```

## Cómo Usar la Nueva Estructura

### 1. Configuración Centralizada

**Antes:**
```python
# En cada archivo
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
# ... repetido en múltiples archivos
```

**Después:**
```python
from config import OPENAI_API_KEY, TWILIO_ACCOUNT_SID, get_openai_client

client = get_openai_client()  # Automáticamente usa GitHub Models o OpenAI
```

### 2. Autenticación Google Sheets

**Antes:**
```python
# Código repetido en nioval_sheets_adapter.py, resultados_sheets_adapter.py, etc.
def _autenticar(self):
    credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if credentials_json:
        credentials_dict = json.loads(credentials_json)
        creds = Credentials.from_service_account_info(...)
    else:
        creds = Credentials.from_service_account_file(...)
    client = gspread.authorize(creds)
    return client
```

**Después:**
```python
from utils.google_auth import crear_cliente_gspread

client = crear_cliente_gspread()  # Maneja automáticamente env o archivo
```

### 3. Normalización de Teléfonos

**Antes:**
```python
# En nioval_sheets_adapter.py línea 97-133
def normalizar_numero(numero):
    # ... código de normalización
```

**Después:**
```python
from utils.phone_formatter import normalizar_numero, formatear_numero_legible

numero_normalizado = normalizar_numero("662 101 2000")  # "+526621012000"
numero_legible = formatear_numero_legible("+526621012000")  # "662 101 2000"
```

### 4. Prompts desde Archivo

**Antes:**
```python
# En agente_ventas.py - 1500+ líneas de SYSTEM_PROMPT embebido
SYSTEM_PROMPT = """# IDENTIDAD Y ROL
Eres Bruce...
... (1500 líneas más) ...
"""
```

**Después:**
```python
from prompts import obtener_system_prompt

SYSTEM_PROMPT = obtener_system_prompt()  # Cargado desde prompts/system_prompt.txt
```

## Migración Gradual

### Paso 1: Extraer SYSTEM_PROMPT (Prioridad Alta)
1. Copiar contenido de SYSTEM_PROMPT a `prompts/system_prompt.txt`
2. En agente_ventas.py cambiar a: `from prompts import obtener_system_prompt`
3. Probar que funciona igual

### Paso 2: Usar utilidades comunes
1. En adapters, cambiar autenticación a usar `utils.google_auth`
2. Cambiar `normalizar_numero` a usar `utils.phone_formatter`

### Paso 3: Usar configuración centralizada
1. Importar variables desde `config` en lugar de `os.getenv()` directo
2. Usar `get_openai_client()` en lugar de crear cliente manualmente

## Beneficios

1. **Menos tokens en chat**: El SYSTEM_PROMPT no ocupa espacio en código Python
2. **Cambios localizados**: Modificar prompt sin tocar código
3. **Sin duplicación**: Autenticación y utilidades en un solo lugar
4. **Mantenibilidad**: Estructura clara para encontrar qué modificar
5. **Compatibilidad**: Los archivos originales siguen funcionando durante migración
