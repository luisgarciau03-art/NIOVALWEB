# Guía: Cambio de Voz en Bruce W

## Sistema de Respaldos y Gestión de Voces

Este sistema permite cambiar la voz de Bruce manteniendo respaldos completos del cache de audios para poder volver atrás en cualquier momento.

---

## Inicio Rápido

### 1. Crear Respaldo del Cache Actual

**SIEMPRE hacer esto ANTES de cualquier cambio:**

```bash
cd "C:\Users\PC 1\AgenteVentas"
python gestor_voces_elevenlabs.py
# Opción 3: Crear respaldo
```

O directamente:

```python
from gestor_voces_elevenlabs import crear_respaldo
crear_respaldo("antes_cambio_voz_femenina")
```

### 2. Cambiar a Voz Femenina

```bash
python gestor_voces_elevenlabs.py
# Opción 4: Regenerar cache con nueva voz
# Seleccionar: domi_femenino
```

**Costo**: 86,660 créditos (~$19 USD en plan Creator)

### 3. Restaurar Voz Original

Si no te gusta la nueva voz:

```bash
python gestor_voces_elevenlabs.py
# Opción 5: Restaurar respaldo
# Seleccionar el respaldo que creaste en paso 1
```

---

## Voces Disponibles

### 1. Bruce - Voz Masculina Original ✅
- **ID**: `7uSWXMmzGnsyxZwYFfmK`
- **Tipo**: Masculina profesional mexicana
- **Estado**: Actual en producción
- **Key**: `bruce_masculino`

### 2. Domi - Voz Femenina ⭐ RECOMENDADA
- **ID**: `AZnzlk1XvdvUeBnXmlld`
- **Tipo**: Femenina profesional y amigable
- **Ideal para**: Cambio a voz femenina manteniendo profesionalismo
- **Key**: `domi_femenino`

### 3. Jessica - Voz Femenina Profesional
- **ID**: `cgSgspJ2msm6clMCkdW9`
- **Tipo**: Femenina clara y profesional
- **Ideal para**: Tono más formal y corporativo
- **Key**: `jessica_femenino`

### 4. Matilda - Voz Femenina Cálida
- **ID**: `XrExE9yKIg1WjnnlVkGX`
- **Tipo**: Femenina cálida y amigable
- **Ideal para**: Tono más cercano y empático
- **Key**: `matilda_femenino`

---

## Flujo Completo de Cambio

### Paso a Paso Seguro

```bash
# 1. Entrar al directorio
cd "C:\Users\PC 1\AgenteVentas"

# 2. Crear respaldo (CRÍTICO)
python -c "from gestor_voces_elevenlabs import crear_respaldo; crear_respaldo('backup_voz_masculina_original')"

# 3. Listar voces disponibles
python -c "from gestor_voces_elevenlabs import listar_voces; listar_voces()"

# 4. Regenerar cache con nueva voz
python -c "from gestor_voces_elevenlabs import regenerar_cache_con_nueva_voz; regenerar_cache_con_nueva_voz('AZnzlk1XvdvUeBnXmlld', crear_backup=True)"

# 5. Verificar que funcionó
ls audio_cache/*.mp3 | measure

# 6. Hacer commit y push a Railway
git add audio_cache/
git commit -m "Cambio de voz: Bruce masculino → Domi femenino"
git push origin main

# 7. Verificar en Railway después de deploy
# https://nioval-webhook-server-production.up.railway.app/info-cache
```

### Si Algo Sale Mal

```bash
# Restaurar respaldo inmediatamente
python -c "from gestor_voces_elevenlabs import restaurar_respaldo; restaurar_respaldo('backup_voz_masculina_original')"

# Verificar restauración
git status
git diff audio_cache/cache_audios.json
```

---

## Comandos Útiles

### Ver Respaldos Existentes

```python
from gestor_voces_elevenlabs import listar_respaldos
listar_respaldos()
```

### Crear Respaldo con Nombre Personalizado

```python
from gestor_voces_elevenlabs import crear_respaldo
crear_respaldo("antes_prueba_jessica")
```

### Regenerar Solo Para Probar (sin commit)

```python
from gestor_voces_elevenlabs import regenerar_cache_con_nueva_voz

# Regenerar
regenerar_cache_con_nueva_voz('AZnzlk1XvdvUeBnXmlld')

# Probar localmente llamando a hacer_llamada.py
# Si no gusta, restaurar:
from gestor_voces_elevenlabs import restaurar_respaldo
restaurar_respaldo('auto_backup_antes_cambio_voz_20260211_123456')
```

---

## Estructura de Respaldos

