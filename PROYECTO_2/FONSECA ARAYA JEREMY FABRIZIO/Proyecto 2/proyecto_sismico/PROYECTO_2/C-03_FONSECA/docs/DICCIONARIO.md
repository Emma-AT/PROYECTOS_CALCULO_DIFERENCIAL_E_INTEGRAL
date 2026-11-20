# Diccionario de datos

Transcripción automática de la hoja Diccionario.

| Hoja | Columna | Significado | Unidad |
|---|---|---|---|
| Catalogo_sismos | id_sismo | Identificador del sismo | --- |
| Catalogo_sismos | fecha_hora | Fecha y hora del registro (año-mes-día hora:minuto) | fecha y hora |
| Catalogo_sismos | magnitud_Mw | Magnitud de momento del sismo | Mw |
| Catalogo_sismos | profundidad_km | Profundidad del hipocentro | km |
| Catalogo_sismos | distancia_sitio_km | Distancia del epicentro al sitio | km |
| Acelerograma | tiempo_s | Tiempo desde el inicio del registro | s |
| Acelerograma | aceleracion_cm_s2 | Aceleración del suelo registrada por el acelerógrafo | cm/s² |
| Evento | evento | Código del sismo registrado | --- |
| Evento | fecha | Fecha del registro (año-mes-día) | fecha |
| Evento | magnitud_Mw | Magnitud de momento del sismo | Mw |
| Evento | distancia_km | Distancia del epicentro a la estación | km |
| Evento | estacion | Ubicación y tipo de suelo de la estación | --- |
| Evento | segundos_previos_al_sismo | Segundos del registro antes de la llegada de las ondas (sirven para la línea base) | s |
| Vulnerabilidad | magnitud_Mw | Magnitud de momento del sismo | Mw |
| Vulnerabilidad | dano_actual_pct | Daño esperado del edificio actual según la magnitud | % del valor |
| Vulnerabilidad | dano_opcion_A_pct | Daño esperado con la opción A de refuerzo | % del valor |
| Vulnerabilidad | dano_opcion_B_pct | Daño esperado con la opción B de refuerzo | % del valor |
| Edificacion | parametro | Nombre del parámetro del problema | --- |
| Edificacion | valor | Valor numérico del parámetro | ver columna unidad |
| Edificacion | unidad | Unidad del parámetro | --- |
| Opciones_refuerzo | opcion | Identificador de la opción que se evalúa | --- |
| Opciones_refuerzo | descripcion | Descripción de la opción | --- |
| Opciones_refuerzo | costo_colones | Costo de la opción | colones |
| Opciones_refuerzo | plazo_obra_meses | Duración de la obra | meses |
