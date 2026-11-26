"""Limpieza de la base de productos de lubricantes.

Punto de entrada: `limpiar(df)`. Recibe la base cruda y regresa la base limpia.
"""
import re

import numpy as np
import pandas as pd

# --- Columnas ----------------------------------------------------------------

# Nombre original -> nombre estandarizado. Las llaves definen además qué
# columnas son relevantes: cualquier otra columna de la base cruda se descarta.
RENOMBRES = {
    "CodigoProducto": "codigo",
    "Familia": "familia",
    "Aceite_Base": "aceite_base",
    "Espesante": "espesante",
    "Grado_ISO_VG": "grado_iso_vg",
    "Viscosidad_a_40°C_cSt": "visc_40c_cst",
    "Viscosidad_a_100°C_cSt": "visc_100c_cst",
    "Indice_de_Viscosidad": "indice_viscosidad",
    "Punto_de_Flama_°C": "punto_flama_c",
    "Punto_de_Congelamiento_°C": "punto_congelamiento_c",
    "Peso_Específico": "peso_especifico",
    "Grado_NLGI_Consistencia": "grado_nlgi",
    "Penetración_de_Cono_a_25°C_0.1mm": "penetracion_cono_25c",
    "Estabilidad_Mecánica_%": "estabilidad_mecanica_pct",
    "Viscosidad_del_Aceite_Base_a_40°C._cSt": "visc_aceite_base_40c_cst",
    "Punto_de_Gota_°C": "punto_gota_c",
    "Resistencia_al_Lavado_por_Agua_a_80°C_%": "lavado_agua_80c_pct",
    "Factor_de_Velocidad": "factor_velocidad",
    "Desgaste_Cuatro_Bolas_mm": "desgaste_4bolas_mm",
    "Punto_de_Soldadura_Cuatro_Bolas_kgf": "soldadura_4bolas_kgf",
    "Carga_Timken_Ok_lb": "carga_timken_lb",
    "Corrosión_al_Cobre": "corrosion_cobre",
    "Registro_NSF": "registro_nsf",
    "Temperatura_de_Servicio_°C_min": "temp_servicio_min_c",
    "Temperatura_de_Servicio_°C_max": "temp_servicio_max_c",
    "Color": "color",
}
COLUMNAS_RELEVANTES = list(RENOMBRES)  # nombres originales, por si se necesitan en un notebook

COLS_ACEITE = ["grado_iso_vg", "visc_40c_cst", "visc_100c_cst", "indice_viscosidad",
               "punto_flama_c", "punto_congelamiento_c", "peso_especifico"]
COLS_GRASA = ["espesante", "grado_nlgi", "penetracion_cono_25c", "estabilidad_mecanica_pct",
              "visc_aceite_base_40c_cst", "punto_gota_c", "lavado_agua_80c_pct",
              "factor_velocidad"]

COLS_CATEGORICAS = ["familia", "aceite_base", "espesante", "color"]
COLS_NO_NUMERICAS = ["codigo", *COLS_CATEGORICAS, "corrosion_cobre", "registro_nsf"]

# Variantes de color que significan lo mismo (ya en minúsculas)
EQUIVALENCIAS_COLOR = {
    "roja": "rojo",
    "amarillo ligero": "amarillo claro",
    "ambar ligero": "ambar claro",
    "ligero verde": "verde claro",
}

# --- Parseo de valores numéricos ---------------------------------------------

_NUM = r"-?\d+(?:\.\d+)?"
RANGO = re.compile(rf"^({_NUM})\s*[-–—]\s*({_NUM})$")
CENSURA = re.compile(rf"^([<>])\s*({_NUM})$")


def parsear_valor(x) -> tuple[float, str | None]:
    """Convierte una celda a (valor, tipo): exacto | rango | mayor | menor | invalido."""
    if pd.isna(x):
        return np.nan, None
    s = str(x).strip()
    try:
        return float(s), "exacto"
    except ValueError:
        pass
    if m := RANGO.match(s):
        a, b = map(float, m.groups())
        return (a + b) / 2, "rango"
    if m := CENSURA.match(s):
        return float(m.group(2)), "mayor" if m.group(1) == ">" else "menor"
    return np.nan, "invalido"


# --- Pasos del pipeline --------------------------------------------------------

def seleccionar_y_renombrar(df: pd.DataFrame) -> pd.DataFrame:
    """Se queda solo con las columnas relevantes y las renombra; falla si falta alguna."""
    faltantes = [c for c in RENOMBRES if c not in df.columns]
    if faltantes:
        raise KeyError(f"Faltan columnas en los datos de entrada: {faltantes}")
    return df[list(RENOMBRES)].rename(columns=RENOMBRES)


def homologar_categorias(df: pd.DataFrame) -> pd.DataFrame:
    """Texto categórico en minúsculas, sin espacios sobrantes y con variantes unificadas."""
    df = df.copy()
    for c in COLS_CATEGORICAS:
        df[c] = df[c].str.strip().str.replace(r"\s+", " ", regex=True).str.lower()
    df["color"] = df["color"].replace(EQUIVALENCIAS_COLOR)
    return df


def anular_cruzados(df: pd.DataFrame) -> pd.DataFrame:
    """Pone NaN en las pruebas que no corresponden a la familia del producto."""
    df = df.copy()
    df.loc[df["familia"] == "aceite", COLS_GRASA] = np.nan
    df.loc[df["familia"] == "grasa", COLS_ACEITE] = np.nan
    return df


def limpiar_numericas(df: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    df = df.copy()
    for col in columnas:
        pares = pd.DataFrame(df[col].map(parsear_valor).tolist(),
                             index=df.index, columns=["valor", "tipo"])
        df[col] = pares["valor"].astype(float)
        df[f"{col}__tipo"] = pares["tipo"]
        n_inv = (pares["tipo"] == "invalido").sum()
        if n_inv:
            print(f"[aviso] {col}: {n_inv} valor(es) inválido(s) → NaN")
    return df


def limpiar_binarias(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["nsf"] = df["registro_nsf"].notna()  # NaN = no tiene registro
    corrosion = df["corrosion_cobre"].str.strip().str.lower()
    df["corrosion_1b"] = corrosion.map({"1a": 0.0, "1b": 1.0})  # NaN sí es faltante
    return df.drop(columns=["registro_nsf", "corrosion_cobre"])


def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    """Pipeline completo de limpieza. El orden importa."""
    df = seleccionar_y_renombrar(df)  # primero: todo lo demás usa los nombres nuevos
    df = homologar_categorias(df)     # antes de anular: anular_cruzados compara "familia" en minúsculas
    df = anular_cruzados(df)          # antes de parsear: así los __tipo de lo anulado quedan en None
    cols_num = [c for c in df.columns if c not in COLS_NO_NUMERICAS]
    df = limpiar_numericas(df, cols_num)
    return limpiar_binarias(df)