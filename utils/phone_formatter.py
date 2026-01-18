"""
Utilidades para normalización y formateo de números telefónicos mexicanos
"""

import re
from typing import Optional


def normalizar_numero(numero: str) -> Optional[str]:
    """
    Normaliza diferentes formatos de números mexicanos al formato estándar.

    Ejemplos de entrada:
    - "662 101 2000" -> "+526621012000"
    - "323 112 7516" -> "+523231127516"
    - "81 1481 9779" -> "+528114819779"
    - "662-101-2000" -> "+526621012000"
    - "6621012000" -> "+526621012000"

    Args:
        numero: Número de teléfono en cualquier formato

    Returns:
        Número en formato +52XXXXXXXXXX o None si es inválido
    """
    if not numero:
        return None

    # Limpiar el número: eliminar espacios, guiones, paréntesis
    numero_limpio = re.sub(r'[^\d+]', '', str(numero))

    # Si ya tiene +52, verificar longitud
    if numero_limpio.startswith('+52'):
        numero_limpio = numero_limpio[3:]  # Quitar +52
    elif numero_limpio.startswith('52'):
        numero_limpio = numero_limpio[2:]  # Quitar 52

    # Ahora numero_limpio debe tener 10 dígitos (número mexicano)
    if len(numero_limpio) == 10 and numero_limpio.isdigit():
        return f"+52{numero_limpio}"

    # Si tiene 11 dígitos y empieza con 1 (formato internacional alternativo)
    elif len(numero_limpio) == 11 and numero_limpio.startswith('1'):
        return f"+52{numero_limpio[1:]}"

    else:
        return None


def formatear_numero_legible(numero: str) -> str:
    """
    Formatea un número normalizado a formato legible: 662 101 2000

    Args:
        numero: Número en formato +52XXXXXXXXXX o 10 dígitos

    Returns:
        Número formateado: XXX XXX XXXX
    """
    # Extraer solo los 10 dígitos
    if numero.startswith('+52'):
        numero_limpio = numero[3:]
    elif numero.startswith('52'):
        numero_limpio = numero[2:]
    else:
        numero_limpio = numero

    # Limpiar caracteres no numéricos
    numero_limpio = re.sub(r'[^\d]', '', numero_limpio)

    # Formatear: 662 108 5297 (3 dígitos, espacio, 3 dígitos, espacio, 4 dígitos)
    if len(numero_limpio) == 10:
        return f"{numero_limpio[:3]} {numero_limpio[3:6]} {numero_limpio[6:]}"

    # Si no tiene 10 dígitos, retornar tal cual
    return numero_limpio


def validar_numero_mexicano(numero: str) -> bool:
    """
    Valida si un número es un número mexicano válido.

    Args:
        numero: Número a validar

    Returns:
        True si es válido, False si no
    """
    normalizado = normalizar_numero(numero)
    return normalizado is not None


def extraer_lada(numero: str) -> Optional[str]:
    """
    Extrae la lada (código de área) de un número mexicano.

    Args:
        numero: Número de teléfono

    Returns:
        Lada de 2 o 3 dígitos, o None si no es válido
    """
    normalizado = normalizar_numero(numero)
    if not normalizado:
        return None

    # Quitar +52
    digitos = normalizado[3:]

    # En México, las ladas pueden ser de 2 o 3 dígitos
    # Ciudades principales tienen lada de 2: 55 (CDMX), 33 (GDL), 81 (MTY)
    ladas_dos_digitos = ['55', '33', '81']

    if digitos[:2] in ladas_dos_digitos:
        return digitos[:2]

    # El resto tiene lada de 3 dígitos
    return digitos[:3]
