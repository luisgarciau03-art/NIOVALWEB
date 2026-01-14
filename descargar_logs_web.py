# -*- coding: utf-8 -*-
"""
Script para descargar logs de Railway usando la interfaz web
No requiere Railway CLI - usa requests directo
"""
import os
import sys
from datetime import datetime

def descargar_logs_manual():
    """
    Guía para descargar logs manualmente desde Railway web
    """
    print("\n" + "="*70)
    print("📥 DESCARGA MANUAL DE LOGS - RAILWAY WEB")
    print("="*70 + "\n")

    print("Como no tienes Railway CLI instalado, sigue estos pasos:\n")

    print("📋 PASOS PARA DESCARGAR LOGS:\n")

    print("1. Abre tu navegador y ve a:")
    print("   https://railway.app/dashboard\n")

    print("2. Selecciona tu proyecto: 'nioval-webhook-server'\n")

    print("3. Haz clic en 'Logs' en el menú lateral\n")

    print("4. Ajusta el rango de logs:")
    print("   - Selecciona 'Last 1000 lines' o 'Last hour'")
    print("   - O usa el selector de fechas\n")

    print("5. Copia TODOS los logs:")
    print("   - Windows: Ctrl+A (seleccionar todo) → Ctrl+C (copiar)")
    print("   - Mac: Cmd+A → Cmd+C\n")

    print("6. Guarda los logs en un archivo:")
    carpeta_logs = "C:\\Users\\PC 1\\AgenteVentas\\LOGS"
    os.makedirs(carpeta_logs, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_sugerido = os.path.join(carpeta_logs, f"logs_railway_{timestamp}.txt")

    print(f"   Ruta sugerida: {archivo_sugerido}\n")

    print("7. Una vez guardado, analízalo con:")
    print(f"   python analizar_logs_railway.py \"{archivo_sugerido}\"\n")

    print("="*70)
    print("💡 ALTERNATIVA: Instalar Railway CLI (Recomendado)")
    print("="*70 + "\n")

    print("Si quieres automatizar esto en el futuro:\n")

    print("1. Instalar Node.js (si no lo tienes):")
    print("   https://nodejs.org/\n")

    print("2. Instalar Railway CLI:")
    print("   npm i -g @railway/cli\n")

    print("3. Login:")
    print("   railway login\n")

    print("4. Vincular proyecto:")
    print("   cd C:\\Users\\PC 1\\AgenteVentas")
    print("   railway link\n")

    print("5. ¡Listo! Ahora podrás usar:")
    print("   python analizar_logs_railway.py\n")

    print("="*70 + "\n")

    # Esperar a que el usuario descargue los logs
    print("¿Ya descargaste los logs desde Railway web?")
    respuesta = input("Ingresa la ruta del archivo (o presiona Enter para salir): ").strip()

    if respuesta and os.path.exists(respuesta):
        print(f"\n✅ Archivo encontrado: {respuesta}")
        print(f"Analizando...\n")

        # Ejecutar análisis
        os.system(f'python analizar_logs_railway.py "{respuesta}"')
    elif respuesta:
        print(f"\n❌ Archivo no encontrado: {respuesta}")
        print("Verifica la ruta y vuelve a intentar\n")
    else:
        print("\n👋 Saliendo...\n")

def crear_script_descarga_rapida():
    """
    Crea un script .bat para facilitar la descarga manual
    """
    carpeta_logs = "C:\\Users\\PC 1\\AgenteVentas\\LOGS"
    os.makedirs(carpeta_logs, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_destino = os.path.join(carpeta_logs, f"logs_railway_{timestamp}.txt")

    bat_content = f"""@echo off
echo ===============================================
echo   GUARDAR LOGS DE RAILWAY
echo ===============================================
echo.
echo 1. Ve a: https://railway.app/dashboard
echo 2. Abre tu proyecto: nioval-webhook-server
echo 3. Click en "Logs"
echo 4. Selecciona rango de logs
echo 5. Copia todo (Ctrl+A, Ctrl+C)
echo 6. Vuelve aqui y presiona cualquier tecla
echo.
pause

echo.
echo Abriendo Notepad para pegar los logs...
echo.
echo IMPORTANTE:
echo 1. Pega los logs en Notepad (Ctrl+V)
echo 2. Guarda como: {archivo_destino}
echo 3. Cierra Notepad
echo.

notepad "{archivo_destino}"

if exist "{archivo_destino}" (
    echo.
    echo ===============================================
    echo   LOGS GUARDADOS CORRECTAMENTE
    echo ===============================================
    echo.
    echo Analizando logs...
    echo.
    python analizar_logs_railway.py "{archivo_destino}"
) else (
    echo.
    echo ===============================================
    echo   NO SE GUARDARON LOS LOGS
    echo ===============================================
    echo.
    echo Vuelve a ejecutar este script y guarda el archivo.
)

echo.
pause
"""

    bat_file = "C:\\Users\\PC 1\\AgenteVentas\\descargar_logs_manual.bat"
    with open(bat_file, 'w', encoding='utf-8') as f:
        f.write(bat_content)

    print(f"✅ Creado script de ayuda: {bat_file}")
    print(f"   Doble clic en ese archivo para guía paso a paso\n")

def main():
    print("\n" + "="*70)
    print("🌐 DESCARGADOR DE LOGS - RAILWAY WEB")
    print("   (Sin necesidad de Railway CLI)")
    print("="*70)

    # Crear script de ayuda
    crear_script_descarga_rapida()

    # Mostrar guía
    descargar_logs_manual()

if __name__ == "__main__":
    main()
