"""
SUPUESTOS del modelo.

Todo lo de este archivo es un valor provisorio, editable desde la interfaz,
hasta conseguir el dato real. En la app se muestran marcados con (S).
"""

# ---------------------------------------------------------------------------
# Daño por granizada (fracción 0–1), por evento.  SUPUESTO.
# No hay datos reales por evento. Distribución CONTINUA por intervalos: se
# elige el intervalo con su probabilidad y dentro de él el daño es uniforme
# (transformada inversa de una función de distribución lineal por tramos).
# El primer "intervalo" es el punto 0: un día con granizo en la estación no
# siempre golpea la finca.
#
# Los puntos medios de los intervalos (0, 5, 15, 30, 50, 70, 90 %) son los
# valores de la tabla discreta de la v1, así que la media se conserva.
# v2: se pasó a continuo porque la tabla discreta tenía un valor exacto en 50 %,
# justo en el umbral del Fondo, y eso distorsionaba la comparación.
# Calibración: pérdida media anual ≈ 13 %, dentro del rango DACC Sur.
# ---------------------------------------------------------------------------
TABLA_DANIO_DESDE = [0.00, 0.00, 0.10, 0.20, 0.40, 0.60, 0.80]
TABLA_DANIO_HASTA = [0.00, 0.10, 0.20, 0.40, 0.60, 0.80, 1.00]
TABLA_DANIO_PROBABILIDADES = [0.52, 0.20, 0.12, 0.07, 0.05, 0.025, 0.015]

# Factor de severidad (SUPUESTO, para sensibilidad): multiplica la probabilidad
# de los intervalos de daño alto (40–60, 60–80, 80–100 %) y renormaliza el resto.
# 1 = la tabla de arriba.
FACTOR_SEVERIDAD = 1.0

# Superficie cultivada total del Oasis Sur (todos los cultivos), para pasar
# las ha dañadas de la DACC a una tasa.  SUPUESTO (dato pendiente).
SUPERFICIE_CULTIVADA_SUR_HA = 60_000

# ---------------------------------------------------------------------------
# Economía.  SUPUESTOS (datos pendientes).
# Todo el modelo trabaja en pesos constantes (sin inflación).
# ---------------------------------------------------------------------------
PRECIO_UVA_POR_KG = 400               # $/kg en San Rafael
COSTO_PRODUCCION_POR_HA = 2_200_000   # $/ha/año
TIPO_DE_CAMBIO = 1450                 # $/USD
TASA_DESCUENTO = 0.05                 # tasa anual real para el VAN
# Costo fijo por finca y por año, independiente de las hectáreas (administración,
# maquinaria, etc.). Es igual para las tres alternativas. Por defecto 0, así todo
# el modelo es proporcional a las hectáreas.
COSTO_FIJO_FINCA = 0

# ---------------------------------------------------------------------------
# Fondo Compensador.
# Forma de la compensación cuando se cumple la condición de pago:
#   "proporcional": compensación/ha × daño del año (por defecto)
#   "fijo":         compensación/ha completa
# Condición de pago. Las fuentes se contradicen:
#   - Preguntas frecuentes oficiales (2024): daño "del 50 % o más"  -> ">="
#   - Nota de prensa (11/08/2025): daños que "superen el 50 %"      -> ">"
# Por defecto se usa la fuente oficial (">=").
# ---------------------------------------------------------------------------
FCA_MODO_COMPENSACION = "proporcional"
FCA_CONDICION_PAGO = ">="

# ---------------------------------------------------------------------------
# Malla antigranizo.
# ---------------------------------------------------------------------------
MALLA_EFICACIA = 0.90          # reduce el 90 % del daño de cada granizada (SUPUESTO)
MALLA_COSTO_USD_HA = 4250      # punto medio del rango real 4.000–4.500
MALLA_VIDA_UTIL = 15           # dentro del rango real 12–20 años
# Forma de pago (las tres tienen el mismo VAN si la tasa del crédito es igual
# a la tasa de descuento):
#   "amortizado": costo anual equivalente (anualidad a la tasa de descuento
#                 durante la vida útil), cada año. Por defecto.
#   "contado":    se paga entera al instalarla y al reponerla; al final del
#                 horizonte se descuenta el valor residual.
#   "financiado": cuotas (sistema francés) al instalarla y al reponerla.
MALLA_MODO_PAGO = "amortizado"
MALLA_TASA_ANUAL = 0.08        # tasa real anual del crédito (SUPUESTO)
MALLA_CUOTAS = 5               # cantidad de cuotas anuales (SUPUESTO)

# ---------------------------------------------------------------------------
# Estado climático del primer año simulado:
#   "estacionaria": sorteado con la distribución estacionaria de la cadena
#   "G" o "S":      fijo
# ---------------------------------------------------------------------------
ESTADO_INICIAL = "estacionaria"
