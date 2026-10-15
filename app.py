# app.py
# ----------------------------------------------------------------------
# APLICACION WEB - COCINA (backend)
# Toda la logica vive aqui. Las vistas solo muestran, no calculan.
# ----------------------------------------------------------------------

import io
from pathlib import Path

import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash

# carpeta de plantillas: "views/" (segun AGENTS.md)
app = Flask(__name__, template_folder="views")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
app.secret_key = "academia-horizonte"  # solo para mensajes flash en local

BASE_DIR = Path(__file__).resolve().parent
RUTA_MAESTRO = BASE_DIR / "insumos" / "Maestro_Estudiantes.xlsx"
RUTA_EVALS = BASE_DIR / "insumos" / "Registro_Evaluaciones.xlsx"

# Estado en memoria de la aplicacion.
# En esta version se inicializa desde los Excel originales de insumos/.
df_maestro = None
df_evals = None
resultados = []
inconsistencias = []


# ----------------------------------------------------------------------
# LADRILLOS: funciones puras de negocio (reutilizadas del analisis)
# ----------------------------------------------------------------------

def leer_maestro_desde_bytes(contenido):
    """Lee el Excel del maestro desde bytes (archivo o disco)."""
    # variable: df (DataFrame de pandas)
    df = pd.read_excel(
        io.BytesIO(contenido),
        sheet_name="Estudiantes",
        dtype={"Identificacion": str},
        engine="openpyxl",
    )
    # limpieza de texto: trim en Identificacion
    df["Identificacion"] = df["Identificacion"].str.strip()
    df["Programa"] = df["Programa"].str.strip()
    df["Nombre_Completo"] = df["Nombre_Completo"].str.strip()
    return df


def leer_evals_desde_bytes(contenido):
    """Lee el Excel de evaluaciones desde bytes."""
    df = pd.read_excel(
        io.BytesIO(contenido),
        sheet_name="Evaluaciones",
        dtype={"Identificacion": str, "Programa": str},
        engine="openpyxl",
    )
    # limpieza de texto
    df["Identificacion"] = df["Identificacion"].str.strip()
    df["Programa"] = df["Programa"].str.strip()
    df["Modulo"] = df["Modulo"].str.strip()
    # conversion numerica (los 0 son valores reales, no nulos)
    df["Nota"] = pd.to_numeric(df["Nota"], errors="coerce")
    df["Asistencia_Pct"] = pd.to_numeric(df["Asistencia_Pct"], errors="coerce")
    return df


def calcular_promedio(valores):
    """Promedio = suma / cantidad. Redondea a 2 decimales (AGENTS.md)."""
    # variable: cantidad (int)
    cantidad = len(valores)
    # condicional: si no hay valores, evitar division por cero
    if cantidad == 0:
        return 0.0
    suma = sum(valores)
    promedio = suma / cantidad
    return round(promedio, 2)


def decidir_certificado(promedio_nota, promedio_asistencia):
    """Reglas de AGENTS.md (los limites INCLUYEN el valor)."""
    # condicional 1: Aprobacion
    if promedio_nota >= 70 and promedio_asistencia >= 80:
        return "Aprobacion"
    # condicional 2: Participacion (nota baja pero asistencia ok)
    elif promedio_asistencia >= 80 and promedio_nota < 70:
        return "Participacion"
    # condicional 3: Sin certificado (asistencia baja)
    elif promedio_asistencia < 80:
        return "Sin certificado"
    # fallback defensivo
    else:
        return "Sin clasificar"


def construir_resultados(maestro, evals):
    """Cruza maestro + evaluaciones por Identificacion + Programa."""
    # variable: lista vacia para acumular filas resultado
    salida = []
    # bucle principal: uno por cada estudiante del maestro
    for _, est in maestro.iterrows():
        ident = est["Identificacion"]          # str
        nombre = est["Nombre_Completo"]       # str
        programa = est["Programa"]            # str

        # filtrar evaluaciones de esta clave
        sub = evals[(evals["Identificacion"] == ident) &
                    (evals["Programa"] == programa)]

        # condicional: si no hay evaluaciones, es inconsistencia
        if sub.empty:
            salida.append({
                "identificacion": ident,
                "nombre": nombre,
                "programa": programa,
                "modulos": 0,
                "promedio_nota": 0.0,
                "promedio_asistencia": 0.0,
                "certificado": "Inconsistencia: sin evaluaciones",
            })
            continue

        # listas de la sub-consulta
        notas = sub["Nota"].tolist()
        asistencias = sub["Asistencia_Pct"].tolist()

        prom_nota = calcular_promedio(notas)
        prom_asist = calcular_promedio(asistencias)
        cert = decidir_certificado(prom_nota, prom_asist)

        salida.append({
            "identificacion": ident,
            "nombre": nombre,
            "programa": programa,
            "modulos": len(sub),
            "promedio_nota": prom_nota,
            "promedio_asistencia": prom_asist,
            "certificado": cert,
        })

    # ordenar por programa y nombre
    salida.sort(key=lambda r: (r["programa"], r["nombre"]))
    return salida


