# Prompts de Bruce - Agente de Ventas NIOVAL

Este directorio contiene los prompts utilizados por el agente Bruce.

## Archivos

- `system_prompt.txt` - Prompt principal del sistema (identidad, reglas, flujos)

## Cómo usar

```python
from prompts import obtener_system_prompt, cargar_prompt

# Obtener el prompt principal (con cache)
prompt = obtener_system_prompt()

# Cargar un prompt específico
otro_prompt = cargar_prompt("nombre_archivo")
```

## Edición

Para modificar el comportamiento de Bruce:
1. Edita el archivo `.txt` correspondiente
2. Reinicia el servidor para aplicar cambios
3. O llama `limpiar_cache()` para recargar sin reiniciar

## Notas

- Los prompts se cargan con encoding UTF-8
- Se mantiene cache en memoria para evitar lecturas repetidas
- El SYSTEM_PROMPT principal está en `system_prompt.txt`
