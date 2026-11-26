"""Genera data/processed/productos_limpios.parquet a partir de los datos crudos."""
from pathlib import Path

import pandas as pd

from reto_multivariado.limpieza import limpiar

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "data" / "raw" / "DATOS_TEC.xlsx"
SALIDA = RAIZ / "data" / "processed" / "productos_limpios.parquet"


def main() -> None:
    df = limpiar(pd.read_excel(ENTRADA))
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(SALIDA, index=False)
    print(f"{len(df)} productos → {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()