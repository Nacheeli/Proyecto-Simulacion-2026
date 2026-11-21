"""
Módulo 6 – Monte Carlo (TP7).

Se generan N escenarios de 'anios' años con el generador propio. Las tres
alternativas se evalúan sobre los MISMOS escenarios (números aleatorios
comunes), así la comparación es justa.

Indicador principal: VAN (valor actual neto) a la tasa de descuento.
Por alternativa: media, desvío y P5 del VAN, suma sin descontar,
% de años con pérdida (resultado anual < 0), percentil 1 de los resultados
anuales (más estable que el peor año) y peor año.
"""

from dataclasses import dataclass

import numpy as np

from .finca import (ALTERNATIVAS, ModeloClima, compensacion_fondo, costo_malla_por_anio,
                    evaluar, fondo_disponible, fondo_paga, van_alternativas)
from .generador import GeneradorLCG


@dataclass
class Escenarios:
    """Clima, daños y rendimientos de todas las réplicas (no depende de la economía)."""
    estados: np.ndarray        # réplicas × años, 1 = G, 0 = S
    dias: np.ndarray           # réplicas × años
    danio: np.ndarray          # réplicas × años
    danio_malla: np.ndarray
    rendimiento: np.ndarray
    eventos_danio: np.ndarray  # daño de cada granizada simulada (todas)
    numeros_usados: int


@dataclass
class ResultadoMC:
    parametros: object
    esc: Escenarios
    anuales: dict              # alternativa -> réplicas × años
    totales: dict              # alternativa -> réplicas (suma sin descontar)
    van: dict                  # alternativa -> réplicas
    compensacion: np.ndarray   # réplicas × años (pagos del Fondo)
    pagos_malla: tuple         # (inicio, fin) por año

    # accesos cortos usados por la interfaz y los tests
    @property
    def estados(self):
        return self.esc.estados

    @property
    def dias(self):
        return self.esc.dias

    @property
    def danio(self):
        return self.esc.danio

    @property
    def danio_malla(self):
        return self.esc.danio_malla

    @property
    def rendimiento(self):
        return self.esc.rendimiento

    @property
    def eventos_danio(self):
        return self.esc.eventos_danio

    @property
    def numeros_usados(self):
        return self.esc.numeros_usados


def generar_escenarios(p, tabla_dias_real=None):
    p.validar()
    gen = GeneradorLCG(p.semilla, p.lcg_a, p.lcg_c, p.lcg_m)
    modelo = ModeloClima(p, tabla_dias_real)
    N, T = p.replicas, p.anios
    estados = np.zeros((N, T), dtype=np.int8)
    dias = np.zeros((N, T), dtype=np.int16)
    danio = np.zeros((N, T))
    danio_m = np.zeros((N, T))
    rend = np.zeros((N, T))
    eventos = []
    for r in range(N):
        e = modelo.generar_escenario(gen)
        estados[r] = [1 if x == "G" else 0 for x in e.estados]
        dias[r] = e.dias
        danio[r] = e.danio
        danio_m[r] = e.danio_malla
        rend[r] = e.rendimiento
        for ev in e.eventos:
            eventos.extend(ev)
    return Escenarios(estados, dias, danio, danio_m, rend, np.array(eventos), gen.cantidad_generada)


def evaluar_escenarios(esc, p):
    """Economía de las tres alternativas sobre escenarios ya generados."""
    pagos = costo_malla_por_anio(p)
    anuales = evaluar(esc.danio, esc.danio_malla, esc.rendimiento, p, pagos)
    totales = {a: anuales[a].sum(axis=1) for a in ALTERNATIVAS}
    vans = van_alternativas(anuales, p, pagos)
    comp = compensacion_fondo(esc.danio, p)
    return ResultadoMC(p, esc, anuales, totales, vans, comp, pagos)


def correr(p, tabla_dias_real=None):
    return evaluar_escenarios(generar_escenarios(p, tabla_dias_real), p)


def indicadores(res):
    """Tabla de indicadores: alternativa -> dict."""
    salida = {}
    for a in ALTERNATIVAS:
        v = res.van[a]
        tot = res.totales[a]
        anu = res.anuales[a]
        salida[a] = {
            "van_media": float(v.mean()),
            "van_desvio": float(v.std(ddof=1)) if v.size > 1 else 0.0,
            "van_p5": float(np.percentile(v, 5)),
            "van_p95": float(np.percentile(v, 95)),
            "pct_van_negativo": float((v < 0).mean() * 100),
            "media": float(tot.mean()),
            "desvio": float(tot.std(ddof=1)) if tot.size > 1 else 0.0,
            "p5": float(np.percentile(tot, 5)),
            "pct_anios_perdida": float((anu < 0).mean() * 100),
            "peor_anio": float(anu.min()),
            "p1_anual": float(np.percentile(anu, 1)),
            "disponible": True if a != "fondo" else bool(fondo_disponible(res.parametros)),
            "media_anual": float(anu.mean()),
        }
    return salida


def equilibrio_fondo(res):
    """Pagos esperados del Fondo contra los aportes de la finca, por año."""
    p = res.parametros
    aporte = p.fca_aporte_ha * p.hectareas
    pago_medio = float(res.compensacion.mean())
    return {
        "aporte_anual": aporte,
        "pago_medio_anual": pago_medio,
        "pagos_sobre_aportes": pago_medio / aporte if aporte else float("inf"),
        "prob_cobrar": float((res.compensacion > 0).mean()),
    }


def resumen_clima(res):
    """Frecuencias simuladas, para comparar con los datos reales."""
    p = res.parametros
    dias = res.dias.ravel()
    maximo = int(dias.max()) if dias.size else 0
    frecuencias = {k: float((dias == k).mean()) for k in range(maximo + 1)}
    return {
        "frecuencia_dias": frecuencias,
        "media_dias": float(dias.mean()),
        "varianza_dias": float(dias.var(ddof=1)) if dias.size > 1 else 0.0,
        "proporcion_G": float(res.estados.mean()),
        "danio_medio_anual": float(res.danio.mean()),
        "danio_medio_anual_malla": float(res.danio_malla.mean()),
        "prob_danio_supera_umbral": float((res.danio > p.fca_umbral).mean()),
        "prob_danio_igual_umbral": float((res.danio == p.fca_umbral).mean()),
        "prob_danio_paga": float(fondo_paga(res.danio, p).mean()),
        "danio_medio_evento": float(res.eventos_danio.mean()) if res.eventos_danio.size else 0.0,
    }
