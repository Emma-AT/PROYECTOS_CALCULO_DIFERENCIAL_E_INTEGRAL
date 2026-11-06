"""Módulo de evaluación técnica y económica de escenarios de repotenciación.

Contiene funciones para la extrapolación vertical del recurso eólico según
la ley potencial de Hellmann, el cálculo de producción neta anual de energía (AEP)
considerando pérdidas globales del parque, y la evaluación de rentabilidad
mediante el Valor Presente Neto (VPN / NPV).
"""

import numpy as np


def escalar_viento_altura(
    v_ref: np.ndarray | float,
    h_ref: float,
    h_nueva: float,
    alpha: float = 0.14,
) -> np.ndarray | float:
    """Escala la velocidad del viento a una cota superior usando la ley de Hellmann.

    Fórmula matemática a programar:
        v(h_nueva) = v_ref * (h_nueva / h_ref)**alpha

    Donde:
        - v_ref: Velocidad medida a la altura del mástil o anemómetro de
          referencia [m/s].
        - h_ref: Altura del sensor de referencia sobre el terreno en metros [m]
          (ej. 40 m).
        - h_nueva: Altura del buje de la nueva turbina en metros [m]
          (ej. 60 m, 70 m u 80 m).
        - alpha: Exponente de fricción / cizalladura vertical del viento
          (adimensional, típicamente 0.10 a 0.25 según rugosidad del terreno).

    Unidades físicas:
        - v_ref y salida: Metros por segundo [m/s].
        - h_ref y h_nueva: Metros [m].
        - alpha: Adimensional.

    Args:
        v_ref (np.ndarray | float): Velocidad del viento o vector de mediciones
            a la cota de referencia [m/s].
        h_ref (float): Altura de la medición de referencia [m].
        h_nueva (float): Altura objetivo del buje de la turbina [m].
        alpha (float, optional): Coeficiente de cizalladura vertical.
            Por defecto 0.14.

    Returns:
        np.ndarray | float: Velocidad o vector de velocidades proyectadas a
            la nueva altura del buje [m/s].

    Raises:
        ValueError: Si alguna altura es menor o igual a cero, o si alpha es negativo.
        NotImplementedError: Pendiente de implementación por el estudiante.
    """
    raise NotImplementedError("Pendiente de implementación")


def energia_anual(
    potencia_media_kw: float,
    n_turbinas: int,
    perdidas_l: float = 0.15,
) -> float:
    """Calcula la producción anual neta de energía (AEP - Annual Energy Production).

    Fórmula matemática a programar:
        Horas anuales: H_anuales = 8760 horas (año estándar)
        Generación bruta anual: E_bruta = potencia_media_kw * 8760 * n_turbinas
        Generación neta anual: E_neta = E_bruta * (1.0 - perdidas_l)

    Donde:
        - perdidas_l: Factor fraccional global de pérdidas del parque eólico
          (estela, disponibilidad eléctrica, ensuciamiento de palas, etc.).
          Ejemplo: perdidas_l = 0.15 representa un 15% de pérdidas totales.

    Unidades físicas:
        - potencia_media_kw: Potencia media unitaria en kilovatios [kW].
        - n_turbinas: Número de máquinas instaladas en el parque.
        - perdidas_l: Factor adimensional en el rango [0.0, 1.0).
        - Retorno: Energía neta anual en kilovatios-hora por año [kWh/año].

    Args:
        potencia_media_kw (float): Potencia eléctrica media de una turbina [kW].
        n_turbinas (int): Cantidad de turbinas de la misma clase en el parque.
        perdidas_l (float, optional): Factor fraccional de pérdidas totales.
            Por defecto 0.15 (15%).

    Returns:
        float: Producción neta anual estimada del parque eólico en [kWh/año].

    Raises:
        ValueError: Si la potencia o número de turbinas es negativo, o perdidas_l
            no está en el rango [0, 1).
        NotImplementedError: Pendiente de implementación por el estudiante.
    """
    raise NotImplementedError("Pendiente de implementación")


def vpn(
    inversion: float,
    delta_energia_kwh: float,
    precio_kwh: float,
    delta_mantenimiento: float,
    tasa_descuento: float,
    anios: int = 20,
) -> float:
    """Calcula el Valor Presente Neto (VPN / NPV) incremental del proyecto de repotenciación.

    Fórmula matemática a programar:
        Flujo de caja neto anual constante (CF_t):
            CF_t = (delta_energia_kwh * precio_kwh) - delta_mantenimiento

        Valor Presente Neto:
            VPN = -inversion + sum_{t=1}^{anios} [ CF_t / (1 + tasa_descuento)**t ]

        O alternativamente usando la fórmula cerrada de anualidad vencida:
            Factor_anualidad = [ 1 - (1 + tasa_descuento)**(-anios) ] / tasa_descuento
            VPN = -inversion + CF_t * Factor_anualidad

    Criterio de decisión económica:
        - VPN > 0: El proyecto es financieramente rentable y crea valor.
        - VPN = 0: El proyecto rinde exactamente la tasa de retorno exigida.
        - VPN < 0: El proyecto destruye valor frente a la alternativa de base.

    Unidades físicas y financieras:
        - inversion: Costo de capital inicial (CAPEX) en [USD].
        - delta_energia_kwh: Incremento anual de energía neta generada
          (E_nueva - E_existente) en [kWh/año].
        - precio_kwh: Tarifa de venta de la energía en [USD/kWh].
        - delta_mantenimiento: Variación anual en costos de OPEX en [USD/año].
        - tasa_descuento: Tasa de corte anual en forma decimal (ej. 0.08 para 8%).
        - anios: Periodo de análisis del proyecto en años [años].
        - Retorno: VPN en dólares [USD].

    Args:
        inversion (float): Inversión inicial de capital (CAPEX) en [USD].
        delta_energia_kwh (float): Diferencial de energía anual neta en [kWh/año].
        precio_kwh (float): Precio pactado de venta de energía en [USD/kWh].
        delta_mantenimiento (float): Incremento anual en costos OPEX en [USD/año].
        tasa_descuento (float): Tasa de descuento anual en valor fraccional.
        anios (int, optional): Horizonte temporal de evaluación en años.
            Por defecto 20.

    Returns:
        float: Valor Presente Neto (VPN) del proyecto en [USD].

    Raises:
        ValueError: Si la tasa de descuento es <= -1.0 o los años <= 0.
        NotImplementedError: Pendiente de implementación por el estudiante.
    """
    raise NotImplementedError("Pendiente de implementación")
