"""Módulo de ingestión, validación y saneamiento de datos meteorológicos.

Este módulo contiene las rutinas encargadas de cargar el archivo Excel del
proyecto C-01_AGUIRRE de forma relativa, validar la integridad del esquema
de datos, tratar valores atípicos/faltantes en mediciones de viento y calcular
la densidad atmosférica del aire a partir de variables termodinámicas.
"""

from pathlib import Path

import numpy as np
import pandas as pd


def cargar_datos(ruta: str | Path) -> dict[str, pd.DataFrame]:
    """Carga y valida el libro de cálculo Excel de la Planta Eólica Tejona.

    Lee el archivo especificado sin asumir rutas absolutas fijas en el sistema,
    verificando la existencia del archivo, las hojas mínimas necesarias y las
    columnas críticas para el posterior análisis.

    Hojas esperadas en el archivo:
        - Datos meteorológicos ('Metereologia' o 'Datos_Viento')
        - Turbina existente ('Turbina_Existente')
        - Turbina repotenciación ('Turbina_Repotenciacion')
        - Curvas de potencia ('Curvas_Potencia')

    Args:
        ruta (str | Path): Ruta relativa o basada en `Path` hacia el archivo
            Excel (ej. 'datos/P09_C-01_AGUIRRE.xlsx').

    Returns:
        dict[str, pd.DataFrame]: Diccionario donde cada clave corresponde al
            nombre de la hoja y el valor es el DataFrame correspondiente con
            tipos de datos validados.

    Raises:
        FileNotFoundError: Si el archivo no existe en la ruta proporcionada.
        ValueError: Si faltan hojas requeridas o columnas indispensables.
        NotImplementedError: Pendiente de implementación por el estudiante.
    """
    raise NotImplementedError("Pendiente de implementación")


def limpiar_viento(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica filtros de calidad y sanea anomalías en series de viento.

    Procesa el DataFrame meteorológico tratando datos faltantes (NaN) y picos
    anómalos (spikes) generados por fallas del anemómetro o perturbaciones
    eléctricas.

    Criterios de limpieza sugeridos para la programación:
        1. Velocidades negativas: v < 0 m/s -> Asignar NaN o corregir a 0.0 m/s.
        2. Picos no físicos: v > 35.0 m/s -> Filtrar o acotar según umbral.
        3. Tratamiento de faltantes: Interpolar linealmente tramos cortos
           (<= 2 horas consecutivas) o aplicar propagación hacia adelante/atrás.
        4. Saltos abruptos temporales: |v_t - v_{t-1}| > 15 m/s en 1 hora.

    Args:
        df (pd.DataFrame): DataFrame original con mediciones meteorológicas
            que debe incluir al menos la columna de velocidad del viento
            (en m/s) y la estampa temporal.

    Returns:
        pd.DataFrame: Copia limpia del DataFrame original, sin valores nulos
            no justificados, con las banderas de calidad aplicadas y las
            series regularizadas.

    Raises:
        NotImplementedError: Pendiente de implementación por el estudiante.
    """
    raise NotImplementedError("Pendiente de implementación")


def densidad_aire(
    temperatura_c: np.ndarray | pd.Series,
    presion_pa: np.ndarray | pd.Series,
) -> np.ndarray | pd.Series:
    """Calcula la densidad local del aire mediante la ley de gases ideales.

    Fórmula matemática a programar:
        rho = p_a / (R_especifico * T_K)

    Donde:
        - rho: Densidad del aire en [kg/m^3].
        - p_a: Presión atmosférica local en Pascales [Pa].
        - R_especifico: Constante de gas específico para aire seco:
            R_aire = 287.058 J / (kg * K)
        - T_K: Temperatura termodinámica absoluta en Kelvin [K]:
            T_K = T_C + 273.15

    Unidades físicas:
        - Entrada temperatura_c: Grados Celsius [°C].
        - Entrada presion_pa: Pascales [Pa] (si viene en hPa, multiplicar por 100).
        - Salida densidad: Kilogramos por metro cúbico [kg/m^3].
          (Valores típicos en Tejona: 1.10 - 1.25 kg/m^3).

    Args:
        temperatura_c (np.ndarray | pd.Series): Serie o vector con temperatura
            ambiente en grados Celsius [°C].
        presion_pa (np.ndarray | pd.Series): Serie o vector con presión
            atmosférica barométrica en Pascales [Pa].

    Returns:
        np.ndarray | pd.Series: Densidad instantánea calculada del aire
            en [kg/m^3], preservando el tipo y dimensiones de entrada.

    Raises:
        NotImplementedError: Pendiente de implementación por el estudiante.
    """
    raise NotImplementedError("Pendiente de implementación")
