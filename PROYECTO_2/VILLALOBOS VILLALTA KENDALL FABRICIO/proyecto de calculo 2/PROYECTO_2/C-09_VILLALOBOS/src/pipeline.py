"""Orquesta el análisis completo a partir del Excel (usado por reporte, app y cuaderno).

Es el «director de orquesta»: no calcula nada por sí mismo, llama en orden a
limpieza -> modelo -> escenarios y guarda los resultados en un solo objeto.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

import pandas as pd

from src import escenarios as esc
from src import limpieza, modelo
from src.config import COBERTURA_PRUDENTE, RUTA_DATOS


@dataclass
class AnalisisCafeina:
    """Resultados de todo el flujo: datos -> modelo -> verificación -> decisión.

    Se construye con ``AnalisisCafeina.desde_excel(ruta)``. Todos los
    atributos son tablas de pandas u objetos del modelo; las unidades
    están en los nombres de las columnas o en los docstrings de origen.
    """

    hojas: dict[str, pd.DataFrame]
    param: limpieza.Parametros
    conc_limpio: pd.DataFrame
    bitacora: pd.DataFrame
    resultados: pd.DataFrame
    clasificados: pd.DataFrame
    atencion: pd.DataFrame
    relacion: modelo.RelacionAtencion
    planes: dict[str, esc.PlanConsumo]
    modelos: dict[str, modelo.ModeloUnCompartimento]
    individuos: dict[str, list[modelo.ModeloUnCompartimento]]
    tablas: dict[str, pd.DataFrame] = field(default_factory=dict)

    @classmethod
    def desde_excel(cls, ruta: str | Path | IO[bytes] = RUTA_DATOS) -> AnalisisCafeina:
        """Lee la base, la limpia y ajusta el modelo de cada voluntario."""
        # 1) Leer y validar el Excel; los parámetros del problema salen de la hoja Parametros
        hojas = limpieza.leer_base(ruta)
        param = limpieza.leer_parametros(hojas["Parametros"])
        # 2) Tratar faltantes y atípicos de las concentraciones
        conc, bitacora = limpieza.limpiar_concentraciones(hojas["Concentraciones"])
        # 3) k, vida media, AUC (integral impropia), CL y V de cada voluntario
        resultados = modelo.analizar_todos(conc, param.dosis_mg)
        # 4) Grupos rápida / normal / lenta y datos de atención emparejados con C
        clasificados = esc.clasificar(resultados, hojas["Voluntarios"])
        atencion = limpieza.unir_atencion(limpieza.revisar_pruebas(hojas["Pruebas_atencion"]), conc)
        # 5) Planes del Excel y modelos (persona típica e individuos) de cada grupo
        return cls(
            hojas=hojas,
            param=param,
            conc_limpio=conc,
            bitacora=bitacora,
            resultados=resultados,
            clasificados=clasificados,
            atencion=atencion,
            relacion=modelo.ajustar_atencion(atencion),
            planes=esc.construir_planes(hojas["Planes"], hojas["Bebidas"]),
            modelos=esc.modelos_por_grupo(clasificados, param.ka),
            individuos=esc.modelos_individuales(clasificados, param.ka),
        )

    def calcular_tablas(self) -> dict[str, pd.DataFrame]:
        """Calcula verificación, escenarios, sensibilidad y guía de consumo.

        Cada clave del diccionario se guarda luego como ``resultados/tablas/<clave>.csv``.
        """
        # 1) Evaluar los 6 planes en los 3 escenarios y elegir el mejor por grupo
        p = self.param
        lista_esc = esc.escenarios_definidos(p)
        evaluacion = esc.evaluar_escenarios(
            lista_esc, self.planes, self.modelos, self.relacion, self.individuos
        )
        recomendaciones = esc.recomendar(evaluacion)
        prudentes = esc.recomendar(evaluacion, COBERTURA_PRUDENTE)
        base = recomendaciones[recomendaciones["escenario"] == lista_esc[0].nombre]
        base_prudente = prudentes[prudentes["escenario"] == lista_esc[0].nombre]
        grupos = self.clasificados.groupby("grupo", observed=True)
        # 2) Reunir todas las tablas: datos, verificación, decisión y sensibilidad
        self.tablas = {
            "calidad_datos": limpieza.resumen_calidad(self.hojas),
            "bitacora_limpieza": self.bitacora,
            "resultados_voluntarios": self.clasificados.reset_index(),
            "resumen_grupos": grupos[["vida_media_h", "k_1_h", "v_l", "cl_l_h", "pct_cola"]]
            .agg(["count", "median", "min", "max"])
            .round(3),
            "factores_vida_media": esc.comparar_factores(self.clasificados),
            "validacion_auc": modelo.validar_auc_modelo(self.resultados, p.ka, p.dosis_mg),
            "verificacion_datos": modelo.verificar_contra_datos(
                self.conc_limpio, self.resultados, p.ka, p.dosis_mg
            ),
            "evaluacion_planes": evaluacion,
            "recomendaciones": recomendaciones,
            "recomendaciones_prudentes": prudentes,
            "comparacion_horas_efecto": esc.comparar_metodos_horas(self.planes, self.modelos, p),
            "sensibilidad": esc.sensibilidad(self.planes, self.modelos, p),
            "horas_limite": esc.tabla_horas_limite(self.modelos, self.hojas["Bebidas"], p),
            "guia_consumo": esc.guia_consumo(base, self.planes, self.modelos, p),
            "guia_consumo_prudente": esc.guia_consumo(base_prudente, self.planes, self.modelos, p),
            "planes_optimizados": esc.planes_optimizados(
                self.modelos, self.individuos, self.hojas["Bebidas"], p, COBERTURA_PRUDENTE
            ),
        }
        return self.tablas
