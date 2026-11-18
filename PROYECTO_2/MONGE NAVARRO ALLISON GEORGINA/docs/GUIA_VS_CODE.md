# Guía para trabajar el proyecto en VS Code

## 1. Instalar lo necesario (una sola vez)

1. **Python 3.11 o superior**: https://www.python.org/downloads/
   En Windows, durante la instalación marque la casilla **"Add Python to PATH"**.
2. **VS Code**: https://code.visualstudio.com/
3. **Git**: https://git-scm.com/
4. En VS Code, abra la pestaña de extensiones (Ctrl+Shift+X) e instale:
   - **Python** (de Microsoft)
   - **Pylance**
   - **Jupyter** (para `analisis.ipynb`)
   - **Ruff** (revisa el estilo del código)

## 2. Obtener el repositorio

1. En GitHub, entre al repositorio del curso y presione **Fork**.
2. En VS Code: `Ctrl+Shift+P` → **Git: Clone** → pegue el enlace de *su* fork.
3. Copie la carpeta `C-06_MONGE` dentro de `PROYECTO_2/`.
4. Copie la carpeta `.github` que viene en `C-06_MONGE` a la **raíz** del fork
   (GitHub solo ejecuta las pruebas automáticas desde ahí).
5. Coloque su Excel `P06_C-06_MONGE.xlsx` en `PROYECTO_2/C-06_MONGE/datos/` sin modificarlo.

## 3. Crear el entorno virtual

Abra la terminal de VS Code (Ctrl+ñ o *Terminal → New Terminal*) y vaya a la carpeta:

```bash
cd PROYECTO_2/C-06_MONGE
python -m venv .venv
```

Actívelo:

- Windows: `.venv\Scripts\activate`
- Mac/Linux: `source .venv/bin/activate`

Instale las bibliotecas:

```bash
pip install -r requirements.txt
```

Luego `Ctrl+Shift+P` → **Python: Select Interpreter** → elija el que dice `.venv`.

## 4. Comandos del día a día

| Qué quiere hacer | Comando |
|---|---|
| Correr las pruebas | `pytest -v` |
| Revisar el estilo | `ruff check .` |
| Ordenar el formato | `ruff format .` |
| Abrir la aplicación web | `streamlit run app.py` |
| Regenerar tablas y figuras | `python -m src.reporte` |

También puede usar el ícono del **matraz (Testing)** en la barra izquierda de VS Code:
muestra cada prueba con una marca verde o roja.

**Importante:** trabaje con el proyecto **fuera de OneDrive** (por ejemplo en `C:\proyectos\`).
OneDrive intenta sincronizar la carpeta `.venv` y eso vuelve todo muy lento.

## 5. La aplicación web

```bash
streamlit run app.py
```

Se abre sola en el navegador (`http://localhost:8501`). Para cerrarla, presione `Ctrl+C` en la
terminal. Si cambia el código, la página muestra un botón **Rerun** para actualizarse.

### Publicarla con un enlace público (Streamlit Community Cloud)

1. Suba todo a su fork en GitHub (paso 7).
2. Entre a https://share.streamlit.io e inicie sesión con su cuenta de GitHub.
3. **Create app** → elija su fork, la rama `main` y como archivo principal
   `PROYECTO_2/C-06_MONGE/app.py`.
4. Presione **Deploy**. En unos minutos tendrá un enlace como `https://…streamlit.app`.
5. Pegue ese enlace en el `README.md`.

## 6. El cuaderno `analisis.ipynb`

1. Ábralo en VS Code.
2. Arriba a la derecha, en **Select Kernel**, elija el entorno `.venv`.
3. Presione **Run All**. Todas las celdas deben correr sin errores y mostrar tablas y gráficos.
4. Guarde el archivo (`Ctrl+S`) para que queden guardados los resultados: el profesor pide el
   cuaderno **ejecutado**.

## 7. Guardar el avance en Git (mínimo 10 *commits*)

Haga un *commit* cada vez que termine una parte, en semanas distintas:

```bash
git add .
git commit -m "Agrega limpieza de conteos con pruebas"
git push
```

El historial de *commits* es parte de la evidencia de que el trabajo es suyo.
