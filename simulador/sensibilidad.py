"""
Módulo 7 – Sensibilidad y experimento de persistencia (pestaña 4).

Criterio de "mejor alternativa" (configurable con criterio_p5_minimo):
    entre las alternativas cuyo P5 del VAN es MAYOR que criterio_p5_minimo
    (por defecto 0, es decir, que en el 95 % de los futuros no pierden plata),
    la de mayor VAN medio. Si ninguna cumple, el resultado es "ninguna".

Todas las corridas usan la misma semilla (números aleatorios comunes), así
las diferencias entre puntos del barrido no son ruido de muestreo.
"""

from dataclasses import replace

import numpy as np

from .clima import CadenaMarkov
from .finca import ALTERNATIVAS, fondo_paga
from . import montecarlo as mc

NINGUNA = -1


def elegir_mejor(ind, p5_minimo=0.0):
    """Índice en ALTERNATIVAS de la mejor alternativa, o NINGUNA."""
    candidatas = [k for k, a in enumerate(ALTERNATIVAS) if ind[a]["van_p5"] > p5_minimo]
    if not candidatas:
        return NINGUNA
    return max(candidatas, key=lambda k: ind[ALTERNATIVAS[k]]["van_media"])


def barrido_precio(res, precios):
    """VAN medio y P5 de cada alternativa según el precio de la uva.

    El clima no depende del precio: se reevalúan los mismos escenarios.
    """
    p = res.parametros
    salida = {a: {"van_media": [], "van_p5": []} for a in ALTERNATIVAS}
    mejores = []
    for precio in precios:
        ind = mc.indicadores(mc.evaluar_escenarios(res.esc, replace(p, precio_uva=float(precio))))
        for a in ALTERNATIVAS:
            salida[a]["van_media"].append(ind[a]["van_media"])
            salida[a]["van_p5"].append(ind[a]["van_p5"])
        mejores.append(elegir_mejor(ind, p.criterio_p5_minimo))
    return {"precios": list(precios), "por_alternativa": salida, "mejor": mejores}


def mapa_mejor(p, hectareas, multiplicadores):
    """Mejor alternativa para cada (multiplicador de frecuencia, hectáreas).

    Por cada multiplicador se generan escenarios nuevos (sens_replicas réplicas);
    las hectáreas no cambian el clima, así que se reevalúan sobre esos escenarios.
    """
    mejor = np.full((len(multiplicadores), len(hectareas)), NINGUNA, dtype=int)
    van_media = {a: np.zeros_like(mejor, dtype=float) for a in ALTERNATIVAS}
    van_p5 = {a: np.zeros_like(mejor, dtype=float) for a in ALTERNATIVAS}
    for i, m in enumerate(multiplicadores):
        pm = replace(p, frecuencia_mult=float(m), replicas=p.sens_replicas)
        esc = mc.generar_escenarios(pm)
        for j, ha in enumerate(hectareas):
            ind = mc.indicadores(mc.evaluar_escenarios(esc, replace(pm, hectareas=float(ha))))
            mejor[i, j] = elegir_mejor(ind, p.criterio_p5_minimo)
            for a in ALTERNATIVAS:
                van_media[a][i, j] = ind[a]["van_media"]
                van_p5[a][i, j] = ind[a]["van_p5"]
    return {"hectareas": list(hectareas), "multiplicadores": list(multiplicadores),
            "mejor": mejor, "van_media": van_media, "van_p5": van_p5}


def racha_maxima(fuerte):
    """Racha más larga de años consecutivos True, por fila."""
    rachas = np.zeros(fuerte.shape[0], dtype=int)
    actual = np.zeros(fuerte.shape[0], dtype=int)
    for t in range(fuerte.shape[1]):
        actual = np.where(fuerte[:, t], actual + 1, 0)
        rachas = np.maximum(rachas, actual)
    return rachas


def persistencia(p, res_markov=None):
    """Cadena de Markov real contra años independientes con la misma proporción de G.

    Años independientes = cadena con P(S→G) = π_G y P(G→S) = π_S, que no tiene
    memoria y deja la misma proporción de años con granizo.
    """
    pi_s, pi_g = CadenaMarkov(p.p_s_a_g, p.p_g_a_s).estacionaria()
    if res_markov is None:
        res_markov = mc.correr(p)
    res_indep = mc.correr(replace(p, p_s_a_g=pi_g, p_g_a_s=pi_s))
    salida = {}
    for nombre, res in (("markov", res_markov), ("independiente", res_indep)):
        fuerte = fondo_paga(res.danio, res.parametros)   # años con granizo fuerte (paga el Fondo)
        salida[nombre] = {
            "indicadores": mc.indicadores(res),
            "proporcion_G": float(res.estados.mean()),
            "racha_G_media": float(racha_maxima(res.estados.astype(bool)).mean()),
            "prob_2_fuertes_seguidos": float((racha_maxima(fuerte) >= 2).mean()),
            "desvio_danio_20_anios": float(res.danio.sum(axis=1).std(ddof=1)),
        }
    salida["pi_G"] = pi_g
    return salida
