#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script rápido para cambiar voz sin menú interactivo
Uso: python cambiar_voz_rapido.py [comando] [args]
"""

import sys
from gestor_voces_elevenlabs import (
    crear_respaldo,
    listar_respaldos,
    listar_voces,
    regenerar_cache_con_nueva_voz,
    restaurar_respaldo,
    VOCES_DISPONIBLES
)

def mostrar_ayuda():
    """Muestra ayuda de comandos"""
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                    CAMBIAR VOZ RÁPIDO - BRUCE W                            ║
╚════════════════════════════════════════════════════════════════════════════╝

COMANDOS:

  backup [nombre]              Crear respaldo del cache actual
  listar-voces                 Mostrar voces disponibles
  listar-respaldos             Mostrar respaldos existentes
  cambiar <voz>                Cambiar a nueva voz
  restaurar <nombre>           Restaurar un respaldo

VOCES DISPONIBLES:
  - bruce_masculino            Voz masculina original
  - domi_femenino             Voz femenina recomendada
  - jessica_femenino          Voz femenina profesional
  - matilda_femenino          Voz femenina cálida

EJEMPLOS:

  # Crear respaldo antes de cambiar
  python cambiar_voz_rapido.py backup voz_masculina_original

  # Cambiar a voz femenina Domi
  python cambiar_voz_rapido.py cambiar domi_femenino

  # Ver respaldos disponibles
  python cambiar_voz_rapido.py listar-respaldos

  # Restaurar voz original
  python cambiar_voz_rapido.py restaurar voz_masculina_original

FLUJO RECOMENDADO:
  1. python cambiar_voz_rapido.py backup voz_actual
  2. python cambiar_voz_rapido.py listar-voces
  3. python cambiar_voz_rapido.py cambiar domi_femenino
  4. git add audio_cache/ && git commit -m "Nueva voz" && git push

═══════════════════════════════════════════════════════════════════════════════
""")


def main():
    if len(sys.argv) < 2:
        mostrar_ayuda()
        return

    comando = sys.argv[1].lower()

    # BACKUP
    if comando == "backup":
        nombre = sys.argv[2] if len(sys.argv) > 2 else None
        crear_respaldo(nombre)

    # LISTAR VOCES
    elif comando == "listar-voces":
        listar_voces()

    # LISTAR RESPALDOS
    elif comando == "listar-respaldos":
        listar_respaldos()

    # CAMBIAR VOZ
    elif comando == "cambiar":
        if len(sys.argv) < 3:
            print("❌ Error: Debes especificar la voz")
            print("\nVoces disponibles:")
            for key, voz in VOCES_DISPONIBLES.items():
                print(f"  - {key}: {voz['nombre']}")
            return

        voz_key = sys.argv[2]
        if voz_key not in VOCES_DISPONIBLES:
            print(f"❌ Error: Voz '{voz_key}' no existe")
            print("\nVoces disponibles:")
            for key, voz in VOCES_DISPONIBLES.items():
                print(f"  - {key}: {voz['nombre']}")
            return

        voice_id = VOCES_DISPONIBLES[voz_key]["voice_id"]
        voz_nombre = VOCES_DISPONIBLES[voz_key]["nombre"]

        print(f"\n⚠️  ADVERTENCIA:")
        print(f"   - Regenerará TODO el cache (1,238 audios)")
        print(f"   - Costo: ~86,660 créditos ElevenLabs")
        print(f"   - Nueva voz: {voz_nombre}")
        print(f"   - Se creará respaldo automático antes de cambiar")

        confirmar = input(f"\n¿Confirmas el cambio a '{voz_nombre}'? (si/no): ").strip().lower()

        if confirmar != "si":
            print("❌ Operación cancelada")
            return

        print("\n🔄 Iniciando cambio de voz...")
        regenerar_cache_con_nueva_voz(voice_id, crear_backup=True)

        print("\n" + "="*80)
        print("✅ SIGUIENTE PASO: Hacer commit y push a Railway")
        print("="*80)
        print('\ngit add audio_cache/')
        print('git commit -m "Cambio de voz: ' + voz_nombre + '"')
        print('git push origin main')
        print()

    # RESTAURAR
    elif comando == "restaurar":
        if len(sys.argv) < 3:
            print("❌ Error: Debes especificar el nombre del respaldo")
            print("\nUsa: python cambiar_voz_rapido.py listar-respaldos")
            return

        nombre = sys.argv[2]
        print(f"\n⚠️  ADVERTENCIA: Esto reemplazará el cache actual")

        confirmar = input(f"\n¿Confirmas restaurar '{nombre}'? (si/no): ").strip().lower()

        if confirmar != "si":
            print("❌ Operación cancelada")
            return

        restaurar_respaldo(nombre)

        print("\n" + "="*80)
        print("✅ SIGUIENTE PASO: Verificar cambios y hacer commit")
        print("="*80)
        print('\ngit status')
        print('git diff audio_cache/cache_audios.json')
        print('git add audio_cache/')
        print('git commit -m "Restaurar voz: ' + nombre + '"')
        print('git push origin main')
        print()

    else:
        print(f"❌ Comando desconocido: {comando}")
        mostrar_ayuda()


if __name__ == "__main__":
    main()
