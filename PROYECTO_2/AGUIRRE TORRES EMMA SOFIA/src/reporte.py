"""Módulo de generación de reportes, tablas ejecutivas y visualizaciones gráficas.

Exporta figuras estadísticas (curvas de potencia, distribución de viento vs Weibull,
perfiles de generación horaria) y tablas comparativas de indicadores técnicos
y financieros a la carpeta `resultados/`.

Diseñado para ejecutarse como script CLI mediante:
    python -m src.reporte
"""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def graficar_curvas_potencia(
    curva_existente: pd.DataFrame,
    curva_nueva: pd.DataFrame,
    ruta_salida: str | Path,
) -> None:
    """Genera y guarda el gráfico comparativo de las curvas de potencia.

    Compara la turbina existente frente a la propuesta de repotenciación,
    marcando las velocidades características (v_in, v_rated, v_out) y la
    cota superior del límite teórico de Betz.

    Args:
        curva_existente (pd.DataFrame): Datos de potencia de la turbina base.
        curva_nueva (pd.DataFrame): Datos de potencia de la turbina repotenciada.
        ruta_salida (str | Path): Ruta de archivo donde se exportará la figura
            (ej. 'resultados/figura_curvas_potencia.png').

    Raises:
        NotImplementedError: Pendiente de implementación por el estudiante.
    """
    raise NotImplementedError("Pendiente de implementación")


def graficar_distribucion_viento(
    v_datos: np.ndarray,
    k: float,
    c: float,
    ruta_salida: str | Path,
) -> None:
    """Grafica el histograma empírico de velocidades de viento vs la FDP de Weibull.

    Permite validar visualmente la bondad de ajuste del método de los momentos
    frente al comportamiento real del recurso eólico en Tejona.

    Args:
        v_datos (np.ndarray): Mediciones históricas de velocidad de viento [m/s].
        k (float): Parámetro de forma estimado de Weibull.
        c (float): Parámetro de escala estimado de Weibull en [m/s].
        ruta_salida (str | Path): Destino de exportación del gráfico
            (ej. 'resultados/histograma_weibull.png').

    Raises:
        NotImplementedError: Pendiente de implementación por el estudiante.
    """
    raise NotImplementedError("Pendiente de implementación")


def generar_tabla_resumen(
    metricas: dict[str, Any],
    ruta_salida: str | Path,
) -> pd.DataFrame:
    """Construye y exporta la tabla ejecutiva de indicadores técnicos y económicos.

    Compila la comparación entre la situación actual y la situación repotenciada:
        - Capacidad instalada total [MW]
        - Producción anual neta estimada [GWh/año]
        - Factor de planta promedio [%]
        - Inversión inicial estimada CAPEX [USD]
        - Valor Presente Neto incremental [USD]

    Args:
        metricas (dict[str, Any]): Diccionario con los resultados calculados.
        ruta_salida (str | Path): Destino del archivo (ej. 'resultados/resumen_ejecutivo.csv').

    Returns:
        pd.DataFrame: DataFrame con la tabla formateada.

    Raises:
        NotImplementedError: Pendiente de implementación por el estudiante.
    """
    raise NotImplementedError("Pendiente de implementación")


def ejecutar_reporte_completo(
    ruta_excel: str | Path = Path("datos/P09_C-01_AGUIRRE.xlsx"),
    dir_salida: str | Path = Path("resultados"),
) -> None:
    """Orquesta la carga, cálculo de modelos y exportación de todos los entregables.

    Coordina el flujo completo:
        1. Carga de datos con `src.limpieza.cargar_datos`.
        2. Limpieza de series con `src.limpieza.limpiar_viento`.
        3. Cálculo de densidad con `src.limpieza.densidad_aire`.
        4. Ajuste estadístico de Weibull y curvas de potencia con `src.modelo`.
        5. Extrapolación vertical y análisis de escenarios con `src.escenarios`.
        6. Exportación de gráficos y tablas a `dir_salida`.

    Args:
        ruta_excel (str | Path, optional): Ubicación del archivo de datos fuente.
            Por defecto Path("datos/P09_C-01_AGUIRRE.xlsx").
        dir_salida (str | Path, optional): Directorio donde se guardarán los
            resultados. Por defecto Path("resultados").

    Raises:
        NotImplementedError: Pendiente de implementación por el estudiante.
    """
    raise NotImplementedError("Pendiente de implementación")


if __name__ == "__main__":
    # Punto de entrada CLI para ejecución con: python -m src.reporte
    print("Iniciando generación de reportes del proyecto C-01_AGUIRRE...")
    ejecutar_reporte_completo()
