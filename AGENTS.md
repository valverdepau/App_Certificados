# AGENTS.md

## Contexto del proyecto

Academia Horizonte: centro de formación que imparte programas técnicos a empresas. Al cerrar cada cohorte emite certificados por estudiante. Hoy el proceso es manual en Excel y Word; se automatiza como aplicación web.

## Arquitectura (3 piezas)

- Bodega (datos): los Excel en `insumos/`. NO se modifican.
- Cocina (backend): Python con Flask, en `app.py`. Toda la lógica va aquí, NUNCA en la interfaz.
- Salón (frontend): páginas web HTML servidas por Flask. Solo muestra información; no calcula ni decide.

## Proyecto

App de Certificados de la Academia. Repo en desarrollo todavía sin código de aplicación ni manifiesto; contiene los insumos de datos (`Insumos/`) y la especificación de la arquitectura esperada. Stack objetivo: Python 3.12 + Flask + PostgreSQL/Supabase, gestionado con `uv` (nunca `pip`).

## Fuente de datos — `Insumos/` (solo lectura)

Dos libros de trabajo (uno por archivo), cada uno con una sola hoja. Nombres exactos de hoja y columnas (español con acentos); cualquier consumidor hace joins con estos:

- `Insumos/Maestro_Estudiantes.xlsx` → sheet `Estudiantes` (24 data rows)
  - `Identificacion`, `Nombre_Completo`, `Correo`, `Programa`, `Cohorte`
- `Insumos/Registro_Evaluaciones.xlsx` → sheet `Evaluaciones` (88 data rows)
  - `Identificacion`, `Programa`, `Modulo`, `Nota`, `Asistencia_Pct`, `Fecha_Cierre`

### Quirks que rompen la ingesta

- `Identificacion` se almacena como **texto**, no número. Únirla como string y no convertir a int.
- `Fecha_Cierre` es texto ISO `YYYY-MM-DD`, no fecha de Excel.
- Registro huérfano: la identificación `999880777` tiene evaluaciones pero no existe en `Estudiantes`.
- El estudiante `304560321` existe en el maestro pero **no** tiene filas de evaluación.
- Cobertura de módulos distinta por programa: `Técnico en IA Aplicada` tiene Módulos 1–4; `Excel Avanzado para Negocios` tiene Módulos 1–3.
- `Nota` y `Asistencia_Pct` van de 0 a 100; `0` es un valor real, no dato faltante.
- Los 24 estudiantes son cohorte `2026-A`; dos programas en total.
- Los archivos de `Insumos/` son fuente de verdad; no modificarlos.

### Cifras de control esperadas

Entre los 23 estudiantes con evaluaciones (más 1 huérfano y 1 sin evaluaciones):

- **19** Aprobación (promedio nota ≥ 70 y asistencia ≥ 80)
- **3** Participación (promedio nota < 70 y asistencia ≥ 80)
- **1** Sin certificado (asistencia < 80)
- **3** inconsistencias reportadas como alerta:
  1. `304560321` (Javier Espinoza): en el maestro, sin evaluaciones.
  2. `999880777`: evaluaciones registradas, no existe en el maestro.
  3. Fernanda Zúñiga (`111230984`): asistencia promedio `36.25%` (< 50%).

### Casos de control

- Camila Rojas Méndez (`101230456`): promedio nota `91.25`, asistencia `96.25` → Aprobación.
- Luis Acuña Blanco (`402340178`): promedio nota `72.0`, asistencia `81.67` → Aprobación.

## Reglas de negocio (fórmulas)

- Promedio de nota = suma de `Nota` / cantidad de módulos cursados.
- Asistencia = promedio de `Asistencia_Pct`.
- Se agrupa por `Identificacion + Programa`; un certificado por estudiante y programa.
- Los límites incluyen el valor (`>=`, `<`): Aprobación si promedio ≥ 70 y asistencia ≥ 80; Participación si promedio < 70 y asistencia ≥ 80; Sin certificado si asistencia < 80.

## Arquitectura esperada (MVC)

