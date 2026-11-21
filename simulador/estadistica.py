"""
Módulo 8 – Precisión estadística del Monte Carlo (TP7).

- Intervalo de confianza del 95 % de una media:  x̄ ± 1,96 · s / √n.
- Diferencias de VAN réplica a réplica con NÚMEROS ALEATORIOS COMUNES (NAC):
  como las tres alternativas se evalúan sobre los mismos escenarios de clima,
  la diferencia D_r = VAN_A,r − VAN_B,r tiene varianza
      Var(D) = Var(A) + Var(B) − 2·Cov(A, B)
  y la covarianza positiva la achica mucho. Con corridas independientes
  (otra semilla para B) la covarianza es 0 y  Var = Var(A) + Var(B).
- Convergencia: el generador es secuencial, así que las primeras n réplicas de
  una corrida de N son exactamente la corrida de n réplicas (misma semilla).
- Precio de corte: con los escenarios fijos, el VAN medio de cada alternativa
  es LINEAL en el precio de la uva, así que el precio donde dos alternativas
  empatan se calcula exacto con dos evaluaciones.
"""

from dataclasses import replace

import numpy as np

from .finca import ALTERNATIVAS
from . import montecarlo as mc

Z_95 = 1.959963984540054
PARES = (("fondo", "sin_proteccion"), ("fondo", "malla"), ("sin_proteccion", "malla"))


def ic_media(x, z=Z_95):
    """Media, semiancho y extremos del IC de la media."""
    x = np.asarray(x, dtype=float)
    n = x.size
    media = float(x.mean())
    s = float(x.std(ddof=1)) if n > 1 else 0.0
    semi = z * s / np.sqrt(n) if n > 0 else float("nan")
    return {"n": n, "media": media, "desvio": s, "semiancho": float(semi),
            "inferior": media - semi, "superior": media + semi}


def ic_van(res):
    """IC 95 % del VAN medio de cada alternativa."""
    return {a: ic_media(res.van[a]) for a in ALTERNATIVAS}


def ic_diferencias(res, res_independiente=None):
    """IC 95 % de las diferencias de VAN medio entre pares de alternativas.

    nac:          diferencias réplica a réplica sobre los mismos escenarios.
    independiente (si se pasa una corrida con otra semilla): la alternativa B se
                  toma de esa corrida; semiancho = z·√(s_A²/n + s_B²/n).
    """
    salida = {}
    for a, b in PARES:
        d = ic_media(res.van[a] - res.van[b])
        fila = {"nac": d, "correlacion": float(np.corrcoef(res.van[a], res.van[b])[0, 1])}
        if res_independiente is not None:
            xa, xb = res.van[a], res_independiente.van[b]
            semi = Z_95 * np.sqrt(xa.var(ddof=1) / xa.size + xb.var(ddof=1) / xb.size)
            media = float(xa.mean() - xb.mean())
            fila["independiente"] = {"media": media, "semiancho": float(semi),
                                     "inferior": media - semi, "superior": media + semi}
            fila["reduccion"] = float(semi / d["semiancho"]) if d["semiancho"] > 0 else float("inf")
        salida[(a, b)] = fila
    return salida


def corrida_independiente(p, desplazamiento_semilla=1):
    """La misma corrida con otra semilla (para comparar contra NAC)."""
    return mc.correr(replace(p, semilla=p.semilla + desplazamiento_semilla))


def convergencia(p, tamanios=(100, 500, 1000, 5000, 10_000, 50_000), res_grande=None):
    """VAN medio e IC 95 % de cada alternativa para distintas cantidades de réplicas.

    Se corre una sola vez con el tamaño máximo y se usan los prefijos.
    """
    tamanios = sorted(int(n) for n in tamanios)
    if res_grande is None or res_grande.parametros.replicas < tamanios[-1]:
        res_grande = mc.correr(replace(p, replicas=tamanios[-1]))
    salida = {"tamanios": tamanios}
    for a in ALTERNATIVAS:
        filas = [ic_media(res_grande.van[a][:n]) for n in tamanios]
        salida[a] = {
            "media": np.array([f["media"] for f in filas]),
            "semiancho": np.array([f["semiancho"] for f in filas]),
        }
    return salida


def _van_medio(esc, p):
    return {a: float(v.mean()) for a, v in mc.evaluar_escenarios(esc, p).van.items()}


def precio_corte(esc, p, a="malla", b="fondo", precios=(400.0, 800.0)):
    """Precio de la uva ($/kg) donde el VAN medio de 'a' iguala al de 'b'.

    Exacto porque el VAN medio es lineal en el precio con los escenarios fijos.
    Devuelve None si las dos rectas son paralelas.
    """
    x1, x2 = precios
    v1 = _van_medio(esc, replace(p, precio_uva=x1))
    v2 = _van_medio(esc, replace(p, precio_uva=x2))
    d1, d2 = v1[a] - v1[b], v2[a] - v2[b]
    if d2 == d1:
        return None
    return x1 - d1 * (x2 - x1) / (d2 - d1)


def cortes_malla(esc, p):
    """Precio de corte de la malla contra el Fondo y contra no protegerse, en $/kg y USD/kg."""
    salida = {}
    for b in ("fondo", "sin_proteccion"):
        pesos = precio_corte(esc, p, "malla", b)
        salida[b] = {"pesos_kg": pesos, "usd_kg": pesos / p.tipo_cambio if pesos is not None else None}
    return salida


def cortes_por_tasa(esc, p, tasas=(0.03, 0.05, 0.08)):
    """Precio de corte de la malla para distintas tasas de descuento (mismos escenarios)."""
    return {t: cortes_malla(esc, replace(p, tasa_descuento=t)) for t in tasas}


def corte_escalando_tipo_de_cambio(esc, p, factor):
    """Precio de corte (USD/kg) si el tipo de cambio se multiplica por 'factor'.

    Sirve para ver si el corte en dólares es independiente del tipo de cambio:
    lo es contra 'sin protección' (todo lo demás se cancela), pero NO contra el
    Fondo, porque el aporte y la compensación del Fondo están fijos en pesos.
    """
    return cortes_malla(esc, replace(p, tipo_cambio=p.tipo_cambio * factor))


def _cruce_cero(x, y):
    """Primer x donde y cambia de signo (interpolación lineal), o None."""
    for i in range(1, len(x)):
        if (y[i - 1] < 0) != (y[i] < 0):
            return x[i - 1] + (x[i] - x[i - 1]) * (-y[i - 1]) / (y[i] - y[i - 1])
    return None


def cruce_severidad(filas):
    """Factor de severidad donde la diferencia Fondo − Sin pasa por 0, con su IC.

    Se interpolan la media y los extremos del IC: el corte del extremo superior
    da el límite inferior del factor y viceversa (la diferencia crece con el factor).
    """
    x = [f["factor"] for f in filas]
    return {
        "estimado": _cruce_cero(x, [f["media"] for f in filas]),
        "inferior": _cruce_cero(x, [f["superior"] for f in filas]),
        "superior": _cruce_cero(x, [f["inferior"] for f in filas]),
    }


def ic_corte_severidad(p, factores, replicas=None):
    """IC 95 % (con NAC) de la diferencia VAN Fondo − Sin protección en cada factor de severidad."""
    replicas = replicas or p.replicas
    salida = []
    for f in factores:
        pf = replace(p, severidad=float(f), replicas=replicas)
        res = mc.evaluar_escenarios(mc.generar_escenarios(pf), pf)
        d = ic_media(res.van["fondo"] - res.van["sin_proteccion"])
        salida.append({"factor": float(f), **d})
    return salida
