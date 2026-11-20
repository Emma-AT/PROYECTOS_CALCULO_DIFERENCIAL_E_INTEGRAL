"""Construye un cuaderno reproducible a partir de las funciones del proyecto."""

import argparse
import json
import sys
import tempfile
from pathlib import Path

import nbformat
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient

from src.limpieza import RUTA_BASE


def construir() -> nbformat.NotebookNode:
    """Devuelve un cuaderno con exploración, modelo y comprobaciones explicadas."""
    m, c = nbformat.v4.new_markdown_cell, nbformat.v4.new_code_cell
    return nbformat.v4.new_notebook(
        cells=[
            m(
                "# Amenaza sísmica y refuerzo del Hospital de Golfito\nJeremy Fabrizio Fonseca Araya · C23005 · C-03.\n\n"
                "Datos simulados del docente. Primera implementación con asistencia de ChatGPT/Codex, para revisión individual."
            ),
            m(
                "## Pregunta de decisión\n¿Conviene reforzar el pabellón, con cuál opción y cuánta pérdida anual se evita por colón invertido? "
                "El criterio es el mayor VPN entre no invertir, A y B. Los costos, daños y horizonte se leen del Excel."
            ),
            c(
                "from src.limpieza import leer_base\nfrom src.analisis import analizar, tabla_visible\n"
                "from src.graficas import (figura_exploracion, figura_movimiento, figura_recurrencia, "
                "figura_arias, figura_pae, figura_descuento, figura_sensibilidad)\n"
                "from IPython.display import display\nimport matplotlib.pyplot as plt\n"
                "base = leer_base()\nresultado = analizar(base)\n"
                "display(tabla_visible(resultado['escenarios']))"
            ),
            m(
                "## Exploración y tratamiento\nLa ventana es 1996–2025: se supone completa durante 30 años. "
                "Se interpolan solo huecos internos de aceleración. La profundidad faltante se conserva porque "
                "no participa en los cálculos. IQR identifica candidatos atípicos, no errores demostrados. "
                "Se conservan los sismos grandes y los picos del acelerograma."
            ),
            c(
                "for nombre, tabla in base.hojas.items():\n    print(nombre, tabla.shape)\n"
                "display(base.incidencias)\ndisplay(base.hojas['Catalogo_sismos'].describe())\n"
                "display(base.hojas['Catalogo_sismos'][['magnitud_Mw','profundidad_km','distancia_sitio_km']].corr())\n"
                "display(figura_exploracion(base))\nplt.close('all')"
            ),
            m(
                "## Magnitudes: de la densidad a b\nSea $\\beta=b\\ln(10)$ y $m_c=2.95$. "
                "$f(m)=\\beta e^{-\\beta(m-m_c)}$. Por sustitución y partes: "
                "$E[M]=m_c+\\int_0^\\infty u\\beta e^{-\\beta u}du=m_c+1/\\beta$. "
                "Igualando a la media muestral, $b=\\log_{10}(e)/(\\bar m-2.95)$. "
                "La corrección de 0,05 procede del redondeo a 0,1 indicado por el enunciado."
            ),
            c(
                "print('b:', resultado['b'])\nprint('lambda3, eventos/año:', resultado['lambda3'])\n"
                "print('P(M>=6), 50 años:', resultado['prob6_50'])\nprint('P(M>=7), 50 años:', resultado['prob7_50'])\n"
                "display(figura_recurrencia(base, resultado))\nplt.close('all')"
            ),
            m(
                "## Movimiento del suelo\n$v(t)=\\int_0^t a(u)du$, $x(t)=\\int_0^t v(u)du$, "
                "con condiciones iniciales cero. Se resta la media previa al evento. Un sesgo constante c "
                "añade ct a v y $ct^2/2$ a x. La regla del trapecio se implementa en `src/numericos.py`."
            ),
            c(
                "display(resultado['indicadores'])\nfor variable in ['aceleracion','velocidad','desplazamiento']:\n"
                "    display(figura_movimiento(resultado, variable))\n    plt.close('all')\n"
                "display(figura_arias(resultado))\nplt.close('all')"
            ),
            m(
                "## Daño, pérdidas y valor presente\nSe interpola D linealmente entre datos, expresados como fracción. "
                "$PAE=V\\int_5^8D(m)[-\\lambda'(m)]dm$ en colones/año. "
                "Simpson propio usa 16 subdivisiones por tramo; se compara con la integral exacta del mismo modelo. "
                "$VPN=-C+\\Delta PAE(1-e^{-rH})/r$. Para r=0 se usa $-C+\\Delta PAE H$."
            ),
            c(
                "display(figura_pae(base, resultado))\nplt.close('all')\n"
                "display(figura_descuento(resultado))\nplt.close('all')\ndisplay(tabla_visible(resultado['escenarios']))"
            ),
            m(
                "## Verificación\nPara sen(t), v=1−cos(t) y x=t−sen(t). Se mide error de norma máxima, "
                "evitando cocientes en ceros. En el registro entregado, trapecio frente a Simpson mide discrepancia, "
                "no error físico. Una velocidad final cercana a cero amplifica el porcentaje."
            ),
            c(
                "display(resultado['seno'])\nassert (resultado['seno'].error_relativo_max_pct < 0.5).all()\n"
                "display(resultado['verificacion'])"
            ),
            m(
                "## Sensibilidad y condiciones de la decisión\nSe prueba b±0,1 del enunciado y descuento ±2 puntos "
                "porcentuales como supuesto de sensibilidad. La recomendación puede cambiar. "
                "Los escenarios no son un intervalo de confianza estadístico."
            ),
            c(
                "display(figura_sensibilidad(resultado))\nplt.close('all')\ndisplay(resultado['sensibilidad'])\n"
                "print('Recomendación base:', resultado['recomendacion'])"
            ),
            m(
                "## Límites y referencias\nLos datos son simulados. La ley regional se extrapola más allá del máximo "
                "registrado. No se incluye atenuación, respuesta estructural, lesiones o interrupción hospitalaria. "
                "El registro aislado y las curvas de daño no constituyen una evaluación estructural.\n\n"
                "Ver `docs/MATEMATICA.md`, `docs/BITACORA.md` y `docs/REFERENCIAS.md` para "
                "las deducciones completas, los supuestos y las fuentes."
            ),
        ],
        metadata={
            "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}
        },
    )


