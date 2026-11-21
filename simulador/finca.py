"""
Módulo 5 – Simulación de la finca año a año (TP4).

Primero se genera un ESCENARIO (clima, daños y rendimientos de cada año) y
después se evalúan las tres alternativas sobre ese mismo escenario, así las
tres enfrentan exactamente los mismos años de granizo.

Resultado del año (pesos constantes):
    ingreso       = ha × rendimiento × precio × (1 − daño del año)
    sin protección = ingreso − costo de producción
    Fondo          = ingreso − costo de producción − aporte + compensación
    malla          = ingreso con daño reducido − costo de producción − costo de la malla
"""

from dataclasses import dataclass

import numpy as np

from .clima import CadenaMarkov, TablaEmpirica, tabla_dias_condicional
from .danio import combinar_danios, danios_con_malla
from . import datos_reales as R

ALTERNATIVAS = ("sin_proteccion", "fondo", "malla")
NOMBRES = {
    "sin_proteccion": "Sin protección",
    "fondo": "Fondo Compensador",
    "malla": "Malla antigranizo",
}


@dataclass
class Escenario:
    """Un futuro posible de 'anios' años (una réplica)."""
    estados: list          # 'G' / 'S'
    dias: list             # granizadas del año
    eventos: list          # lista de daños por evento, por año
    danio: list            # daño combinado del año, sin malla
    danio_malla: list      # daño combinado del año, con malla
    rendimiento: list      # kg/ha sin daño


class ModeloClima:
    """Arma las tablas una sola vez y genera escenarios con un generador dado."""

    def __init__(self, p, tabla_dias_real=None):
        self.p = p
        if tabla_dias_real is None:
            valores, _, probs = R.tabla_dias_granizo()
        else:
            valores, probs = tabla_dias_real
        self.cadena = CadenaMarkov(p.p_s_a_g, p.p_g_a_s)
        self.dias_si_g = tabla_dias_condicional(valores, probs)
        self.tabla_danio = TablaEmpirica(p.danio_valores, p.danio_probabilidades)

    def generar_escenario(self, gen):
        """Orden fijo de sorteos por año: estado, días, daño de cada evento, rendimiento."""
        p = self.p
        estados, dias, eventos, danio, danio_m, rend = [], [], [], [], [], []
        estado = None
        for anio in range(p.anios):
            u = gen.siguiente()
            if anio == 0:
                estado = self.cadena.estado_inicial(u, p.estado_inicial)
            else:
                estado = self.cadena.siguiente(estado, u)
            n = self.dias_si_g.inversa(gen.siguiente()) if estado == "G" else 0
            ev = [self.tabla_danio.inversa(gen.siguiente()) for _ in range(n)]
            estados.append(estado)
            dias.append(n)
            eventos.append(ev)
            danio.append(combinar_danios(ev))
            danio_m.append(combinar_danios(danios_con_malla(ev, p.malla_eficacia)))
            rend.append(gen.uniforme(p.rendimiento_min, p.rendimiento_max))
        return Escenario(estados, dias, eventos, danio, danio_m, rend)


# ---------------------------------------------------------------------------
# Economía (funciones puras; aceptan escalares o arreglos de numpy)
# ---------------------------------------------------------------------------
def ingreso(danio, rendimiento, p):
    return p.hectareas * rendimiento * p.precio_uva * (1 - np.asarray(danio))


def compensacion_fondo(danio, p):
    """Paga solo si el daño del año SUPERA el umbral (50 %)."""
    danio = np.asarray(danio, dtype=float)
    base = p.fca_compensacion_ha * p.hectareas
    monto = base * danio if p.fca_modo == "proporcional" else base * np.ones_like(danio)
    return np.where(danio > p.fca_umbral, monto, 0.0)


def costo_malla_por_anio(p):
    """Costo de la malla imputado a cada año del horizonte (pesos).

    amortizado: costo / vida útil cada año.
    contado:    pago completo al instalar y al reponer; al final del horizonte
                se descuenta el valor residual (vida que le queda a la malla).
    financiado: cuotas de sistema francés al instalar y al reponer; al final se
                suma la deuda pendiente y se descuenta el valor residual.
    """
    n_anios = p.anios
    costo_total = p.malla_costo_usd_ha * p.tipo_cambio * p.hectareas
    vida = int(p.malla_vida_util)
    costos = np.zeros(n_anios)

    if p.malla_modo_pago == "amortizado":
        costos[:] = costo_total / vida
        return costos

    compras = list(range(0, n_anios, vida))       # años en que se instala/repone
    ultima = compras[-1]
    anios_usados = n_anios - ultima
    valor_residual = costo_total * max(vida - anios_usados, 0) / vida

    if p.malla_modo_pago == "contado":
        for k in compras:
            costos[k] += costo_total
    else:  # financiado
        i, n = p.malla_tasa_anual, int(p.malla_cuotas)
        cuota = costo_total / n if i == 0 else costo_total * i / (1 - (1 + i) ** -n)
        for k in compras:
            for j in range(n):
                anio = k + j
                if anio < n_anios:
                    costos[anio] += cuota
                else:
                    # cuota que vence después del horizonte: se trae al último año
                    costos[-1] += cuota / (1 + i) ** (anio - (n_anios - 1))
    costos[-1] -= valor_residual
    return costos


def evaluar(danio, danio_malla, rendimiento, p, costo_malla=None):
    """Resultado anual de las tres alternativas.

    danio, danio_malla y rendimiento pueden ser vectores (un año por elemento)
    o matrices (réplicas × años). Devuelve un dict alternativa -> arreglo.
    """
    danio = np.asarray(danio, dtype=float)
    danio_malla = np.asarray(danio_malla, dtype=float)
    rendimiento = np.asarray(rendimiento, dtype=float)
    if costo_malla is None:
        costo_malla = costo_malla_por_anio(p)
    costo_prod = p.costo_produccion_ha * p.hectareas
    sin = ingreso(danio, rendimiento, p) - costo_prod
    fondo = sin - p.fca_aporte_ha * p.hectareas + compensacion_fondo(danio, p)
    malla = ingreso(danio_malla, rendimiento, p) - costo_prod - costo_malla
    return {"sin_proteccion": sin, "fondo": fondo, "malla": malla}
