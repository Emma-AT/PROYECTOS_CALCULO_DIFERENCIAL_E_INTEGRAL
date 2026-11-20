"""Demostración en vivo de las fórmulas de integración con los datos reales del proyecto.

Uso (desde PROYECTO_2/C-09_VILLALOBOS):
    ../../.venv/bin/python ../../tools/demo_integracion.py          # voluntario V01
    ../../.venv/bin/python ../../tools/demo_integracion.py V15      # otro voluntario
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "PROYECTO_2" / "C-09_VILLALOBOS"))

from src import modelo  # noqa: E402
from src.pipeline import AnalisisCafeina  # noqa: E402


def titulo(texto: str) -> None:
    print(f"\n{'=' * 70}\n{texto}\n{'=' * 70}")


def main() -> None:
    vol = sys.argv[1] if len(sys.argv) > 1 else "V01"
    a = AnalisisCafeina.desde_excel()
    p = a.param
    datos = a.conc_limpio[a.conc_limpio["voluntario"] == vol].sort_values("tiempo_h")
    t = np.concatenate([[0.0], datos["tiempo_h"].to_numpy()])
    c = np.concatenate([[0.0], datos["concentracion_mg_L"].to_numpy()])
    r = a.resultados.loc[vol]
    m = modelo.modelo_de(r, p.ka)

    titulo(f"1) TRAPECIO: ∫ f ≈ Σ (x_i+1 − x_i)·(y_i + y_i+1)/2   [voluntario {vol}]")
    print("Primeros tramos (área de cada trapecio):")
    for i in range(4):
        area = (t[i + 1] - t[i]) * (c[i] + c[i + 1]) / 2
        print(f"  [{t[i]:5.2f}, {t[i + 1]:5.2f}] h  ({t[i + 1] - t[i]:.2f}) · ({c[i]:.2f} + {c[i + 1]:.2f})/2"
              f" = {area:.3f} mg·h/L")
    trap = modelo.trapecio(t, c)
    print(f"Suma de los {len(t) - 1} trapecios, de 0 a 24 h: {trap:.3f} mg·h/L")

    titulo("2) SIMPSON: parábolas por cada par de tramos (espaciado irregular)")
    simp = modelo.simpson(t, c)
    print(f"Simpson de 0 a 24 h: {simp:.3f} mg·h/L   (diferencia con trapecio: "
          f"{100 * abs(trap - simp) / simp:.1f} %)")
    print("Se usa el trapecio para el AUC: el salto de 12 a 24 h es largo y la parábola no sigue "
          "bien a la exponencial.")

    titulo("3) INTEGRAL IMPROPIA: AUC = ∫_0^24 (trapecio) + cola C(24)/k")
    cola = c[-1] / r["k_1_h"]
    print(f"k = {r['k_1_h']:.4f} 1/h   C(24) = {c[-1]:.3f} mg/L   cola = C(24)/k = {cola:.3f} mg·h/L")
    print(f"AUC total = {trap:.3f} + {cola:.3f} = {trap + cola:.3f} mg·h/L   "
          f"(la cola es el {100 * cola / (trap + cola):.1f} %)")
    print(f"De ahí salen CL = D/AUC = {r['cl_l_h']:.3f} L/h y V = CL/k = {r['v_l']:.2f} L "
          "(la comprobación independiente es el punto 5)")

    titulo("4) CONVERGENCIA: ∫_0^T e^(−kt) dt → 1/k cuando T → ∞ (Simpson propio)")
    k = r["k_1_h"]
    for tope in (10, 24, 50, 100, 200):
        print(f"  T = {tope:4d} h   ∫ = {modelo.integral_exponencial_truncada(k, tope):8.4f} h")
    print(f"  1/k          = {1 / k:8.4f} h")

    titulo("5) VALIDACIÓN OBLIGATORIA: Simpson de C(t) hasta 200 h contra D/(Vk)")
    tt = np.linspace(0, 200, 20001)
    num = modelo.simpson(tt, m.concentracion(tt, p.dosis_mg))
    exacta = m.auc_infinito(p.dosis_mg)
    print(f"Numérica = {num:.4f}   fórmula = {exacta:.4f}   error = {100 * abs(num - exacta) / exacta:.4f} %"
          "  (límite 0,5 %)")

    titulo("6) HORAS CON EFECTO: H = ∫_8^20 1[C(t) ≥ 1,5] dt, por malla y por bisección")
    malla = np.arange(0, 32 + 1 / 60, 1 / 60)
    curva = m.concentracion(malla - p.inicio, p.dosis_mg)
    h_malla = modelo.horas_efecto(malla, curva, p.c_efecto, p.inicio, p.fin)
    h_bis = modelo.horas_efecto_biseccion(lambda x: float(m.concentracion(x - p.inicio, p.dosis_mg)),
                                          p.c_efecto, p.inicio, p.fin)
    print(f"Con {p.dosis_mg:.0f} mg a las {p.inicio:.0f}:00 →  malla: {h_malla:.4f} h   "
          f"bisección: {h_bis:.4f} h")


if __name__ == "__main__":
    main()
