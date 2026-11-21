"""
Parámetros de una corrida. Junta los datos reales y los supuestos en un solo
objeto que la interfaz puede editar. Los valores por defecto salen de
datos_reales.py y supuestos.py.
"""

from dataclasses import dataclass, field

from . import datos_reales as R
from . import supuestos as S
from .generador import A_DEFECTO, C_DEFECTO, M_DEFECTO


@dataclass
class Parametros:
    # Simulación
    replicas: int = 10_000
    anios: int = 20
    semilla: int = 12345
    lcg_a: int = A_DEFECTO
    lcg_c: int = C_DEFECTO
    lcg_m: int = M_DEFECTO

    # Finca (INV) – real
    hectareas: float = R.HECTAREAS_FINCA
    rendimiento_min: float = R.RENDIMIENTO_MIN_KG_HA
    rendimiento_max: float = R.RENDIMIENTO_MAX_KG_HA

    # Clima – real
    p_s_a_g: float = R.MARKOV_P_S_A_G
    p_g_a_s: float = R.MARKOV_P_G_A_S
    estado_inicial: str = S.ESTADO_INICIAL                     # SUPUESTO
    # Escenario: multiplica la cantidad de granizadas de cada año (1 = datos reales)
    frecuencia_mult: float = 1.0

    # Daño por evento – SUPUESTO (intervalos)
    danio_desde: list = field(default_factory=lambda: list(S.TABLA_DANIO_DESDE))
    danio_hasta: list = field(default_factory=lambda: list(S.TABLA_DANIO_HASTA))
    danio_probabilidades: list = field(default_factory=lambda: list(S.TABLA_DANIO_PROBABILIDADES))
    severidad: float = S.FACTOR_SEVERIDAD                      # SUPUESTO

    # Economía – SUPUESTOS
    precio_uva: float = S.PRECIO_UVA_POR_KG
    costo_produccion_ha: float = S.COSTO_PRODUCCION_POR_HA
    tipo_cambio: float = S.TIPO_DE_CAMBIO
    tasa_descuento: float = S.TASA_DESCUENTO
    costo_fijo_finca: float = S.COSTO_FIJO_FINCA

    # Fondo Compensador – real (salvo modo y condición)
    fca_aporte_ha: float = R.FCA_APORTE_POR_HA
    fca_compensacion_ha: float = R.FCA_COMPENSACION_POR_HA
    fca_umbral: float = R.FCA_UMBRAL_DANIO
    fca_modo: str = S.FCA_MODO_COMPENSACION                    # SUPUESTO
    fca_condicion: str = S.FCA_CONDICION_PAGO                  # SUPUESTO
    fca_max_hectareas: float = R.FCA_MAX_HECTAREAS             # por encima no se puede adherir

    # Malla – costo y vida dentro del rango real; eficacia y pago SUPUESTOS
    malla_costo_usd_ha: float = S.MALLA_COSTO_USD_HA
    malla_vida_util: int = S.MALLA_VIDA_UTIL
    malla_eficacia: float = S.MALLA_EFICACIA
    malla_modo_pago: str = S.MALLA_MODO_PAGO
    malla_tasa_anual: float = S.MALLA_TASA_ANUAL
    malla_cuotas: int = S.MALLA_CUOTAS

    # Referencia DACC – SUPUESTO
    superficie_cultivada_sur: float = S.SUPERFICIE_CULTIVADA_SUR_HA

    # Sensibilidad (pestaña 4)
    sens_replicas: int = 2000
    sens_precio_min: float = 200
    sens_precio_max: float = 1000
    sens_precio_paso: float = 50
    sens_sev_min: float = 0.25
    sens_sev_max: float = 3.0
    sens_sev_paso: float = 0.25
    sens_ha_max: int = 60
    conv_replicas_max: int = 50_000   # convergencia (pestaña 5)
    criterio_p5_minimo: float = 0.0   # "mejor" = mayor VAN medio con P5 del VAN > este valor

    def validar(self):
        errores = []
        if self.replicas < 1 or self.anios < 1 or self.sens_replicas < 1:
            errores.append("Réplicas y años deben ser al menos 1.")
        if self.hectareas <= 0:
            errores.append("Las hectáreas deben ser positivas.")
        if self.rendimiento_min > self.rendimiento_max:
            errores.append("El rendimiento mínimo supera al máximo.")
        for nombre in ("p_s_a_g", "p_g_a_s", "malla_eficacia", "fca_umbral"):
            if not 0 <= getattr(self, nombre) <= 1:
                errores.append(f"{nombre} debe estar entre 0 y 1.")
        if self.severidad < 0:
            errores.append("El factor de severidad no puede ser negativo.")
        if self.frecuencia_mult < 0:
            errores.append("El multiplicador de frecuencia no puede ser negativo.")
        if self.tasa_descuento <= -1 or self.malla_tasa_anual < 0:
            errores.append("Tasas inválidas.")
        n = len(self.danio_probabilidades)
        if len(self.danio_desde) != n or len(self.danio_hasta) != n:
            errores.append("La tabla de daño tiene columnas de distinto largo.")
        if abs(sum(self.danio_probabilidades) - 1) > 1e-6:
            errores.append(
                f"Las probabilidades de daño suman {sum(self.danio_probabilidades):.4f}, deben sumar 1."
            )
        if any(not 0 <= a <= b <= 1 for a, b in zip(self.danio_desde, self.danio_hasta)):
            errores.append("Cada intervalo de daño debe cumplir 0 % <= desde <= hasta <= 100 %.")
        if self.fca_modo not in ("proporcional", "fijo"):
            errores.append("Modo del Fondo: 'proporcional' o 'fijo'.")
        if self.fca_condicion not in (">=", ">"):
            errores.append("Condición de pago del Fondo: '>=' o '>'.")
        if self.malla_modo_pago not in ("amortizado", "contado", "financiado"):
            errores.append("Pago de la malla: 'amortizado', 'contado' o 'financiado'.")
        if self.malla_vida_util < 1 or self.malla_cuotas < 1:
            errores.append("Vida útil y cuotas de la malla deben ser al menos 1.")
        if self.estado_inicial not in ("estacionaria", "G", "S"):
            errores.append("Estado inicial: 'estacionaria', 'G' o 'S'.")
        if errores:
            raise ValueError("\n".join(errores))
