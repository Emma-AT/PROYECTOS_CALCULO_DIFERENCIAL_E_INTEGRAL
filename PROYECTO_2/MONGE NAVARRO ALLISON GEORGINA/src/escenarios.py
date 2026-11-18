"""Escenarios, sensibilidad y recomendación.

Un escenario es una forma posible de organizar la campaña:
qué día empieza, cuántos días dura y en qué horario se cuenta.
Para cada escenario calculamos qué fracción de todas las aves de la
temporada lograría registrar, y así podemos compararlos.

Fracción registrada = (fracción del paso que cae en las fechas)
                    x (fracción del día que cae en el turno).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from src import limpieza
from src.datos import Parametros
from src.modelo import (
    acumulada,
    aves_en_ventana,
    fecha_percentil,
    media_movil,
    mejor_turno,
    mejor_ventana,
    perfil_horario,
    total_diario,
    totales_diarios,
    trapecio,
)

ESPECIES = ["Gavilán aludo", "Gavilán de Swainson", "Zopilote cabecirrojo"]


@dataclass(frozen=True)
class Escenario:
    """Resultado de evaluar una campaña.

    nombre: nombre corto del escenario.
    inicio, fin: días de inicio y fin (días desde el primer día).
    fecha_inicio, fecha_fin: las mismas fechas en calendario (fin = último día).
    hora_inicio, hora_fin: horario del turno (h).
    frac_fechas: fracción del paso total que ocurre en las fechas (0 a 1).
    frac_turno: fracción de las aves del día que pasa en el turno (0 a 1).
    frac_registrada: frac_fechas x frac_turno (0 a 1).
    aves_registradas: aves que la campaña podría contar (aves).
    """

    nombre: str
    inicio: float
    fin: float
    fecha_inicio: str
    fecha_fin: str
    hora_inicio: float
    hora_fin: float
    frac_fechas: float
    frac_turno: float
    frac_registrada: float
    aves_registradas: float


def dia_a_fecha(dia: float, fecha0: pd.Timestamp) -> str:
    """Convierte 'días desde el inicio' en una fecha legible (ej. '08/10/2026')."""
    return (fecha0 + pd.Timedelta(days=int(round(dia)))).strftime("%d/%m/%Y")


def hora_texto(hora: float) -> str:
    """Convierte una hora decimal en texto (ej. 6.2 -> '06:12')."""
    minutos = int(round(hora * 60))
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def fraccion_turno(
    limpio: pd.DataFrame, inicio: float, L: int, horas: int, hi: float, hf: float
) -> tuple[float, float]:
    """Mejor turno dentro de los días de la campaña.

    Usa el perfil horario promedio de esos días (todas las especies).
    Salida: (hora de inicio del turno, fracción del día en el turno).
    """
    perfil = perfil_horario(limpio, dias=(inicio, inicio + L))
    total_dia = total_diario(perfil["Total"], hi, hf, inicio_obs=float(perfil["hora"].min()))
    turno = mejor_turno(perfil["Total"], horas, float(perfil["hora"].min()), total_dia)
    return turno.hora_inicio, turno.fraccion


def evaluar_escenario(
    nombre: str,
    totales: pd.DataFrame,
    limpio: pd.DataFrame,
    params: Parametros,
    inicio: float,
    L: int | None = None,
    horas: int | None = None,
    columna: str = "Total",
) -> Escenario:
    """Calcula qué fracción de las aves registra una campaña dada.

    Entradas: nombre, tabla de totales diarios, tabla limpia, parámetros,
        día de inicio, duración L (días) y horas del turno. Si L u horas
        no se dan, se usan los del Excel.
    Salida: un `Escenario`.
    """
    L = params.dias_campana if L is None else L
    horas = params.horas_turno if horas is None else horas
    n, t = totales[columna].to_numpy(), totales["dia"].to_numpy(dtype=float)
    frac_fechas = aves_en_ventana(n, inicio, L, t) / trapecio(n, t)
    hora_ini, frac_turno = fraccion_turno(limpio, inicio, L, horas, params.hi, params.hf)
    fecha0 = pd.Timestamp(totales["fecha"].min())
    frac = frac_fechas * frac_turno
    return Escenario(
        nombre=nombre,
        inicio=inicio,
        fin=inicio + L,
        fecha_inicio=dia_a_fecha(inicio, fecha0),
        fecha_fin=dia_a_fecha(inicio + L - 1, fecha0),
        hora_inicio=hora_ini,
        hora_fin=hora_ini + horas,
        frac_fechas=frac_fechas,
        frac_turno=frac_turno,
        frac_registrada=frac,
        aves_registradas=frac * trapecio(n, t),
    )


def fraccion_por_especie(totales: pd.DataFrame, L: int) -> pd.DataFrame:
    """G(a)/N para cada especie y cada día de inicio posible.

    Salida: tabla con la columna 'inicio' y una columna por especie (0 a 1).
    """
    t = totales["dia"].to_numpy(dtype=float)
    tabla = {}
    for especie in ESPECIES:
        r = mejor_ventana(totales[especie].to_numpy(), L, t)
        tabla["inicio"] = r.inicios
        tabla[especie] = r.G / trapecio(totales[especie].to_numpy(), t)
    return pd.DataFrame(tabla)


def inicio_equilibrado(totales: pd.DataFrame, L: int) -> float:
    """Día de inicio que maximiza la fracción de la especie PEOR registrada.

    Así ninguna especie queda poco registrada, aunque se cuenten algo
    menos de aves en total (el zopilote es mucho más abundante y domina
    el total).
    """
    fr = fraccion_por_especie(totales, L)
    peor = fr[ESPECIES].min(axis=1)
    return float(fr["inicio"].iloc[int(np.argmax(peor))])


def inicio_centrado(totales: pd.DataFrame, L: int) -> float:
    """Regla simple: centrar la campaña en la fecha del 50 % del paso.

    inicio = fecha del 50 % - L/2, redondeado al día más cercano.
    """
    t = totales["dia"].to_numpy(dtype=float)
    F = acumulada(totales["Total"].to_numpy(), t)
    return float(round(fecha_percentil(F, t, 0.5) - L / 2))


def comparar_escenarios(
    totales: pd.DataFrame,
    limpio: pd.DataFrame,
    params: Parametros,
    L: int | None = None,
    horas: int | None = None,
) -> pd.DataFrame:
    """Compara la campaña tradicional con dos alternativas.

    1. Tradicional: empieza el día indicado en el Excel.
    2. Centrada: centrada en la fecha del 50 % del paso (regla simple).
    3. Óptima: la que registra más aves en total (máximo de G(a)).
    4. Equilibrada: la que mejor registra a la especie menos cubierta.
    Cada escenario usa el mejor turno dentro de sus fechas.
    Salida: tabla con un escenario por fila y la fracción por especie.
    """
    L = params.dias_campana if L is None else L
    t = totales["dia"].to_numpy(dtype=float)
    optima = mejor_ventana(totales["Total"].to_numpy(), L, t).inicio
    inicios = {
        "Tradicional": params.inicio_tradicional,
        "Centrada en el 50 %": inicio_centrado(totales, L),
        "Óptima (más aves)": optima,
        "Equilibrada (3 especies)": inicio_equilibrado(totales, L),
    }
    filas = []
    for nombre, inicio in inicios.items():
        esc = evaluar_escenario(nombre, totales, limpio, params, inicio, L, horas)
        fila = asdict(esc)
        for especie in ESPECIES:
            n = totales[especie].to_numpy()
            fila[f"frac_{especie}"] = aves_en_ventana(n, inicio, L, t) / trapecio(n, t)
        filas.append(fila)
    return pd.DataFrame(filas)


def sensibilidad_duracion(
    totales: pd.DataFrame, params: Parametros, valores: list[int]
) -> pd.DataFrame:
    """¿Cómo cambia la mejor campaña si dura más o menos días?

    Salida: por cada L, el mejor inicio, la fracción del paso en esas
    fechas y la de la campaña tradicional con la misma duración.
    """
    t = totales["dia"].to_numpy(dtype=float)
    n = totales["Total"].to_numpy()
    N = trapecio(n, t)
    filas = []
    for L in valores:
        r = mejor_ventana(n, L, t)
        trad = params.inicio_tradicional
        frac_trad = aves_en_ventana(n, trad, L, t) / N if trad + L <= t[-1] else np.nan
        filas.append(
            {
                "dias": L,
                "mejor_inicio": r.inicio,
                "frac_optima": r.fraccion,
                "frac_tradicional": frac_trad,
            }
        )
    return pd.DataFrame(filas)


def sensibilidad_turno(
    limpio: pd.DataFrame, params: Parametros, valores: list[int]
) -> pd.DataFrame:
    """¿Cómo cambia el mejor horario si el turno tiene más o menos horas?"""
    perfil = perfil_horario(limpio)
    h0 = float(perfil["hora"].min())
    total_dia = total_diario(perfil["Total"], params.hi, params.hf, inicio_obs=h0)
    filas = []
    for horas in valores:
        r = mejor_turno(perfil["Total"], horas, h0, total_dia)
        filas.append(
            {
                "horas": horas,
                "hora_inicio": r.hora_inicio,
                "hora_fin": r.hora_fin,
                "fraccion": r.fraccion,
            }
        )
    return pd.DataFrame(filas)


def sensibilidad_vuelo(
    limpio: pd.DataFrame, params: Parametros, cambios: list[float]
) -> pd.DataFrame:
    """¿Qué pasa si el vuelo empieza/termina antes o después (hi y hf)?

    Se mueve la duración de las colas en ±cambio horas y se recalculan
    el total de la temporada y la mejor ventana.
    """
    filas = []
    for cambio in cambios:
        hi, hf = params.hi - cambio, params.hf + cambio
        tot = totales_diarios(limpio, hi, hf)
        t = tot["dia"].to_numpy(dtype=float)
        r = mejor_ventana(tot["Total"].to_numpy(), params.dias_campana, t)
        filas.append(
            {
                "cambio_h": cambio,
                "hi": hi,
                "hf": hf,
                "total_aves": trapecio(tot["Total"], t),
                "mejor_inicio": r.inicio,
                "frac_optima": r.fraccion,
            }
        )
    return pd.DataFrame(filas)


def sensibilidad_limpieza(
    conteos: pd.DataFrame, params: Parametros, factores: list[float]
) -> pd.DataFrame:
    """¿Cambia la decisión si el criterio de 'cero de más' es más o menos estricto?"""
    filas = []
    for factor in factores:
        limpio = limpieza.limpiar_conteos(conteos, factor=factor)
        tot = totales_diarios(limpio, params.hi, params.hf)
        t = tot["dia"].to_numpy(dtype=float)
        r = mejor_ventana(tot["Total"].to_numpy(), params.dias_campana, t)
        filas.append(
            {
                "factor": factor,
                "atipicos": int((limpio["correccion"] == "atípico").sum()),
                "total_aves": trapecio(tot["Total"], t),
                "mejor_inicio": r.inicio,
                "frac_optima": r.fraccion,
            }
        )
    return pd.DataFrame(filas)


def comprobar_extremos(
    totales: pd.DataFrame, inicio: float, L: int, ancho: int = 5
) -> dict[str, float]:
    """Comprueba la condición del óptimo G'(a) = n(a + L) - n(a) = 0.

    Con los datos diarios (que tienen "ruido" por la lluvia) se usa la
    serie suavizada con una media móvil de `ancho` días. Se busca el día
    a* donde n(a + L) - n(a) cambia de signo (interpolando) y se compara
    con el inicio óptimo encontrado con G(a).

    Salida: aves/día suavizadas al inicio y al fin de la ventana,
    su diferencia relativa y el día a* donde se cumple la condición.
    """
    t = totales["dia"].to_numpy(dtype=float)
    suave = media_movil(totales["Total"].to_numpy(), ancho)
    k = int(round(L / (t[1] - t[0])))
    d = suave[k:] - suave[:-k]  # G'(a) para cada inicio posible
    cambios = np.where(np.diff(np.sign(d)) < 0)[0]  # de + a -: máximo
    if cambios.size:
        i = int(cambios[np.argmin(np.abs(t[cambios] - inicio))])
        a_cero = float(t[i] + d[i] / (d[i] - d[i + 1]) * (t[i + 1] - t[i]))
    else:
        a_cero = float("nan")
    n_a = float(np.interp(inicio, t, suave))
    n_b = float(np.interp(inicio + L, t, suave))
    return {
        "n_inicio": n_a,
        "n_fin": n_b,
        "diferencia_relativa": abs(n_b - n_a) / max(n_a, n_b),
        "a_donde_G_prima_es_cero": a_cero,
    }


def recomendacion(escenarios: pd.DataFrame) -> str:
    """Texto corto con la recomendación, a partir de la tabla de escenarios."""
    opt = escenarios[escenarios["nombre"].str.startswith("Óptima")].iloc[0]
    trad = escenarios[escenarios["nombre"] == "Tradicional"].iloc[0]
    ganancia = opt["aves_registradas"] - trad["aves_registradas"]
    return (
        f"Hacer la campaña del {opt['fecha_inicio']} al {opt['fecha_fin']}, con turno de "
        f"{hora_texto(opt['hora_inicio'])} a {hora_texto(opt['hora_fin'])}. Registraría el "
        f"{opt['frac_registrada']:.0%} de las aves de la temporada "
        f"(unas {opt['aves_registradas']:,.0f}), "
        f"frente al {trad['frac_registrada']:.0%} de la campaña tradicional: "
        f"{ganancia:,.0f} aves más."
    )
