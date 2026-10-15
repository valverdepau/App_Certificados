# PLAN.md

Implementación por etapas. Primero validamos datos, luego backend, luego interfaz. En cada etapa hay un criterio de validación que debe cumplirse antes de pasar a la siguiente.

## Etapa 0 — Entorno base

- Crear entorno con `uv` y declarar dependencias: Flask, pandas, openpyxl, psycopg, python-dotenv, fpdf2.
- Crear `.env` local con `DATABASE_URL` (no versionado). Mantener `.env.ejemplo` vacío.
- Confirmar que Flask corre en el puerto 5000 con una app mínima.

Validación:
- `uv run python --version`
- `uv run python -c "import flask, pandas, openpyxl, psycopg, dotenv, fpdf"`
- `uv run python app.py` responde en `http://localhost:5000`.

## Etapa 1 — Validación de cruce de datos (solo lectura)

- Script de análisis sobre `Insumos/`:
  - verificar hojas y encabezados exactos;
  - verificar `Identificacion` como texto;
  - verificar programa consistente entre maestro y evaluaciones;
  - listar huérfanos, estudiantes sin evaluaciones y asistencias < 50%;
  - recalcular conteos: 19 Aprobación, 3 Participación, 1 Sin certificado, 3 inconsistencias.
- Validar los casos Camila (`91.25`, `96.25`) y Luis (`72.0`, `81.67`).

Validación:
- Salida del script coincide con las cifras de control de `AGENTS.md`.
- No se modifica ningún archivo en `Insumos/`.

## Etapa 2 — Modelo de acceso a datos (`models/datos.py`)

- Implementar conexión única a Supabase/PostgreSQL con `psycopg` y `prepare_threshold=None`.
- Leer `DATABASE_URL` desde `.env` con `python-dotenv`.
- Crear funciones para guardar maestro y evaluaciones.
- Evitar SQL directo fuera de este archivo.

Validación:
- Prueba de conexión exitosa.
- Inserción y lectura de datos de prueba sin credenciales hardcodeadas.
- `git diff` confirma que `.env` no se versiona.

## Etapa 3 — Reglas de negocio (`models/certificados.py`)

- Definir `NOTA_MINIMA = 70` y `ASISTENCIA_MINIMA = 80`.
- Agrupar por `Identificacion + Programa`.
- Calcular promedio de nota y promedio de asistencia, redondeados a 2 decimales.
- Determinar estado: Aprobación, Participación, Sin certificado o Inconsistencia.
- Detectar las 3 inconsistencias definidas.

Validación:
- Pruebas unitarias con los 23 grupos de estudiantes + huérfano.
- Se reproducen las cifras: 19 / 3 / 1 / 3.
- Los `0` no se tratan como nulos.

## Etapa 4 — Servicio de carga Excel (`services/carga_excel.py`)

- Lectura con `pandas` + `openpyxl`.
- Normalizar `Identificacion` a string recortado.
- Validar encabezados exactos.
- Validar programa consistente.
- Guardar vía `models/datos.py`.

Validación:
- Carga completa sin errores.
- Re-ejecutar Etapa 3 sobre datos persistidos y obtener las mismas cifras.

## Etapa 5 — Generación de PDF (`services/generador_pdf.py`)

- Implementar certificado A4 horizontal con `fpdf2`.
- Generar PDF individual por ruta `/certificado/<identificacion>/<programa>`.
- Generar `.zip` para `/descargar-todos`.

Validación:
- PDF abre correctamente y contiene datos esperados.
- ZIP contiene la cantidad esperada de archivos (22 certificados válidos).

## Etapa 6 — Controladores y app (`controllers/`, `app.py`)

- Rutas: `/`, `/cargar`, `/certificado/<identificacion>/<programa>`, `/descargar-todos`.
- Controladores delgados, sin cálculos ni SQL.
- Instanciar Flask en `app` y configurar puerto 5000.

Validación:
- Cada ruta responde con código esperado.
- Subida de los dos Excel funciona desde `/cargar`.

## Etapa 7 — Interfaz (`views/` o `templates/`, `static/`)

- Dashboard con resumen de estudiantes, estado de certificación y alertas de inconsistencias.
- Formulario de carga con retroalimentación visual.
- Paleta azul marino `#14213D` y dorado `#B8923D`.
- La vista solo presenta datos.

Validación:
- Renderiza sin errores en navegador.
- Alertas visibles para las 3 inconsistencias.

## Etapa 8 — Verificación final (tester)

- Ruta `/` muestra 19 Aprobación, 3 Participación, 1 Sin certificado.
- Se muestran las 3 inconsistencias:
  - `304560321` sin evaluaciones.
  - `999880777` no registrado en el maestro.
  - Fernanda Zúñiga con asistencia `36.25%`.
- Casos Camila y Luis validados.
- Descargas individual y masiva funcionan.

Validación:
- Checklist completa de `AGENTS.md` sin hallazgos críticos.