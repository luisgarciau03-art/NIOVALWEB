"""
Adaptador para el TABLERO DE NIOVAL (Excel)
Lee información existente de clientes para que Bruce no pregunte lo que ya sabemos
"""

import pandas as pd
from typing import Dict, Optional, List
import re


class TaberoNiovalAdapter:
    """Adaptador para leer el TABLERO DE NIOVAL y enriquecer contactos"""

    def __init__(self, archivo_excel: str = "TABLERO DE NIOVAL Yahir .xlsx"):
        """
        Inicializa el adaptador

        Args:
            archivo_excel: Ruta al archivo Excel del tablero
        """
        self.archivo_excel = archivo_excel
        self.df = None
        self._cargar_tablero()

    def _cargar_tablero(self):
        """Carga el archivo Excel del tablero"""
        try:
            self.df = pd.read_excel(self.archivo_excel)
            print(f" Tablero NIOVAL cargado: {len(self.df)} registros")
            print(f"   Columnas: {', '.join(self.df.columns.tolist())}")
        except Exception as e:
            print(f" Error al cargar tablero: {e}")
            self.df = None

    def buscar_contacto_por_telefono(self, telefono: str) -> Optional[Dict]:
        """
        Busca un contacto en el tablero por número de teléfono

        Args:
            telefono: Número de teléfono normalizado (+52XXXXXXXXXX)

        Returns:
            Dict con información del contacto o None si no se encuentra
        """
        if self.df is None:
            return None

        # Limpiar teléfono para búsqueda
        tel_limpio = re.sub(r'[^\d]', '', telefono)[-10:]  # Últimos 10 dígitos

        # Buscar en el DataFrame
        # Asumimos que puede haber una columna de teléfono o estar en CONTACTO
        for idx, row in self.df.iterrows():
            # Buscar en columna CONTACTO si tiene números
            contacto_str = str(row.get('CONTACTO', ''))
            if tel_limpio in re.sub(r'[^\d]', '', contacto_str):
                return self._extraer_datos_contacto(row)

        return None

    def buscar_contacto_por_nombre(self, nombre: str) -> Optional[Dict]:
        """
        Busca un contacto en el tablero por nombre del negocio

        Args:
            nombre: Nombre del negocio

        Returns:
            Dict con información del contacto o None si no se encuentra
        """
        if self.df is None or not nombre:
            return None

        nombre_lower = nombre.lower()

        # Buscar coincidencia en columna CONTACTO o Maps
        for idx, row in self.df.iterrows():
            contacto = str(row.get('CONTACTO', '')).lower()
            maps = str(row.get('Maps', '')).lower()

            if nombre_lower in contacto or nombre_lower in maps:
                return self._extraer_datos_contacto(row)

        return None

    def _extraer_datos_contacto(self, row) -> Dict:
        """
        Extrae datos relevantes de una fila del tablero

        Args:
            row: Fila del DataFrame

        Returns:
            Dict con datos del contacto
        """
        datos = {
            # Datos básicos
            'nombre_negocio': self._get_value(row, 'CONTACTO') or self._get_value(row, 'Maps'),
            'domicilio': self._get_value(row, 'Domicilio'),
            'horario': self._get_value(row, 'Horario'),

            # Datos de Google Maps
            'puntuacion_maps': self._get_value(row, 'Puntuacion'),
            'resenas_maps': self._get_value(row, 'Reseñas'),
            'link_maps': self._get_value(row, 'Link'),
            'latitud': self._get_value(row, 'Latitud'),
            'longitud': self._get_value(row, 'Longitud'),

            # Estado del contacto
            'estatus': self._get_value(row, 'Estatus'),
            'respuesta_previa': self._get_value(row, 'RESPUESTA'),
            'porcentaje': self._get_value(row, 'PORCENTAJES'),

            # Metadata
            'fecha_registro': self._get_value(row, 'Fecha'),
            'medida': self._get_value(row, 'Medida'),
            'esquema': self._get_value(row, 'Esquema'),

            # Flags
            'tiene_datos_previos': True,
        }

        return datos

    def _get_value(self, row, column: str):
        """
        Obtiene un valor de la fila, manejando NaN y valores vacíos

        Args:
            row: Fila del DataFrame
            column: Nombre de la columna

        Returns:
            Valor limpio o None
        """
        try:
            value = row.get(column)
            if pd.isna(value) or value == '' or str(value).strip() == '':
                return None
            return str(value).strip()
        except Exception:
            return None  # Columna no existe o valor inválido

    def enriquecer_contacto(self, contacto_base: Dict) -> Dict:
        """
        Enriquece un contacto con datos del tablero

        Args:
            contacto_base: Dict con datos básicos del contacto (telefono, nombre_negocio)

        Returns:
            Dict enriquecido con datos del tablero
        """
        if self.df is None:
            return contacto_base

        # Buscar primero por teléfono
        datos_tablero = None
        if 'telefono' in contacto_base:
            datos_tablero = self.buscar_contacto_por_telefono(contacto_base['telefono'])

        # Si no se encuentra, buscar por nombre
        if not datos_tablero and 'nombre_negocio' in contacto_base:
            datos_tablero = self.buscar_contacto_por_nombre(contacto_base['nombre_negocio'])

        # Merge de datos
        if datos_tablero:
            # Copiar contacto base
            contacto_enriquecido = contacto_base.copy()

            # Agregar datos del tablero (sin sobreescribir los existentes)
            for key, value in datos_tablero.items():
                if value is not None and key not in contacto_enriquecido:
                    contacto_enriquecido[key] = value

            return contacto_enriquecido
        else:
            # No se encontró en tablero
            contacto_base['tiene_datos_previos'] = False
            return contacto_base

    def obtener_estadisticas(self) -> Dict:
        """Obtiene estadísticas del tablero"""
        if self.df is None:
            return {}

        stats = {
            'total_registros': len(self.df),
            'con_domicilio': self.df['Domicilio'].notna().sum() if 'Domicilio' in self.df.columns else 0,
            'con_puntuacion': self.df['Puntuacion'].notna().sum() if 'Puntuacion' in self.df.columns else 0,
            'con_estatus': self.df['Estatus'].notna().sum() if 'Estatus' in self.df.columns else 0,
        }

        return stats


