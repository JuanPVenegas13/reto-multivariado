import re

import numpy as np
import pandas as pd

_NUM = r"-?\d+(?:\.\d+)?"
RANGO = re.compile(rf"^({_NUM})\s*[-–—]\s*({_NUM})$")
CENSURA = re.compile(rf"^([<>])\s*({_NUM})$")

COLUMNAS_RELEVANTES = ['CodigoProducto', 'Familia', 'Aceite_Base', 'Espesante',
                    'Grado_ISO_VG', 'Viscosidad_a_40°C_cSt', 'Viscosidad_a_100°C_cSt',
                    'Indice_de_Viscosidad', 'Punto_de_Flama_°C', 'Punto_de_Congelamiento_°C',
                    'Peso_Específico', 'Grado_NLGI_Consistencia',
                    'Penetración_de_Cono_a_25°C_0.1mm', 'Estabilidad_Mecánica_%',
                    'Viscosidad_del_Aceite_Base_a_40°C._cSt', 'Punto_de_Gota_°C',
                    'Resistencia_al_Lavado_por_Agua_a_80°C_%', 'Factor_de_Velocidad',
                    'Desgaste_Cuatro_Bolas_mm', 'Punto_de_Soldadura_Cuatro_Bolas_kgf',
                    'Carga_Timken_Ok_lb', 'Corrosión_al_Cobre', 'Registro_NSF',
                    'Temperatura_de_Servicio_°C_min', 'Temperatura_de_Servicio_°C_max',
                    'Color']

COLS_ACEITE = ["Grado_ISO_VG", "Viscosidad_a_40°C_cSt", "Viscosidad_a_100°C_cSt",
               "Indice_de_Viscosidad", "Punto_de_Flama_°C",
               "Punto_de_Congelamiento_°C", "Peso_Específico"]
COLS_GRASA = ["Espesante", "Grado_NLGI_Consistencia", "Penetración_de_Cono_a_25°C_0.1mm",
              "Estabilidad_Mecánica_%", "Viscosidad_del_Aceite_Base_a_40°C._cSt",
              "Punto_de_Gota_°C", "Resistencia_al_Lavado_por_Agua_a_80°C_%",
              "Factor_de_Velocidad"]

COLS_NO_NUMERICAS = ["CodigoProducto", "Familia", "Aceite_Base", "Espesante",
                     "Color", "Corrosión_al_Cobre", "Registro_NSF"]


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
    df["NSF"] = df["Registro_NSF"].notna()  # NaN = no tiene registro
    df["Corrosion_1b"] = df["Corrosión_al_Cobre"].map({"1a": 0.0, "1b": 1.0})  # NaN sí es faltante
    return df.drop(columns=["Registro_NSF", "Corrosión_al_Cobre"])


def anular_cruzados(df: pd.DataFrame) -> pd.DataFrame:
    """Pone NaN en las pruebas que no corresponden a la familia del producto."""
    df = df.copy()
    familia = df["Familia"].str.strip().str.lower()
    df.loc[familia == "aceite", COLS_GRASA] = np.nan
    df.loc[familia == "grasa", COLS_ACEITE] = np.nan
    return df


def seleccionar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Se queda solo con las columnas relevantes; falla si falta alguna."""
    faltantes = [c for c in COLUMNAS_RELEVANTES if c not in df.columns]
    if faltantes:
        raise KeyError(f"Faltan columnas en los datos de entrada: {faltantes}")
    return df[COLUMNAS_RELEVANTES].copy()


def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    """Pipeline completo de limpieza. El orden importa."""
    df = seleccionar_columnas(df)  # primero: el resto asume que solo existen estas columnas
    df = anular_cruzados(df)       # antes de parsear: así los __tipo de lo anulado quedan en None
    cols_num = [c for c in df.columns if c not in COLS_NO_NUMERICAS]
    df = limpiar_numericas(df, cols_num)
    return limpiar_binarias(df)