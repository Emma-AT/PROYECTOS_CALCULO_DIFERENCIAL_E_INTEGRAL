"""Grupos de eliminación, planes de consumo, escenarios y recomendación.

Principio de superposición: el modelo es lineal en la dosis, por lo que la
concentración de un plan con tomas (t_j, D_j) es

    C_plan(t) = Σ_j C(t − t_j; D_j)

Las horas con efecto son la integral de la función indicadora
H_ef = ∫_inicio^fin 1[C_plan(t) >= c_ef] dt.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.config import (
    DIAS_SEMANA_EXAMENES,
    GRUPOS,
    PASO_MALLA_H,
    SEMILLA,
    VARIACION_SENSIBILIDAD,
)
from src.limpieza import Parametros, a_horas_decimales
from src.modelo import (
    ModeloUnCompartimento,
    RelacionAtencion,
    biseccion,
    horas_efecto,
    horas_efecto_biseccion,
    horas_efecto_filas,
    modelo_de,
    trapecio,
)

# ---------------------------------------------------------------------------
# Utilidad de formato
# ---------------------------------------------------------------------------


def hora_texto(h: float) -> str:
    """Hora decimal a 'hh:mm' (12.5 -> '12:30'); NaN -> 'no recomendable'."""
    if np.isnan(h):
        return "no recomendable"
    minutos = int(round(h * 60))
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


# ---------------------------------------------------------------------------
# Clasificación de voluntarios
# ---------------------------------------------------------------------------


def clasificar(resultados: pd.DataFrame, voluntarios: pd.DataFrame) -> pd.DataFrame:
    """Agrupa a los voluntarios en eliminación rápida, normal y lenta.

    Usa terciles de la vida media: el tercio con menor t½ es "rápida".
    Entradas: resultados por voluntario (con vida_media_h) y hoja Voluntarios.
    Salidas: resultados unidos a las características con columna ``grupo``.
    """
    unido = resultados.join(voluntarios.set_index("voluntario"))
    unido["grupo"] = pd.qcut(unido["vida_media_h"], 3, labels=list(GRUPOS))
    return unido


def prueba_permutaciones(
    a: np.ndarray, b: np.ndarray, n: int = 5000, semilla: int = SEMILLA
) -> float:
    """Valor p bilateral de la diferencia de medianas por permutaciones.

    Entradas: dos muestras; número de permutaciones; semilla.
    Salidas: proporción de permutaciones con diferencia al menos tan extrema.
    """
    rng = np.random.default_rng(semilla)
    observada = abs(np.median(a) - np.median(b))
    todos = np.concatenate([a, b])
    perm = np.array([rng.permutation(todos) for _ in range(n)])
    dif = np.abs(np.median(perm[:, : a.size], axis=1) - np.median(perm[:, a.size :], axis=1))
    return float((np.sum(dif >= observada) + 1) / (n + 1))


def comparar_factores(clasificados: pd.DataFrame) -> pd.DataFrame:
    """Compara la vida media según tabaquismo y anticonceptivo hormonal.

    Entradas: tabla de ``clasificar``.
    Salidas: DataFrame con n, mediana y media de t½ (h) por categoría y
    valor p de permutaciones Sí contra No.
    """
    filas = []
    for factor in ["fuma", "anticonceptivo_hormonal"]:
        si = clasificados.loc[clasificados[factor] == "Sí", "vida_media_h"].to_numpy()
        no = clasificados.loc[clasificados[factor] == "No", "vida_media_h"].to_numpy()
        p = prueba_permutaciones(si, no)
        for etiqueta, muestra in [("Sí", si), ("No", no)]:
            filas.append(
                {
                    "factor": factor,
                    "categoria": etiqueta,
                    "n": muestra.size,
                    "mediana_t12_h": np.median(muestra),
                    "media_t12_h": muestra.mean(),
                    "p_valor": p,
                }
            )
    return pd.DataFrame(filas)


def modelos_por_grupo(clasificados: pd.DataFrame, ka: float) -> dict[str, ModeloUnCompartimento]:
    """Persona representativa de cada grupo: mediana de k y de V.

    Entradas: tabla de ``clasificar``; ka (1/h) de la hoja Parametros.
    Salidas: diccionario grupo -> modelo.
    """
    medianas = clasificados.groupby("grupo", observed=True)[["k_1_h", "v_l"]].median()
    return {g: modelo_de(medianas.loc[g], ka) for g in GRUPOS}


def modelos_individuales(
    clasificados: pd.DataFrame, ka: float
) -> dict[str, list[ModeloUnCompartimento]]:
    """Modelos de todos los voluntarios de cada grupo (para % de cumplimiento)."""
    return {
        g: [modelo_de(f, ka) for _, f in clasificados[clasificados["grupo"] == g].iterrows()]
        for g in GRUPOS
    }


# ---------------------------------------------------------------------------
# Planes de consumo y superposición
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlanConsumo:
    """Plan diario de tomas de cafeína.

    Atributos: nombre, horas del día de cada toma (h), dosis de cada toma
    (mg) y nombre de cada bebida.
    """

    nombre: str
    horas: tuple[float, ...]
    dosis_mg: tuple[float, ...]
    bebidas: tuple[str, ...] = field(default=())

    @property
    def total_mg(self) -> float:
        """Cafeína diaria total (mg)."""
        return float(sum(self.dosis_mg))

    @property
    def ultima_toma(self) -> float:
        """Hora de la última toma (h del día)."""
        return max(self.horas)

    def descripcion(self) -> str:
        """Texto legible: '08:00 Café chorreado + 13:00 Café chorreado'."""
        partes = [
            f"{int(h):02d}:{round(60 * (h % 1)):02d} {b}"
            for h, b in zip(self.horas, self.bebidas, strict=True)
        ]
        return " + ".join(partes)


def construir_planes(planes: pd.DataFrame, bebidas: pd.DataFrame) -> dict[str, PlanConsumo]:
    """Crea los planes de la hoja ``Planes`` con la cafeína de ``Bebidas``.

    Entradas: hojas Planes y Bebidas.
    Salidas: diccionario código de plan -> ``PlanConsumo``.
    Lanza ``ValueError`` si un plan usa una bebida que no está en la tabla.
    """
    cafeina = bebidas.set_index("bebida")["cafeina_mg"]
    desconocidas = set(planes["bebida"]) - set(cafeina.index)
    if desconocidas:
        raise ValueError(f"Bebidas sin contenido de cafeína: {', '.join(sorted(desconocidas))}")
    resultado = {}
    for codigo, g in planes.groupby("plan", sort=True):
        horas = tuple(a_horas_decimales(h) for h in g["hora_toma"])
        resultado[str(codigo)] = PlanConsumo(
            nombre=str(codigo),
            horas=horas,
            dosis_mg=tuple(float(cafeina[b]) for b in g["bebida"]),
            bebidas=tuple(g["bebida"]),
        )
    return resultado


def malla_dia(param: Parametros, paso: float = PASO_MALLA_H) -> np.ndarray:
    """Malla temporal (h del día) desde 0 h hasta 8 h después de acostarse."""
    return np.arange(0.0, param.hora_dormir + 8 + paso / 2, paso)


def concentracion_plan(
    plan: PlanConsumo,
    parametros: ModeloUnCompartimento,
    t: np.ndarray,
    dias_previos: int = 0,
) -> np.ndarray:
    """C_plan(t) por superposición vectorizada (mg/L).

    Entradas: plan; modelo de la persona; malla t (h del día); número de
    días previos en que se repitió el mismo plan (acumulación).
    Salidas: arreglo de concentraciones del tamaño de t.
    """
    # 1) Repetir las tomas de los días previos corridas −24 h, −48 h, ...
    desfases = 24.0 * np.arange(dias_previos + 1)
    horas = (np.asarray(plan.horas)[None, :] - desfases[:, None]).ravel()
    dosis = np.tile(np.asarray(plan.dosis_mg), dias_previos + 1)
    # 2) Curva de 1 mg por cada toma (columna) y suma ponderada por la dosis: Σ D_j C(t − t_j)
    unitaria = parametros.concentracion(np.asarray(t)[:, None] - horas[None, :], 1.0)
    return unitaria @ dosis


# ---------------------------------------------------------------------------
# Evaluación y recomendación
# ---------------------------------------------------------------------------


def evaluar_plan(
    plan: PlanConsumo,
    modelo: ModeloUnCompartimento,
    param: Parametros,
    relacion: RelacionAtencion | None = None,
    dias_previos: int = 0,
) -> dict[str, float]:
    """Indicadores de un plan para una persona.

    Salidas: horas_efecto (h), c_dormir (mg/L), c_media_jornada (mg/L),
    mejora_rt_ms (ms, si se da ``relacion``) y cafeína total (mg).
    """
    t = malla_dia(param)
    c = concentracion_plan(plan, modelo, t, dias_previos)
    # Valor medio de C en la jornada: (1/(b − a)) ∫_a^b C dt
    en_jornada = (t >= param.inicio) & (t <= param.fin)
    c_media = trapecio(t[en_jornada], c[en_jornada]) / (param.fin - param.inicio)
    return {
        "horas_efecto": horas_efecto(t, c, param.c_efecto, param.inicio, param.fin),
        "c_dormir": float(np.interp(param.hora_dormir, t, c)),
        "c_media_jornada": c_media,
        "mejora_rt_ms": relacion.pendiente * c_media if relacion else np.nan,
        "cafeina_mg": plan.total_mg,
    }


def evaluar_planes(
    planes: dict[str, PlanConsumo],
    modelos: dict[str, ModeloUnCompartimento],
    param: Parametros,
    relacion: RelacionAtencion | None = None,
    dias_previos: int = 0,
    individuos: dict[str, list[ModeloUnCompartimento]] | None = None,
) -> pd.DataFrame:
    """Tabla de planes por grupo con su cumplimiento.

    Entradas: planes; modelo representativo por grupo; parámetros; relación
    de atención; días previos de consumo; modelos individuales (opcional)
    para calcular el % de personas del grupo que cumplen el umbral de sueño.
    Salidas: DataFrame (grupo, plan, ..., cumple_sueno, cumple_maximo, cumple).
    """
    filas = []
    for grupo, modelo in modelos.items():
        for codigo, plan in planes.items():
            fila = {"grupo": grupo, "plan": codigo, "descripcion": plan.descripcion()}
            fila["n_tomas"] = len(plan.horas)
            fila.update(evaluar_plan(plan, modelo, param, relacion, dias_previos))
            # Repetir con cada voluntario del grupo: qué % queda bajo el umbral de sueño
            if individuos:
                ok = [
                    evaluar_plan(plan, m, param, None, dias_previos)["c_dormir"] < param.c_sueno
                    for m in individuos[grupo]
                ]
                fila["pct_personas_duermen_bien"] = 100 * float(np.mean(ok))
            filas.append(fila)
    tabla = pd.DataFrame(filas)
    # Criterio de éxito: dormir con C < c_sueno y no pasar el máximo diario
    tabla["cumple_sueno"] = tabla["c_dormir"] < param.c_sueno
    tabla["cumple_maximo"] = tabla["cafeina_mg"] <= param.max_diario_mg
    tabla["cumple"] = tabla["cumple_sueno"] & tabla["cumple_maximo"]
    return tabla


def recomendar(tabla: pd.DataFrame, cobertura_minima: float | None = None) -> pd.DataFrame:
    """Elige por grupo el plan factible con más horas de efecto.

    Empates (diferencia < 0,01 h) se rompen con la menor cafeína diaria.
    Entradas: tabla de ``evaluar_planes`` (puede tener columna ``escenario``);
    ``cobertura_minima`` opcional (%): exige además que ese porcentaje de
    personas del grupo quede bajo el umbral de sueño (criterio prudente).
    Salidas: una fila por grupo (y escenario) con el plan recomendado.
    """
    # 1) Quedarse solo con los planes que cumplen (y, si se pide, con la cobertura mínima)
    claves = ["escenario", "grupo"] if "escenario" in tabla.columns else ["grupo"]
    factible = tabla["cumple"]
    if cobertura_minima is not None:
        factible &= tabla["pct_personas_duermen_bien"] >= cobertura_minima
    factibles = tabla[factible].assign(h_red=lambda d: d["horas_efecto"].round(2))
    # 2) Ordenar por más horas con efecto y, si empatan, menos cafeína; tomar el primero
    ordenada = factibles.sort_values(
        claves + ["h_red", "cafeina_mg"], ascending=[True] * len(claves) + [False, True]
    )
    elegida = ordenada.groupby(claves, observed=True, sort=False).head(1).drop(columns="h_red")
    orden = {g: i for i, g in enumerate(GRUPOS)}
    return elegida.sort_values(claves, key=lambda s: s.map(orden) if s.name == "grupo" else s)


# ---------------------------------------------------------------------------
# Hora límite y máximo diario
# ---------------------------------------------------------------------------


def hora_limite(
    modelo: ModeloUnCompartimento,
    dosis_mg: float,
    param: Parametros,
    previo: PlanConsumo | None = None,
    dias_previos: int = 0,
) -> float:
    """Última hora para una toma de ``dosis_mg`` sin superar c_sueno al acostarse.

    Resuelve C_total(hora_dormir; t_toma) = c_sueno con bisección en
    [inicio, hora_dormir − t_max], tramo donde C al acostarse crece con t_toma.
    Entradas: modelo de la persona, dosis (mg), parámetros, tomas previas
    del día (opcional) y días previos de consumo.
    Salidas: hora del día (h); NaN si ni a la hora de inicio es seguro.
    """
    a, b = param.inicio, param.hora_dormir - modelo.tiempo_maximo()
    t = np.array([param.hora_dormir])
    base = concentracion_plan(previo, modelo, t, dias_previos)[0] if previo else 0.0

    # Función cuya raíz buscamos: C al acostarse (con la nueva toma) − umbral de sueño
    def exceso(t_toma: float) -> float:
        nueva = PlanConsumo("x", (t_toma,), (dosis_mg,))
        return base + concentracion_plan(nueva, modelo, t, dias_previos)[0] - param.c_sueno

    if exceso(a) >= 0:
        return float("nan")
    if exceso(b) < 0:
        return b
    return biseccion(exceso, a, b, tol=1e-6)


def maximo_diario(
    plan: PlanConsumo,
    modelo: ModeloUnCompartimento,
    param: Parametros,
    dias_previos: int = 0,
) -> float:
    """Máximo de cafeína diaria (mg) con los horarios del plan.

    Por linealidad, escalar todas las dosis por s escala C(hora_dormir) por s;
    s* = c_sueno / C(hora_dormir). Se limita al máximo diario de la base.
    Salidas: mg por día.
    """
    c_dormir = concentracion_plan(plan, modelo, np.array([param.hora_dormir]), dias_previos)[0]
    return float(min(plan.total_mg * param.c_sueno / c_dormir, param.max_diario_mg))


def comparar_metodos_horas(
    planes: dict[str, PlanConsumo],
    modelos: dict[str, ModeloUnCompartimento],
    param: Parametros,
) -> pd.DataFrame:
    """H_ef por dos métodos: interpolación en malla y cruces por bisección.

    Salidas: DataFrame (grupo, plan, h_malla, h_biseccion, error_rel).
    """
    filas = []
    t = malla_dia(param)
    for grupo, modelo in modelos.items():
        for codigo, plan in planes.items():
            c = concentracion_plan(plan, modelo, t)
            h_malla = horas_efecto(t, c, param.c_efecto, param.inicio, param.fin)
            h_bis = horas_efecto_biseccion(
                lambda x, p=plan, m=modelo: float(concentracion_plan(p, m, np.array([x]))[0]),
                param.c_efecto,
                param.inicio,
                param.fin,
            )
            filas.append(
                {
                    "grupo": grupo,
                    "plan": codigo,
                    "h_malla": h_malla,
                    "h_biseccion": h_bis,
                    "error_rel": abs(h_malla - h_bis) / h_bis if h_bis > 0 else 0.0,
                }
            )
    return pd.DataFrame(filas)


def tabla_horas_limite(
    modelos: dict[str, ModeloUnCompartimento],
    bebidas: pd.DataFrame,
    param: Parametros,
    dias_previos: int = 0,
) -> pd.DataFrame:
    """Hora límite de una toma única de cada bebida para cada grupo.

    Salidas: DataFrame bebida × grupo con la hora límite (h del día).
    """
    filas = []
    for _, beb in bebidas.iterrows():
        fila = {"bebida": beb["bebida"], "cafeina_mg": beb["cafeina_mg"]}
        for grupo, modelo in modelos.items():
            fila[grupo] = hora_limite(modelo, float(beb["cafeina_mg"]), param, None, dias_previos)
        filas.append(fila)
    return pd.DataFrame(filas)


def _combinaciones(n_horas: int, n_bebidas: int, max_tomas: int) -> list[tuple[np.ndarray, ...]]:
    """Índices (horas, bebidas) de todos los planes de 1 a ``max_tomas`` tomas."""
    bloques = []
    for n in range(1, max_tomas + 1):
        horas = np.array(list(itertools.combinations(range(n_horas), n)))
        bebidas = np.array(list(itertools.product(range(n_bebidas), repeat=n)))
        h = np.repeat(horas, len(bebidas), axis=0)
        b = np.tile(bebidas, (len(horas), 1))
        bloques.append((h, b))
    return bloques


def optimizar_plan(
    modelo: ModeloUnCompartimento,
    individuos: list[ModeloUnCompartimento],
    bebidas: pd.DataFrame,
    param: Parametros,
    cobertura_minima: float,
    max_tomas: int = 3,
    paso: float = 0.1,
) -> pd.Series:
    """Busca el plan de 1 a ``max_tomas`` tomas con más horas de efecto.

    Candidatos: bebidas de la hoja Bebidas a horas enteras entre el inicio
    de la jornada y fin − 2 h. Restricciones: C(hora_dormir) < c_sueno para
    la persona representativa, al menos ``cobertura_minima`` % del grupo bajo
    el umbral y cafeína total <= máximo diario. Empates (0,1 h) se rompen
    con menos cafeína y luego menos tomas.
    Salidas: Serie con descripcion, n_tomas, horas_efecto (h), c_dormir
    (mg/L), pct_personas_duermen_bien (%), cafeina_mg (mg).
    """
    # 1) Precalcular la curva de 1 mg para cada hora candidata (persona típica e individuos)
    horas = np.arange(param.inicio, param.fin - 2 + 1e-9, 1.0)
    dosis = bebidas["cafeina_mg"].to_numpy(float)
    nombres = bebidas["bebida"].to_numpy()
    t = np.arange(param.inicio, param.fin + paso / 2, paso)
    unitaria = modelo.concentracion(t[None, :] - horas[:, None], 1.0)
    al_dormir = modelo.concentracion(param.hora_dormir - horas, 1.0)
    ind_dormir = np.array([m.concentracion(param.hora_dormir - horas, 1.0) for m in individuos])
    # 2) Para 1, 2 y 3 tomas: evaluar todas las combinaciones a la vez y filtrar las factibles
    mejores = []
    for h, b in _combinaciones(len(horas), len(dosis), max_tomas):
        d = dosis[b]
        total = d.sum(axis=1)
        c_dormir = np.sum(d * al_dormir[h], axis=1)
        cobertura = 100 * np.mean(
            np.einsum("nj,inj->ni", d, ind_dormir[:, h]) < param.c_sueno, axis=1
        )
        ok = (c_dormir < param.c_sueno) & (total <= param.max_diario_mg)
        ok &= cobertura >= cobertura_minima
        if not ok.any():
            continue
        # 3) Horas con efecto de las factibles (superposición) y el mejor de este número de tomas
        curvas = np.einsum("nj,njt->nt", d[ok], unitaria[h[ok]])
        h_ef = horas_efecto_filas(t, curvas, param.c_efecto)
        for i in np.lexsort((total[ok], -np.round(h_ef, 1)))[:1]:
            fila = np.flatnonzero(ok)[i]
            mejores.append(
                {
                    "descripcion": PlanConsumo(
                        "opt", tuple(horas[h[fila]]), tuple(d[fila]), tuple(nombres[b[fila]])
                    ).descripcion(),
                    "n_tomas": h.shape[1],
                    "horas_efecto": float(h_ef[i]),
                    "c_dormir": float(c_dormir[fila]),
                    "pct_personas_duermen_bien": float(cobertura[fila]),
                    "cafeina_mg": float(total[fila]),
                }
            )
    # 4) Ganador global entre 1, 2 y 3 tomas
    if not mejores:
        return pd.Series(dtype=object)
    tabla = pd.DataFrame(mejores).assign(h_red=lambda x: x["horas_efecto"].round(1))
    tabla = tabla.sort_values(["h_red", "cafeina_mg", "n_tomas"], ascending=[False, True, True])
    return tabla.iloc[0].drop("h_red")


def planes_optimizados(
    modelos: dict[str, ModeloUnCompartimento],
    individuos: dict[str, list[ModeloUnCompartimento]],
    bebidas: pd.DataFrame,
    param: Parametros,
    cobertura_minima: float,
) -> pd.DataFrame:
    """Plan ajustado (fuera del catálogo) de cada grupo; ver ``optimizar_plan``."""
    filas = []
    for g in GRUPOS:
        mejor = optimizar_plan(modelos[g], individuos[g], bebidas, param, cobertura_minima)
        if len(mejor):
            filas.append({"grupo": g, **mejor.to_dict()})
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Escenarios y sensibilidad
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Escenario:
    """Conjunto de supuestos para evaluar los planes."""

    nombre: str
    param: Parametros
    dias_previos: int = 0


def escenarios_definidos(param: Parametros) -> list[Escenario]:
    """Escenario base y dos alternativos factibles.

    * Base: parámetros de la hoja, primer día de consumo.
    * Semana de exámenes: el plan se repite ``DIAS_SEMANA_EXAMENES`` días.
    * Acostarse 1 h antes: la persona se duerme a hora_dormir − 1.
    """
    return [
        Escenario("Base (día 1)", param, 0),
        Escenario(
            f"Semana de exámenes ({DIAS_SEMANA_EXAMENES} días)", param, DIAS_SEMANA_EXAMENES - 1
        ),
        Escenario("Acostarse 1 h antes", param.con_cambios(hora_dormir=param.hora_dormir - 1), 0),
    ]


def evaluar_escenarios(
    escenarios: list[Escenario],
    planes: dict[str, PlanConsumo],
    modelos: dict[str, ModeloUnCompartimento],
    relacion: RelacionAtencion | None = None,
    individuos: dict[str, list[ModeloUnCompartimento]] | None = None,
) -> pd.DataFrame:
    """Evalúa todos los planes en cada escenario (columna ``escenario``)."""
    tablas = [
        evaluar_planes(planes, modelos, e.param, relacion, e.dias_previos, individuos).assign(
            escenario=e.nombre
        )
        for e in escenarios
    ]
    return pd.concat(tablas, ignore_index=True)


def _variar_modelos(
    modelos: dict[str, ModeloUnCompartimento], atributo: str, factor: float
) -> dict[str, ModeloUnCompartimento]:
    """Copia de los modelos con un atributo (k, v_l o ka) multiplicado."""
    return {
        g: ModeloUnCompartimento(**{**m.__dict__, atributo: getattr(m, atributo) * factor})
        for g, m in modelos.items()
    }


def sensibilidad(
    planes: dict[str, PlanConsumo],
    modelos: dict[str, ModeloUnCompartimento],
    param: Parametros,
    variacion: float = VARIACION_SENSIBILIDAD,
) -> pd.DataFrame:
    """Cambia cada parámetro ±``variacion`` (hora de dormir ±1 h) y recalcula.

    Salidas: DataFrame (parametro, cambio, grupo, plan, horas_efecto,
    c_dormir, cambia_decision) respecto a la recomendación base.
    """
    # 1) Decisión de referencia y lista de casos: (nombre, cambio, modelos, parámetros)
    base = recomendar(evaluar_planes(planes, modelos, param)).set_index("grupo")["plan"]
    casos: list[tuple[str, str, dict, Parametros]] = []
    for nombre, attr in [
        ("k (eliminación)", "k"),
        ("V (volumen)", "v_l"),
        ("ka (absorción)", "ka"),
    ]:
        for f in (1 - variacion, 1 + variacion):
            casos.append((nombre, f"{f - 1:+.0%}", _variar_modelos(modelos, attr, f), param))
    for nombre, attr in [("umbral de efecto", "c_efecto"), ("umbral de sueño", "c_sueno")]:
        for f in (1 - variacion, 1 + variacion):
            casos.append(
                (
                    nombre,
                    f"{f - 1:+.0%}",
                    modelos,
                    param.con_cambios(**{attr: getattr(param, attr) * f}),
                )
            )
    for dh in (-1.0, 1.0):
        casos.append(
            (
                "hora de dormir",
                f"{dh:+.0f} h",
                modelos,
                param.con_cambios(hora_dormir=param.hora_dormir + dh),
            )
        )
    # 2) Recalcular la recomendación en cada caso y anotar si cambia el plan elegido
    filas = []
    for nombre, cambio, mods, prm in casos:
        tabla = evaluar_planes(planes, mods, prm)
        rec = recomendar(tabla).set_index("grupo")
        for g in GRUPOS:
            plan = rec["plan"].get(g, "ninguno")
            coincide = tabla[(tabla["grupo"] == g) & (tabla["plan"] == base.get(g))]
            fila_base = (
                coincide.iloc[0]
                if len(coincide)
                else pd.Series({"horas_efecto": np.nan, "c_dormir": np.nan})
            )
            filas.append(
                {
                    "parametro": nombre,
                    "cambio": cambio,
                    "grupo": g,
                    "plan": plan,
                    "horas_efecto": rec["horas_efecto"].get(g, 0.0),
                    "horas_efecto_plan_base": fila_base["horas_efecto"],
                    "c_dormir_plan_base": fila_base["c_dormir"],
                    "cambia_decision": plan != base.get(g),
                }
            )
    return pd.DataFrame(filas)


def guia_consumo(
    recomendacion: pd.DataFrame,
    planes: dict[str, PlanConsumo],
    modelos: dict[str, ModeloUnCompartimento],
    param: Parametros,
    dias_previos: int = 0,
) -> pd.DataFrame:
    """Guía final por grupo: plan, hora límite de la última toma y máximo diario.

    La hora límite se calcula para la última bebida del plan, manteniendo
    las tomas anteriores del mismo plan.
    Salidas: DataFrame con una fila por grupo.
    """
    filas = []
    for _, fila in recomendacion.iterrows():
        plan, modelo = planes[fila["plan"]], modelos[fila["grupo"]]
        # Separar la última bebida del plan de las anteriores (que se mantienen fijas)
        idx = int(np.argmax(plan.horas))
        previas = [i for i in range(len(plan.horas)) if i != idx]
        previo = (
            PlanConsumo(
                "prev",
                tuple(plan.horas[i] for i in previas),
                tuple(plan.dosis_mg[i] for i in previas),
            )
            if previas
            else None
        )
        filas.append(
            {
                "grupo": fila["grupo"],
                "vida_media_h": modelo.vida_media,
                "plan": fila["plan"],
                "descripcion": fila["descripcion"],
                "horas_efecto": fila["horas_efecto"],
                "c_dormir": fila["c_dormir"],
                "cafeina_mg": fila["cafeina_mg"],
                "hora_limite_ultima_toma": hora_limite(
                    modelo, plan.dosis_mg[idx], param, previo, dias_previos
                ),
                "maximo_diario_mg": maximo_diario(plan, modelo, param, dias_previos),
                "mejora_rt_ms": fila.get("mejora_rt_ms", np.nan),
                "pct_personas_duermen_bien": fila.get("pct_personas_duermen_bien", np.nan),
            }
        )
    return pd.DataFrame(filas)
