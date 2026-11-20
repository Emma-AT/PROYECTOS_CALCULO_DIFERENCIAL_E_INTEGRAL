# Cómo conectar el explicador (cuando tengas la clave)

## 1. Crear la clave (tú, unos 3 minutos)
Crea una cuenta con tu correo en la consola de Groq, genera una API key y guárdala en un lugar privado.
Nunca la pegues en el chat, en el código, en un cuaderno ni en un commit.

## 2. Copiar los archivos al proyecto
- `src/explicador.py` → `src/explicador.py`
- `tests/test_explicador.py` → `tests/test_explicador.py`
- Agrega `requests` a `requirements.txt`.
- Agrega al `.gitignore` las líneas de `gitignore_agregar.txt`.

## 3. Poner la clave
- En tu computadora: copia `.streamlit/secrets.toml.example` como `.streamlit/secrets.toml` y pega la clave.
- En Streamlit Community Cloud: Settings → Secrets, y pega la misma línea `GROQ_API_KEY = "..."`.

## 4. Usarlo en la app (semana 14)
```python
import streamlit as st
from src.explicador import explicar

try:
    clave = st.secrets.get("GROQ_API_KEY")
except Exception:
    clave = None  # no hay secrets.toml: se usa el texto local

if st.button("Explicar este resultado"):
    texto, origen = explicar(indicadores, clave=clave)
    st.write(texto)
    st.caption(
        "Redactado con IA" if origen == "ia" else "Texto generado por el código del proyecto"
    )
```
`indicadores` es el diccionario que arma tu `escenarios.py` con sus propios resultados (ver el formato en el encabezado de `explicador.py`).

## 5. Antes de la defensa
- Verifica en la consola de Groq que el modelo `openai/gpt-oss-120b` siga disponible (puedes cambiarlo con la variable `GROQ_MODEL`).
- Prueba la app una vez sin clave y otra con clave.
- Ten claro qué se le envía (solo indicadores agregados) y qué hace la guardia de cifras.
