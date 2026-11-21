"""
SUPUESTOS del modelo.

Todo lo de este archivo es un valor provisorio, editable desde la interfaz,
hasta conseguir el dato real. En la app se muestran marcados con (S).
"""

# ---------------------------------------------------------------------------
# Daño por granizada (%), por evento.  SUPUESTO.
# No hay datos reales por evento. La tabla está calibrada para que la pérdida
# media anual simulada quede dentro del rango de referencia de la DACC para el
# Oasis Sur (ver referencia_dacc() en danio.py). Incluye una probabilidad alta
# de daño 0: un día con granizo en la estación no siempre golpea la finca.
# ---------------------------------------------------------------------------
TABLA_DANIO_VALORES = [0.00, 0.05, 0.15, 0.30, 0.50, 0.70, 0.90]
TABLA_DANIO_PROBABILIDADES = [0.52, 0.20, 0.12, 0.07, 0.05, 0.025, 0.015]
# Con esta tabla: daño medio por evento ≈ 10,6 %, pérdida media anual ≈ 13 %
# (el centro del rango DACC Sur 8–18 % con 60.000 ha cultivadas) y
# probabilidad de que un año supere el 50 % de daño ≈ 9 %.

# Superficie cultivada total del Oasis Sur (todos los cultivos), para pasar
# las ha dañadas de la DACC a una tasa.  SUPUESTO (dato pendiente).
SUPERFICIE_CULTIVADA_SUR_HA = 60_000

# ---------------------------------------------------------------------------
# Economía.  SUPUESTOS (datos pendientes).
# Todo el modelo trabaja en pesos constantes, sin inflación.
# ---------------------------------------------------------------------------
PRECIO_UVA_POR_KG = 400               # $/kg en San Rafael
COSTO_PRODUCCION_POR_HA = 2_200_000   # $/ha/año
TIPO_DE_CAMBIO = 1450                 # $/USD

# ---------------------------------------------------------------------------
# Fondo Compensador: forma de la compensación cuando el daño supera el umbral.
#   "proporcional": compensación/ha × daño del año (por defecto)
#   "fijo":         compensación/ha completa
# ---------------------------------------------------------------------------
FCA_MODO_COMPENSACION = "proporcional"

# ---------------------------------------------------------------------------
# Malla antigranizo.
# ---------------------------------------------------------------------------
MALLA_EFICACIA = 0.90          # reduce el 90 % del daño de cada granizada (SUPUESTO)
MALLA_COSTO_USD_HA = 4250      # punto medio del rango real 4.000–4.500
MALLA_VIDA_UTIL = 15           # dentro del rango real 12–20 años
# Forma de pago:
#   "amortizado": costo / vida útil cada año (por defecto)
#   "contado":    se paga entera al instalarla y al reponerla
#   "financiado": cuotas (sistema francés) al instalarla y al reponerla
MALLA_MODO_PAGO = "amortizado"
MALLA_TASA_ANUAL = 0.08        # tasa real anual del crédito (SUPUESTO)
MALLA_CUOTAS = 5               # cantidad de cuotas anuales (SUPUESTO)

# ---------------------------------------------------------------------------
# Estado climático del primer año simulado:
#   "estacionaria": sorteado con la distribución estacionaria de la cadena
#   "G" o "S":      fijo
# ---------------------------------------------------------------------------
ESTADO_INICIAL = "estacionaria"
