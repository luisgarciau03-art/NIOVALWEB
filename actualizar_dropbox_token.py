"""
Actualiza el DROPBOX_TOKEN en Railway via CLI.
Requiere: railway CLI instalado y logueado (railway login).
Ejecutar desde la carpeta del proyecto NIOVALWEB.
"""
import subprocess
import sys

def actualizar_token_railway():
    nuevo_token = input('Introduce el nuevo token de Dropbox: ').strip()
    if not nuevo_token:
        print('Token vacio. Cancelando.')
        return

    # Actualizar variable en Railway via CLI
    try:
        result = subprocess.run(
            ['railway', 'variables', 'set', f'DROPBOX_TOKEN={nuevo_token}'],
            capture_output=True, text=True, cwd=r'C:\Users\PC 1\NIOVALWEB'
        )
        if result.returncode == 0:
            print('DROPBOX_TOKEN actualizado en Railway correctamente.')
            print('El cambio se aplica automaticamente sin redeploy.')
        else:
            print(f'Error actualizando en Railway: {result.stderr}')
            print('\nSi no tienes Railway CLI, actualiza manualmente:')
            print('1. Ve a railway.app > tu proyecto NIOVALWEB > Variables')
            print('2. Edita DROPBOX_TOKEN con el nuevo valor')
            print(f'\nNuevo token: {nuevo_token}')
    except FileNotFoundError:
        print('Railway CLI no encontrado. Instalalo con: npm install -g @railway/cli')
        print('Luego ejecuta: railway login')
        print(f'\nMientras tanto, actualiza manualmente en railway.app:')
        print(f'Variable: DROPBOX_TOKEN')
        print(f'Valor: {nuevo_token}')

if __name__ == '__main__':
    actualizar_token_railway()
