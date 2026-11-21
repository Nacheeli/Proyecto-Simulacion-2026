"""
Módulo 7 – Sensibilidad y experimento de persistencia (pestaña 4).

Criterio de "mejor alternativa" (configurable con criterio_p5_minimo):
    entre las alternativas DISPONIBLES cuyo P5 del VAN es MAYOR que
    criterio_p5_minimo (por defecto 0: en el 95 % de los futuros no pierden
    plata), la de mayor VAN medio. Si ninguna cumple, el resultado es "ninguna".

Nota sobre las hectáreas: con costo fijo por finca = 0, todo el modelo es
proporcional a las hectáreas (ingresos, costos, aportes, compensaciones y
malla), así que el VAN escala exactamente con ellas y el ranking NO puede
cambiar con el tamaño. Las hectáreas solo importan por el límite de 30 ha del
Fondo y por un costo fijo por finca, que además es igual para las tres
alternativas y solo afecta el criterio P5 > 0.

Todas las corridas usan la misma semilla (números aleatorios comunes). El
factor de severidad cambia la tabla de daño pero no la secuencia de números
aleatorios, así que los escenarios de distintos factores son comparables.
"""

from dataclasses import replace

import numpy as np

from .clima import CadenaMarkov
from .danio import referencia_dacc
from .finca import ALTERNATIVAS, fondo_paga
from . import montecarlo as mc

NINGUNA = -1


def elegir_mejor(ind, p5_minimo=0.0):
    """Índice en ALTERNATIVAS de la mejor alternativa, o NINGUNA."""
    candidatas = [k for k, a in enumerate(ALTERNATIVAS)
                  if ind[a].get("disponible", True) and ind[a]["van_p5"] > p5_minimo]
    if not candidatas:
        return NINGUNA
    return max(candidatas, key=lambda k: ind[ALTERNATIVAS[k]]["van_media"])


def es_caso_limite(ind, mejor, p5_minimo=0.0, tolerancia=0.02):
    """True si la elección de la celda depende de un P5 pegado al criterio.

    "Pegado" = a menos de max(tolerancia × |VAN medio|, semiancho del IC 95 % del
    P5) del criterio. Se marca si (a) la mejor alternativa tiene un P5 pegado al
    criterio, o (b) una alternativa disponible con MAYOR VAN medio quedó afuera
    por un P5 pegado al criterio. En los dos casos, con otra semilla u otra
    cantidad de réplicas la celda puede cambiar de color.
    """
    def cerca(a):
        banda = max(tolerancia * abs(ind[a]["van_media"]), ind[a].get("van_p5_semiancho", 0.0))
        return abs(ind[a]["van_p5"] - p5_minimo) < banda

    media_mejor = ind[ALTERNATIVAS[mejor]]["van_media"] if mejor != NINGUNA else -np.inf
    for k, a in enumerate(ALTERNATIVAS):
        if not ind[a].get("disponible", True):
            continue
        if k == mejor and cerca(a):
            return True
        if k != mejor and ind[a]["van_media"] > media_mejor and cerca(a):
            return True
    return False


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


def analisis_severidad(p, factores, precios, hectareas, replicas=None):
    """Barrido del factor de severidad del daño, con dos mapas de mejor alternativa.

    Por cada factor se generan escenarios nuevos (misma semilla) y sobre ellos:
      - indicadores de daño: P(el Fondo paga), pérdida media anual, pagos/aportes;
      - VAN medio y P5 de cada alternativa y mejor alternativa (con los parámetros base);
      - mapa precio de la uva × severidad (se reevalúan los mismos escenarios);
      - mapa hectáreas × severidad (importa por el límite de 30 ha y el costo fijo).
    """
    replicas = replicas or p.sens_replicas
    dacc = referencia_dacc(p.superficie_cultivada_sur)
    nf = len(factores)
    salida = {
        "factores": list(factores), "precios": list(precios), "hectareas": list(hectareas),
        "prob_paga": np.zeros(nf), "perdida_media": np.zeros(nf), "pagos_sobre_aportes": np.zeros(nf),
        "dentro_dacc": np.zeros(nf, dtype=bool), "mejor": np.full(nf, NINGUNA),
        "van_media": {a: np.zeros(nf) for a in ALTERNATIVAS},
        "van_p5": {a: np.zeros(nf) for a in ALTERNATIVAS},
        "mapa_precio": np.full((nf, len(precios)), NINGUNA),
        "mapa_ha": np.full((nf, len(hectareas)), NINGUNA),
        "limite_precio": np.zeros((nf, len(precios)), dtype=bool),
        "limite_ha": np.zeros((nf, len(hectareas)), dtype=bool),
        "dacc": dacc, "replicas": replicas,
    }
    for i, f in enumerate(factores):
        pf = replace(p, severidad=float(f), replicas=replicas)
        esc = mc.generar_escenarios(pf)
        res = mc.evaluar_escenarios(esc, pf)
        ind = mc.indicadores(res)
        salida["prob_paga"][i] = float(fondo_paga(esc.danio, pf).mean())
        salida["perdida_media"][i] = float(esc.danio.mean())
        salida["pagos_sobre_aportes"][i] = mc.equilibrio_fondo(res)["pagos_sobre_aportes"]
        salida["dentro_dacc"][i] = dacc["con_lucha"] <= salida["perdida_media"][i] <= dacc["sin_lucha"]
        salida["mejor"][i] = elegir_mejor(ind, p.criterio_p5_minimo)
        for a in ALTERNATIVAS:
            salida["van_media"][a][i] = ind[a]["van_media"]
            salida["van_p5"][a][i] = ind[a]["van_p5"]
        for j, precio in enumerate(precios):
            ij = mc.indicadores(mc.evaluar_escenarios(esc, replace(pf, precio_uva=float(precio))))
            salida["mapa_precio"][i, j] = elegir_mejor(ij, p.criterio_p5_minimo)
            salida["limite_precio"][i, j] = es_caso_limite(ij, salida["mapa_precio"][i, j], p.criterio_p5_minimo)
        for j, ha in enumerate(hectareas):
            ij = mc.indicadores(mc.evaluar_escenarios(esc, replace(pf, hectareas=float(ha))))
            salida["mapa_ha"][i, j] = elegir_mejor(ij, p.criterio_p5_minimo)
            salida["limite_ha"][i, j] = es_caso_limite(ij, salida["mapa_ha"][i, j], p.criterio_p5_minimo)
    return salida


def factor_cambio_fondo(analisis):
    """Tramos de severidad donde el Fondo deja de ser (o pasa a ser) la mejor alternativa.

    Devuelve una lista de (factor_antes, factor_despues, mejor_antes, mejor_despues).
    """
    k_fondo = ALTERNATIVAS.index("fondo")
    cambios = []
    f, m = analisis["factores"], analisis["mejor"]
    for i in range(1, len(f)):
        if (m[i - 1] == k_fondo) != (m[i] == k_fondo):
            cambios.append((f[i - 1], f[i], int(m[i - 1]), int(m[i])))
    return cambios


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
