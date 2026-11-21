"""
DATOS REALES del proyecto, con su fuente.

Todo lo que está en este archivo viene del relevamiento documentado en
"Proyecto granizo - datos reales y fuentes.md". No poner acá valores supuestos:
esos van en supuestos.py.
"""

import csv
import os
from collections import Counter

# ---------------------------------------------------------------------------
# 1. Granizo – estación San Rafael Aero (OMM 87509), 1974–2024
#    Fuente: tutiempo.net (reportes SYNOP, código GR). Años sin datos:
#    1982, 1996, 2002, 2005.
# ---------------------------------------------------------------------------
RUTA_CSV_GRANIZO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "granizo_san_rafael_aero_1974_2024.csv",
)

# Matriz de transición de la cadena de Markov año con granizo (G) / sin
# granizo (S), calculada con los pares de años consecutivos válidos de la serie.
MARKOV_P_S_A_G = 0.20   # S -> G   (S -> S = 0,80)
MARKOV_P_G_A_S = 0.11   # G -> S   (G -> G = 0,89)
# Distribución estacionaria documentada: S = 0,36, G = 0,64.


def cargar_serie_granizo(ruta=RUTA_CSV_GRANIZO):
    """Devuelve la serie como lista de (anio, dias_granizo); dias = None si falta."""
    serie = []
    with open(ruta, encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            dias = fila["dias_granizo"].strip()
            serie.append((int(fila["anio"]), int(dias) if dias else None))
    return serie


def tabla_dias_granizo(ruta=RUTA_CSV_GRANIZO):
    """Tabla empírica de días con granizo por año (solo años válidos).

    Devuelve (valores, frecuencias_absolutas, probabilidades). Con la serie real:
    0:16, 1:13, 2:9, 3:5, 4:2, 5:1, 7:1  (47 años, media 1,40, varianza 2,33).
    """
    dias = [d for _, d in cargar_serie_granizo(ruta) if d is not None]
    conteo = Counter(dias)
    valores = sorted(conteo)
    absolutas = [conteo[v] for v in valores]
    n = len(dias)
    return valores, absolutas, [a / n for a in absolutas]


# ---------------------------------------------------------------------------
# 2. Finca tipo – INV, Informe Área Sur (2016)
# ---------------------------------------------------------------------------
HECTAREAS_FINCA = 5.3          # tamaño medio del viñedo en San Rafael
RENDIMIENTO_MIN_KG_HA = 7100   # 71 qq/ha
RENDIMIENTO_MAX_KG_HA = 7600   # 76 qq/ha

# ---------------------------------------------------------------------------
# 3. Fondo Compensador Agrícola 2025-26 – cobertura Específica (granizo),
#    Oasis Sur. Fuente: Gobierno de Mendoza, 11/08/2025.
# ---------------------------------------------------------------------------
FCA_APORTE_POR_HA = 51_000           # $/ha/año
FCA_COMPENSACION_POR_HA = 2_000_000  # $/ha con daño total
FCA_UMBRAL_DANIO = 0.50              # umbral de daño del año para cobrar
# Si el umbral se cumple con ">=" o con ">" es un SUPUESTO: las fuentes se
# contradicen (ver FCA_CONDICION_PAGO en supuestos.py).
FCA_MAX_HECTAREAS = 30

# ---------------------------------------------------------------------------
# 4. Malla antigranizo – MDZ (2024)
# ---------------------------------------------------------------------------
MALLA_COSTO_USD_HA_MIN = 4000
MALLA_COSTO_USD_HA_MAX = 4500
MALLA_VIDA_UTIL_MIN = 12
MALLA_VIDA_UTIL_MAX = 20

# ---------------------------------------------------------------------------
# 5. Daño en la zona – DACC (referencia para calibrar la tabla de daño)
# ---------------------------------------------------------------------------
DACC_HA_100_PROVINCIA = 15_841     # ha/año "llevadas al 100 %", 2005/06–2019/20
DACC_HA_SUR_SIN_LUCHA = 11_000     # ha/año estimadas en Oasis Sur sin lucha antigranizo
DACC_HA_SUR_CON_LUCHA = 5_000      # ha/año estimadas en Oasis Sur con lucha antigranizo

FUENTES = {
    "granizo": "tutiempo.net – San Rafael Aero 87509 (SYNOP), 1974–2024",
    "finca": "INV – Informe Área Sur (2016)",
    "fca": "Gobierno de Mendoza – Fondo Compensador Agrícola 2025-26 (11/08/2025)",
    "malla": "MDZ – Aviones vs malla antigranizo (01/07/2024)",
    "dacc": "DACC – Resumen actuaciones LAG 2020-21; Sitio Andino (2026)",
}
