# Contexto para continuar con Codex

Proyecto académico individual de Jeremy Fabrizio Fonseca Araya, C23005, código C-03.
El trabajo está en `PROYECTO_2/C-03_FONSECA/`. Corresponde a cálculo integral:
amenaza sísmica y refuerzo del Hospital de Golfito.

## Criterios de trabajo

- Mantener el Excel entregado intacto. Toda transformación se documenta.
- Leer los parámetros económicos y los datos desde el Excel.
- Implementar trapecio, Simpson e integral acumulada en código propio. SciPy sirve para comparar.
- Mantener todas las fórmulas en `src/`; la app solo organiza la interacción.
- Explicar los cambios en español sencillo y relacionar el código con su fórmula matemática.
- Mantener consistentes app, cuaderno, resultados y documentos generados.
- Usar datos simulados como tales; no presentarlos como registros oficiales del hospital.
- Mostrar explícitamente límites, discrepancias y supuestos que afecten la decisión.
- Conservar el crédito de asistencia y la bitácora de trabajo individual.
- No inventar commits históricos, publicaciones, enlaces ni pruebas de CI remoto.

## Verificación de cambios

Desde `PROYECTO_2/C-03_FONSECA/`, con el entorno activado:

```bash
ruff check .
ruff format --check .
pytest -q
python -m src.reporte
```

Si cambian cálculos o narrativa, regenerar también `analisis.ipynb` con `python -m src.cuaderno --ejecutar`.
Los PDFs se regeneran con el reporte. Revisar visualmente las páginas afectadas.
El workflow operativo está en `.github/workflows/pruebas.yml` en la raíz del fork.

Los pendientes de entrega están en `docs/CUMPLIMIENTO.md`. Seguir las decisiones
matemáticas de `docs/BITACORA.md` y las deducciones de `docs/MATEMATICA.md`.