- `models/datos.py`: **único** archivo que conecta con Supabase/PostgreSQL. Usa `psycopg` con `prepare_threshold=None` (compatibilidad con el pooler). Lee `DATABASE_URL` con `python-dotenv`. No SQL directo fuera de aquí.
- `models/certificados.py`: reglas de negocio puras, sin HTTP ni BD. Constantes obligatorias `NOTA_MINIMA = 70` y `ASISTENCIA_MINIMA = 80`. Agrupa evaluaciones por `identificacion + programa`, calcula promedios/asistencia redondeados a 2 decimales y determina estado:
  - Aprobación: promedio ≥ 70 y asistencia ≥ 80
  - Participación: promedio < 70 y asistencia ≥ 80
  - Sin certificado: asistencia < 80
  - Inconsistencia: sin evaluaciones, identificación no registrada en el maestro, o asistencia promedio < 50%
- `services/carga_excel.py`: procesa Excel (desde `insumos/` o subidos por usuario) con `pandas` + `openpyxl` y persiste vía `models/datos.py`. `Identificacion` siempre se guarda como string limpio sin espacios.
- `services/generador_pdf.py`: genera certificados con `fpdf2` en A4 horizontal; sin lógica de BD.
- `controllers/`: rutas Flask delgadas (`/`, `/cargar`, `/certificado/<identificacion>/<programa>`, `/descargar-todos`), sin cálculos ni SQL.
- `views/`: plantillas Jinja solo presentación. Paleta: `#14213D` (azul marino) y `#B8923D` (dorado).
- `app.py`: instancia Flask en la variable `app` y puerto `5000`.

## Stack y herramientas

- Python 3.12; gestor `uv` (0.12.x) para instalar y ejecutar; no usar `pip`.
- Librerías: Flask, psycopg, python-dotenv, pandas, openpyxl, fpdf2.
- BD: Supabase/PostgreSQL vía `psycopg`; `prepare_threshold=None`.

## Decisiones técnicas (implementación)

- Dependencias y ejecución con `uv`, no `pip`.
- Lectura Excel: `pandas` con engine `openpyxl`; `Identificacion` se fuerza a texto y se recorta.
- Servidor web: Flask con plantillas Jinja.
- PDFs: `fpdf2`, A4 horizontal.
- Base de datos: PostgreSQL/Supabase vía `psycopg`; conexión y SQL únicamente en `models/datos.py`; `prepare_threshold=None`.
- Secreto: `DATABASE_URL` se lee con `python-dotenv`.
- Plan detallado por etapas en `PLAN.md`.

## Seguridad y entorno

- `.env` está en `.gitignore` y contiene `DATABASE_URL`; `.env.ejemplo` es la plantilla (vacía).
- No hardcodear credenciales, tokens ni cadenas de conexión; usar `os.getenv`/`python-dotenv`.
- No leer ni exponer `.env`.
- `Insumos/` es de solo lectura.

## Agentes disponibles

- `.agents/agents/backend-flask.md`
- `.agents/agents/disenador-vistas.md`
- `.agents/agents/revisor.md`
- `.agents/agents/tester-datos.md`

## Comandos de verificación

- Inspeccionar una hoja:
  ```bash
  python3 -c "import openpyxl; wb=openpyxl.load_workbook('Insumos/Maestro_Estudiantes.xlsx'); [print(r) for r in wb['Estudiantes'].iter_rows(values_only=True)]"
  ```
- Cuando exista `app.py`, ejecutar con `uv run python app.py` y verificar http://localhost:5000.

## Estilo de trabajo

- Código simple y comentado en español, señalando los bloques básicos: variables, tipos, condicionales, bucles y funciones.
- Diseño web en azul marino y dorado (`#14213D`, `#B8923D`).
- Explicar en español sencillo lo que se vaya haciendo.

## Idioma y comunicación

- Responder y comunicarse siempre en español.
- Usar explicaciones claras, sencillas y didácticas, orientadas a principiantes.
- Mantener este archivo en español.
