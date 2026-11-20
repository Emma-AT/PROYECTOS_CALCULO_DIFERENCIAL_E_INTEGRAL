"""Rutas relativas y constantes metodológicas del proyecto.

Los parámetros del problema (dosis, umbrales, horarios, constante de
absorción) NO están aquí: se leen de la hoja ``Parametros`` del Excel.
Aquí solo viven decisiones de método documentadas en
``docs/bitacora_supuestos.md``.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Rutas (relativas a la carpeta del proyecto, funcionan en cualquier equipo)
# ---------------------------------------------------------------------------

RAIZ: Path = Path(__file__).resolve().parents[1]
RUTA_DATOS: Path = RAIZ / "datos" / "P02_C-09_VILLALOBOS.xlsx"
DIR_RESULTADOS: Path = RAIZ / "resultados"
DIR_TABLAS: Path = DIR_RESULTADOS / "tablas"
DIR_FIGURAS: Path = DIR_RESULTADOS / "figuras"

# ---------------------------------------------------------------------------
# Constantes de método (limpieza, integración, escenarios y sensibilidad)
# ---------------------------------------------------------------------------

T_TERMINAL_H: float = 6.0
"""Inicio de la fase terminal (h) para estimar k, según el enunciado."""

FACTOR_ATIPICO: float = 1.8
"""Un punto es atípico si difiere más de este factor de lo esperado
por interpolación log-lineal entre sus vecinos válidos."""

RANGO_TR_MS: tuple[float, float] = (100.0, 1000.0)
"""Rango fisiológicamente plausible del tiempo de reacción simple (ms)."""

HORIZONTE_VALIDACION_H: float = 200.0
"""Horizonte de integración (h) para la validación AUC = D/(V k)."""

TOLERANCIA_VALIDACION: float = 0.005
"""Error relativo máximo admitido en la validación (0,5 %)."""

PASO_MALLA_H: float = 1 / 60
"""Paso (h) de la malla temporal para evaluar planes (1 minuto)."""

DIAS_SEMANA_EXAMENES: int = 5
"""Días consecutivos de consumo en el escenario de semana de exámenes."""

VARIACION_SENSIBILIDAD: float = 0.20
"""Variación relativa (±) de cada parámetro en el análisis de sensibilidad."""

COBERTURA_PRUDENTE: float = 80.0
"""Porcentaje mínimo de personas del grupo bajo el umbral de sueño para
la recomendación prudente (supuesto de diseño de la campaña)."""

SEMILLA: int = 2026
"""Semilla para la prueba de permutaciones (reproducibilidad)."""

# ---------------------------------------------------------------------------
# Etiquetas comunes a figuras, documentos y aplicación
# ---------------------------------------------------------------------------

FUENTE: str = "Fuente: P02_C-09_VILLALOBOS.xlsx (datos simulados con fines didácticos)"

GRUPOS: tuple[str, str, str] = ("rápida", "normal", "lenta")
"""Tipos de eliminación, del tercio con menor vida media al de mayor."""