def main() -> None:
    """Genera analisis.ipynb; --ejecutar usa el intérprete activo y verifica cada celda."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--ejecutar", action="store_true")
    parser.add_argument(
        "--en-proceso",
        action="store_true",
        help="Ejecuta realmente las celdas con IPython sin abrir sockets de kernel.",
    )
    args = parser.parse_args()
    nb = construir()
    if args.en_proceso:
        from IPython.core.interactiveshell import InteractiveShell
        from IPython.utils.capture import capture_output

        shell = InteractiveShell.instance()
        from IPython.core.pylabtools import print_figure
        from matplotlib.figure import Figure

        shell.display_formatter.formatters["image/png"].for_type(
            Figure, lambda fig: print_figure(fig, fmt="png")
        )
        numero = 0
        for celda in nb.cells:
            if celda.cell_type != "code":
                continue
            numero += 1
            with capture_output() as salida:
                resultado = shell.run_cell(celda.source, store_history=True)
            if not resultado.success:
                resultado.raise_error()
            celda.execution_count = numero
            celda.outputs = []
            if salida.stdout:
                celda.outputs.append(
                    nbformat.v4.new_output("stream", name="stdout", text=salida.stdout)
                )
            if salida.stderr:
                celda.outputs.append(
                    nbformat.v4.new_output("stream", name="stderr", text=salida.stderr)
                )
            for visual in salida.outputs:
                import base64

                datos = {
                    tipo: base64.b64encode(valor).decode("ascii")
                    if isinstance(valor, bytes)
                    else valor
                    for tipo, valor in visual.data.items()
                }
                celda.outputs.append(
                    nbformat.v4.new_output("display_data", data=datos, metadata=visual.metadata)
                )
        nb.metadata["execution_method"] = (
            "IPython en proceso, ejecución real secuencial sin sockets"
        )
    elif args.ejecutar:
        with tempfile.TemporaryDirectory() as temporal:
            kernel = Path(temporal) / "sismos"
            kernel.mkdir()
            especificacion = {
                "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                "display_name": "Sismos",
                "language": "python",
            }
            (kernel / "kernel.json").write_text(json.dumps(especificacion), encoding="utf-8")
            from jupyter_client import KernelManager

            km = KernelManager(
                kernel_name="sismos",
                kernel_spec_manager=KernelSpecManager(kernel_dirs=[temporal]),
            )
            NotebookClient(
                nb, km=km, timeout=120, resources={"metadata": {"path": str(RUTA_BASE)}}
            ).execute()
    nbformat.write(nb, RUTA_BASE / "analisis.ipynb")
    print(
        "Cuaderno guardado"
        + (" y ejecutado sin errores." if args.ejecutar or args.en_proceso else ".")
    )


if __name__ == "__main__":
    main()
