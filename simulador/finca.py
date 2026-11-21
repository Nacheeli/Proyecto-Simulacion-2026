"""
Módulo 5 – Simulación de la finca año a año (TP4).

Primero se genera un ESCENARIO (clima, daños y rendimientos de cada año) y
después se evalúan las tres alternativas sobre ese mismo escenario, así las
tres enfrentan exactamente los mismos años de granizo.

Resultado del año (pesos constantes, flujo de caja del año):
    ingreso        = ha × rendimiento × precio × (1 − daño del año)
    sin protección = ingreso − costo de producción
    Fondo          = ingreso − costo de producción − aporte + compensación
    malla          = ingreso con daño reducido − costo de producción − pagos de la malla
    costo de producción = costo/ha × ha + costo fijo por finca (por defecto 0)
El Fondo no está disponible por encima de 30 ha (límite real).

VAN: los resultados operativos se descuentan como flujos de fin de año
(año t -> (1+i)^t). La compra de la malla al contado ocurre al INICIO del año
(año t -> (1+i)^(t-1)).
"""

import math
from dataclasses import dataclass

import numpy as np

from .clima import CadenaMarkov, tabla_dias_condicional
from .danio import TablaDanio, aplicar_severidad, combinar_danios, danios_con_malla
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
        probs = aplicar_severidad(p.danio_desde, p.danio_probabilidades, p.severidad)
        self.tabla_danio = TablaDanio(p.danio_desde, p.danio_hasta, probs)

    def _aplicar_multiplicador(self, n, gen):
        """Escala la cantidad de granizadas con redondeo estocástico: E[n'] = mult · n.

        Con mult = 1 no consume números aleatorios (los resultados no cambian).
        """
        m = self.p.frecuencia_mult
        if m == 1 or n == 0:
            return n
        x = n * m
        entero = math.floor(x)
        fraccion = x - entero
        if fraccion > 0 and gen.siguiente() < fraccion:
            entero += 1
        return entero

    def generar_escenario(self, gen):
        """Orden fijo de sorteos por año: estado, días, (multiplicador), daño de cada evento, rendimiento."""
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
            n = self._aplicar_multiplicador(n, gen)
            ev = [self.tabla_danio.inversa(gen.siguiente()) for _ in range(n)]
            estados.append(estado)
            dias.append(n)
            eventos.append(ev)
            danio.append(combinar_danios(ev))
            danio_m.append(combinar_danios(danios_con_malla(ev, p.malla_eficacia)))
            rend.append(gen.uniforme(p.rendimiento_min, p.rendimiento_max))
        return Escenario(estados, dias, eventos, danio, danio_m, rend)


# ---------------------------------------------------------------------------
# Matemática financiera
# ---------------------------------------------------------------------------
def factor_anualidad(n, i):
    """Valor actual de 1 $ por año durante n años (pagos a fin de año)."""
    if n <= 0:
        return 0.0
    return n if i == 0 else (1 - (1 + i) ** -n) / i


def costo_anual_equivalente(valor, n, i):
    """Cuota constante de n años cuyo valor actual a la tasa i es 'valor'."""
    return valor / factor_anualidad(n, i)


def van(flujos, tasa, inversion_inicio=None):
    """Valor actual neto.

    flujos: resultados anuales (último eje = años), ya incluyen las inversiones.
    inversion_inicio: parte de cada año pagada al INICIO del año (se descuenta un
    período menos). Devuelve un escalar o un arreglo sin el eje de años.
    """
    flujos = np.asarray(flujos, dtype=float)
    T = flujos.shape[-1]
    desc_fin = (1 + tasa) ** -np.arange(1, T + 1)
    resultado = flujos @ desc_fin
    if inversion_inicio is not None:
        inv = np.asarray(inversion_inicio, dtype=float)
        desc_ini = (1 + tasa) ** -np.arange(0, T)
        resultado = resultado + inv @ desc_fin - inv @ desc_ini
    return resultado


# ---------------------------------------------------------------------------
# Economía (funciones puras; aceptan escalares o arreglos de numpy)
# ---------------------------------------------------------------------------
def ingreso(danio, rendimiento, p):
    return p.hectareas * rendimiento * p.precio_uva * (1 - np.asarray(danio))