# Testing
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TESTING TABLERO NIOVAL ADAPTER")
    print("=" * 80 + "\n")

    try:
        adapter = TaberoNiovalAdapter()

        if adapter.df is not None:
            print("\n ESTADÍSTICAS:")
            print("-" * 80)
            stats = adapter.obtener_estadisticas()
            for key, value in stats.items():
                print(f"{key:30}: {value}")

            print("\n EJEMPLO DE BÚSQUEDA:")
            print("-" * 80)

            # Buscar primer contacto como ejemplo
            if len(adapter.df) > 0:
                primer_contacto = adapter.df.iloc[0]
                nombre = primer_contacto.get('CONTACTO', 'Ejemplo')
                print(f"Buscando: {nombre}")

                resultado = adapter.buscar_contacto_por_nombre(str(nombre))
                if resultado:
                    print("\n Contacto encontrado:")
                    for key, value in resultado.items():
                        if value:
                            print(f"  {key:25}: {value}")

            print("\n EJEMPLO DE ENRIQUECIMIENTO:")
            print("-" * 80)

            contacto_prueba = {
                'telefono': '+526621012000',
                'nombre_negocio': 'Ferretería La Estrella'
            }

            contacto_enriquecido = adapter.enriquecer_contacto(contacto_prueba)
            print(f"\nContacto original: {contacto_prueba}")
            print(f"\nContacto enriquecido:")
            for key, value in contacto_enriquecido.items():
                if value:
                    print(f"  {key:25}: {value}")

        print("\n" + "=" * 80)

    except Exception as e:
        print(f" Error: {e}")
        import traceback
        traceback.print_exc()
