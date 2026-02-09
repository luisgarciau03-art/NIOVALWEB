# INSTRUCCIONES PARA DESCARGAR LOGS

## Opción 1: Railway CLI (Recomendado)

1. Abre PowerShell o CMD
2. Navega a la carpeta:
   ```
   cd C:\Users\PC 1\AgenteVentas
   ```

3. Autentícate en Railway (abrirá navegador):
   ```
   railway login
   ```

4. Una vez autenticado, descarga logs:
   ```
   railway logs --lines 30000 > logs_railway_completo.txt
   ```

5. Extrae casos BRUCE:
   ```
   python extractor_bruce.py
   ```

## Opción 2: Desde Dashboard Railway (Manual)

1. Abre: https://railway.com/project/26c3f3e6-17c5-4497-baab-9fb83f5d9e4c

2. Click en "Deployments" → deployment d0f1e74d

3. Para cada caso (BRUCE1288, 1289, 1290, 1291):
   - Filtra por el ID
   - Click en "Download logs" o "Export"
   - Si no hay opción de descarga:
     * Usa F12 (DevTools) → Network
     * Recarga los logs
     * Busca la petición a /logs o similar
     * Copy as cURL → ejecútalo en terminal
     * Guarda output en logs_bruce[ID].txt

## Opción 3: Pedir a Claude token con permisos

Si nada funciona, puedes generar un nuevo token en Railway con permisos de lectura y proporcionármelo.

---

Una vez tengas los archivos logs_bruce1288.txt - logs_bruce1291.txt, 
avísame y procederé con el análisis.
