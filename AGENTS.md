# AGENTS.md

## What this repo is

Input data only ("Insumos") for a certificate-generation app (App_Certificados). **No application code lives here** — the app that consumes these files is built elsewhere. Don't search for entrypoints, configs, or tests; there is no package manifest, CI, or git history.

## Data contract

Two workbooks, both with a single sheet. Sheet and column names are exact (Spanish, with accents) — any consumer joins on these:

- `Insumos/Maestro_Estudiantes.xlsx` → sheet `Estudiantes` (24 rows)
  - `Identificacion`, `Nombre_Completo`, `Correo`, `Programa`, `Cohorte`
- `Insumos/Registro_Evaluaciones.xlsx` → sheet `Evaluaciones` (88 rows)
  - `Identificacion`, `Programa`, `Modulo`, `Nota`, `Asistencia_Pct`, `Fecha_Cierre`

## Quirks that will trip you up

- `Identificacion` is stored as **text**, not a number. Join on it as a string; never coerce to int.
- `Fecha_Cierre` is ISO-format **text** (`YYYY-MM-DD`), not an Excel date.
- Orphan record: eval ID `999880777` has no matching student in `Estudiantes`.
- Student `304560321` exists in the master but has **no** evaluation rows.
- Module coverage differs by program: `Técnico en IA Aplicada` has Módulos 1–4 (4 rows/student); `Excel Avanzado para Negocios` has only Módulo 1 (1 row/student).
- `Nota` and `Asistencia_Pct` range 0–100; `0` is a real value, not missing data.
- All 24 students are cohort `2026-A`; two programs total.

## Working with the data

- No tooling in-repo. To inspect or validate after edits, read the sheets directly, e.g.:
  ```bash
  python3 -c "import openpyxl; wb=openpyxl.load_workbook('Insumos/Maestro_Estudiantes.xlsx'); [print(r) for r in wb['Estudiantes'].iter_rows(values_only=True)]"
  ```
- Treat the two files as the source of truth for the app's data model; keep column names and sheet names unchanged when editing.

## Idioma y Comunicación

- Responder y comunicarse siempre en español.
- Usar explicaciones claras, sencillas y didácticas, orientadas a principiantes.
