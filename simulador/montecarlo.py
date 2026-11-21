"""
Módulo 6 – Monte Carlo (TP7).

Se generan N escenarios de 'anios' años con el generador propio. Las tres
alternativas se evalúan sobre los MISMOS escenarios (números aleatorios
comunes), así la comparación es justa.

Indicadores por alternativa:
    media, desvío y P5 de la ganancia total de los 'anios' años,
    % de años con pérdida (resultado anual < 0) y peor año.
"""

from dataclasses import dataclass

import numpy as np

from .finca import ALTERNATIVAS, ModeloClima, costo_malla_por_anio, evaluar
from .generador import GeneradorLCG


@dataclass
class ResultadoMC:
    parametros: object
    estados: np.ndarray        # réplicas × años, 1 = G, 0 = S
    dias: np.ndarray           # réplicas × años
    danio: np.ndarray          # réplicas × años
    danio_malla: np.ndarray
    rendimiento: np.ndarray
    eventos_danio: np.ndarray  # daño de cada granizada simulada (todas)
    anuales: dict              # alternativa -> réplicas × años
    totales: dict              # alternativa -> réplicas
    costo_malla: np.ndarray    # años
    numeros_usados: int


def correr(p, tabla_dias_real=None):
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
        esc = modelo.generar_escenario(gen)
        estados[r] = [1 if e == "G" else 0 for e in esc.estados]
        dias[r] = esc.dias
        danio[r] = esc.danio
        danio_m[r] = esc.danio_malla
        rend[r] = esc.rendimiento
        for ev in esc.eventos:
            eventos.extend(ev)
    costo_malla = costo_malla_por_anio(p)
    anuales = evaluar(danio, danio_m, rend, p, costo_malla)
    totales = {a: anuales[a].sum(axis=1) for a in ALTERNATIVAS}
    return ResultadoMC(p, estados, dias, danio, danio_m, rend, np.array(eventos),
                       anuales, totales, costo_malla, gen.cantidad_generada)


def indicadores(res):
    """Tabla de indicadores: alternativa -> dict."""
    salida = {}
    for a in ALTERNATIVAS:
        tot = res.totales[a]
        anu = res.anuales[a]
        salida[a] = {
            "media": float(tot.mean()),
            "desvio": float(tot.std(ddof=1)) if tot.size > 1 else 0.0,
            "p5": float(np.percentile(tot, 5)),
            "p95": float(np.percentile(tot, 95)),
            "pct_anios_perdida": float((anu < 0).mean() * 100),
            "pct_replicas_perdida": float((tot < 0).mean() * 100),
            "peor_anio": float(anu.min()),
            "media_anual": float(anu.mean()),
        }
    return salida


def resumen_clima(res):
    """Frecuencias simuladas, para comparar con los datos reales."""
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
        "prob_danio_supera_umbral": float((res.danio > res.parametros.fca_umbral).mean()),
        "danio_medio_evento": float(res.eventos_danio.mean()) if res.eventos_danio.size else 0.0,
    }