def construir_inconsistencias(maestro, evals):
    """Devuelve las 3 inconsistencias definidas en AGENTS.md."""
    lista = []

    maestro_ids = set(maestro["Identificacion"])
    eval_ids = set(evals["Identificacion"])

    # 1) estudiantes del maestro sin evaluaciones
    for ident in sorted(maestro_ids - eval_ids):
        nombre = maestro.loc[maestro["Identificacion"] == ident, "Nombre_Completo"].iloc[0]
        programa = maestro.loc[maestro["Identificacion"] == ident, "Programa"].iloc[0]
        lista.append({
            "tipo": "Sin evaluaciones",
            "identificacion": ident,
            "detalle": f"{nombre} ({programa}) esta en el maestro pero no tiene evaluaciones.",
        })

    # 2) identificaciones en evaluaciones no presentes en el maestro
    for ident in sorted(eval_ids - maestro_ids):
        sub = evals[evals["Identificacion"] == ident]
        lista.append({
            "tipo": "No esta en el maestro",
            "identificacion": ident,
            "detalle": f"Tiene {len(sub)} evaluacion(es) en {sub['Programa'].iloc[0]} pero no existe en el maestro.",
        })

    # 3) asistencia promedio menor al 50%
    for _, est in maestro.iterrows():
        ident = est["Identificacion"]
        programa = est["Programa"]
        sub = evals[(evals["Identificacion"] == ident) &
                    (evals["Programa"] == programa)]
        if sub.empty:
            continue
        prom_asist = calcular_promedio(sub["Asistencia_Pct"].tolist())
        if prom_asist < 50:
            lista.append({
                "tipo": "Asistencia < 50%",
                "identificacion": ident,
                "detalle": f"{est['Nombre_Completo']} ({programa}) tiene asistencia promedio de {prom_asist}%.",
            })

    return lista


def recalcular(maestro, evals):
    """Actualiza el estado global con nuevos DataFrames."""
    global df_maestro, df_evals, resultados, inconsistencias
    df_maestro = maestro
    df_evals = evals
    resultados = construir_resultados(maestro, evals)
    inconsistencias = construir_inconsistencias(maestro, evals)


def cargar_iniciales():
    """Carga los Excel originales desde insumos/."""
    with open(RUTA_MAESTRO, "rb") as f:
        m = leer_maestro_desde_bytes(f.read())
    with open(RUTA_EVALS, "rb") as f:
        e = leer_evals_desde_bytes(f.read())
    recalcular(m, e)


# ----------------------------------------------------------------------
# RUTAS (controladores delgados)
# ----------------------------------------------------------------------

@app.route("/")
def index():
    # contadores para la pagina
    aprob = sum(1 for r in resultados if r["certificado"] == "Aprobacion")
    part = sum(1 for r in resultados if r["certificado"] == "Participacion")
    sin_cert = sum(1 for r in resultados if r["certificado"] == "Sin certificado")
    programas = sorted({r["programa"] for r in resultados})
    return render_template(
        "index.html",
        resultados=resultados,
        inconsistencias=inconsistencias,
        aprob=aprob,
        part=part,
        sin_cert=sin_cert,
        total=len(resultados),
        programas=programas,
    )


@app.route("/cargar", methods=["GET", "POST"])
def cargar():
    if request.method == "POST":
        f1 = request.files.get("maestro")
        f2 = request.files.get("evaluaciones")
        if not (f1 and f2):
            flash("Debes subir ambos archivos.", "error")
            return redirect(url_for("cargar"))
        try:
            m = leer_maestro_desde_bytes(f1.read())
            e = leer_evals_desde_bytes(f2.read())
            recalcular(m, e)
            flash("Datos cargados correctamente.", "ok")
        except Exception as exc:  # noqa: BLE001
            flash(f"Error al leer los Excel: {exc}", "error")
        return redirect(url_for("index"))
    return render_template("cargar.html")


if __name__ == "__main__":
    cargar_iniciales()
    # app variable + puerto 5000 (AGENTS.md)
    app.run(host="0.0.0.0", port=5000, debug=True)