```
audio_cache_backups/
├── backup_voz_masculina_original/
│   ├── metadata.json              # Info del respaldo
│   ├── cache_audios.json          # Metadata de audios
│   ├── cache_frases_frecuentes.json
│   └── *.mp3                      # 1,238 archivos de audio
│
├── backup_antes_cambio_voz_20260211_203045/
│   └── ...
│
└── auto_backup_antes_restaurar_20260211_210530/
    └── ...
```

### Metadata.json

```json
{
  "fecha_creacion": "2026-02-11T20:30:45",
  "nombre": "backup_voz_masculina_original",
  "archivos_respaldados": 1238,
  "tamano_mb": 118.19,
  "voice_id": "7uSWXMmzGnsyxZwYFfmK",
  "voz_nombre": "Bruce - Voz Masculina Original"
}
```

---

## Costos y Tiempos

### Regeneración Completa (1,238 audios)

| Métrica | Valor |
|---------|-------|
| Créditos necesarios | 86,660 |
| Plan requerido | Creator ($22/month) |
| Tiempo estimado | 15-20 minutos |
| Espacio en disco | ~118 MB |
| Audios regenerados | 1,238 MP3 |

### Rate Limiting

El script incluye rate limiting automático:
- Pausa de 1 segundo cada 10 audios
- Evita sobrepasar límites de API de ElevenLabs
- Tiempo total: ~20 minutos para 1,238 audios

---

## Troubleshooting

### Error: "ELEVENLABS_API_KEY no encontrada"

```bash
# Verificar .env
cat .env | grep ELEVENLABS_API_KEY

# O exportar manualmente
export ELEVENLABS_API_KEY="tu_api_key_aqui"
```

### Error: "No se encontró cache_audios.json"

```bash
# Verificar que existe el cache
ls audio_cache/cache_audios.json

# Si no existe, necesitas generar el cache primero
python generar_cache_audios.py
```

### Respaldo Ocupa Demasiado Espacio

```bash
# Ver tamaño de respaldos
du -sh audio_cache_backups/*

# Eliminar respaldos antiguos manualmente
rm -rf audio_cache_backups/backup_old_20250101_*

# O usar el gestor
python gestor_voces_elevenlabs.py
# Navegar a directorio y eliminar manualmente
```

### Railway No Detecta el Cambio

```bash
# Forzar commit de todos los archivos
git add -f audio_cache/*.mp3
git add audio_cache/cache_audios.json
git commit -m "Forzar actualización cache de audio"
git push origin main

# Verificar en Railway logs
# https://railway.app/project/[tu-proyecto]/logs
```

---

## Mejores Prácticas

### ✅ Hacer Siempre

1. **Crear respaldo ANTES de cualquier cambio**
2. **Probar localmente antes de hacer commit**
3. **Verificar metadata.json del respaldo**
4. **Hacer git commit con mensaje descriptivo**
5. **Monitorear Railway logs post-deploy**

### ❌ Nunca Hacer

1. **NO eliminar audio_cache/ sin respaldo**
2. **NO regenerar sin verificar créditos disponibles**
3. **NO hacer push a Railway sin probar localmente**
4. **NO eliminar respaldos antes de confirmar que nueva voz funciona**
5. **NO cambiar voice_id en agente_ventas.py manualmente** (usar el gestor)

---

## Checklist de Cambio de Voz

```
□ 1. Crear respaldo con nombre descriptivo
□ 2. Verificar créditos disponibles en ElevenLabs (>86,660)
□ 3. Regenerar cache con nueva voz
□ 4. Verificar que se generaron 1,238 MP3
□ 5. Probar 2-3 llamadas localmente
□ 6. Revisar que audio suena correcto
□ 7. Hacer commit descriptivo
□ 8. Push a Railway
□ 9. Esperar deploy (2-3 min)
□ 10. Hacer llamada de prueba en producción
□ 11. Verificar /info-cache en Railway
□ 12. Si todo OK, marcar respaldo como "stable"
□ 13. Si algo falla, restaurar respaldo inmediatamente
```

---

## Soporte

Si tienes problemas:

1. **Verificar logs**: Railway dashboard → Logs
2. **Revisar respaldos**: `python gestor_voces_elevenlabs.py` → Opción 2
3. **Restaurar último respaldo estable**: Opción 5
4. **Verificar créditos ElevenLabs**: https://elevenlabs.io/app/usage

---

## Próximos Pasos

Después de cambiar la voz exitosamente:

1. Monitorear bugs post-cambio (primeras 24h)
2. Ajustar voice_settings si es necesario (stability, similarity_boost)
3. Recopilar feedback de llamadas
4. Mantener respaldo de voz anterior por al menos 1 semana