def fondo_paga(danio, p):
    """True si el daño del año cumple la condición de pago (>= o > umbral)."""
    danio = np.asarray(danio, dtype=float)
    return danio >= p.fca_umbral if p.fca_condicion == ">=" else danio > p.fca_umbral


def fondo_disponible(p):
    """El Fondo solo admite productores de hasta 30 ha cultivadas (dato real)."""
    return p.hectareas <= p.fca_max_hectareas


def compensacion_fondo(danio, p):
    danio = np.asarray(danio, dtype=float)
    if not fondo_disponible(p):
        return np.zeros_like(danio)
    base = p.fca_compensacion_ha * p.hectareas
    monto = base * danio if p.fca_modo == "proporcional" else base * np.ones_like(danio)
    return np.where(fondo_paga(danio, p), monto, 0.0)


def costo_malla_por_anio(p):
    """Pagos de la malla en cada año del horizonte (pesos).

    Devuelve (inicio, fin): lo que se paga al inicio y al final de cada año.
    El resultado del año incluye ambos; el VAN descuenta 'inicio' un período menos.
    Con i = tasa de descuento y C = costo de una malla:

    amortizado: costo anual equivalente C / a(vida, i) a fin de cada año.
    contado:    C al inicio del año de instalación y de cada reposición; al final
                del horizonte se descuenta el valor residual = CAE × a(vida restante, i).
    financiado: sistema francés a la tasa del crédito, primera cuota a fin del año
                de compra; las cuotas que vencen después del horizonte se suman al
                último año (deuda pendiente) y se descuenta el mismo valor residual.

    Si la tasa del crédito es igual a la de descuento, las tres tienen el mismo VAN.
    """
    T = p.anios
    i = p.tasa_descuento
    C = p.malla_costo_usd_ha * p.tipo_cambio * p.hectareas
    vida = int(p.malla_vida_util)
    cae = costo_anual_equivalente(C, vida, i)
    inicio, fin = np.zeros(T), np.zeros(T)

    if p.malla_modo_pago == "amortizado":
        fin[:] = cae
        return inicio, fin

    compras = list(range(0, T, vida))          # años (0 = primero) de instalación/reposición
    restante = vida - (T - compras[-1])
    valor_residual = cae * factor_anualidad(restante, i)

    if p.malla_modo_pago == "contado":
        for k in compras:
            inicio[k] += C
    else:  # financiado
        ic, n = p.malla_tasa_anual, int(p.malla_cuotas)
        cuota = costo_anual_equivalente(C, n, ic)
        for k in compras:
            for j in range(n):
                anio = k + j
                if anio < T:
                    fin[anio] += cuota
                else:
                    fin[-1] += cuota / (1 + ic) ** (anio - (T - 1))
    fin[-1] -= valor_residual
    return inicio, fin


def evaluar(danio, danio_malla, rendimiento, p, pagos_malla=None):
    """Resultado anual de las tres alternativas.

    danio, danio_malla y rendimiento pueden ser vectores (un año por elemento)
    o matrices (réplicas × años). Devuelve un dict alternativa -> arreglo.
    """
    danio = np.asarray(danio, dtype=float)
    danio_malla = np.asarray(danio_malla, dtype=float)
    rendimiento = np.asarray(rendimiento, dtype=float)
    if pagos_malla is None:
        pagos_malla = costo_malla_por_anio(p)
    inicio, fin = pagos_malla
    costo_prod = p.costo_produccion_ha * p.hectareas + p.costo_fijo_finca
    sin = ingreso(danio, rendimiento, p) - costo_prod
    if fondo_disponible(p):
        fondo = sin - p.fca_aporte_ha * p.hectareas + compensacion_fondo(danio, p)
    else:
        fondo = sin.copy()   # no puede adherir: queda igual que sin protección (se marca no disponible)
    malla = ingreso(danio_malla, rendimiento, p) - costo_prod - inicio - fin
    return {"sin_proteccion": sin, "fondo": fondo, "malla": malla}


def van_alternativas(anuales, p, pagos_malla=None):
    """VAN de cada alternativa a la tasa de descuento."""
    if pagos_malla is None:
        pagos_malla = costo_malla_por_anio(p)
    inicio, _ = pagos_malla
    i = p.tasa_descuento
    return {
        "sin_proteccion": van(anuales["sin_proteccion"], i),
        "fondo": van(anuales["fondo"], i),
        "malla": van(anuales["malla"], i, inversion_inicio=inicio),
    }
