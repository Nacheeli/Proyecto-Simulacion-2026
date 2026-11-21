"""
Cálculos de una corrida completa de la app, sin Tk.

calcular_todo() junta en un diccionario todo lo que muestran las cinco
pestañas, así la interfaz solo dibuja y la exportación de gráficos no
necesita recalcular. No cambia ningún resultado del modelo: solo llama a
las funciones de simulador/.
"""

import numpy as np

from simulador import datos_reales as R
from simulador import estadistica as est
from simulador import montecarlo as mc
from simulador import sensibilidad as sens
from simulador.clima import CadenaMarkov
from simulador.danio import referencia_dacc
from simulador.generador import GeneradorLCG, prueba_chi_cuadrado

PASOS = ("Monte Carlo", "Sensibilidad al precio", "Sensibilidad a la severidad",
         "Persistencia", "Convergencia", "Intervalos de confianza")


def _rango(a, b, paso):
    return np.round(np.arange(a, b + paso / 2, paso), 6)


def calcular_todo(p, replica=1, progreso=None):
    """Devuelve un diccionario con los resultados de las cinco pestañas.

    progreso(texto, i, total) se llama antes de cada paso.
    """
    def avisar(i):
        if progreso:
            progreso(PASOS[i], i, len(PASOS))

    p.validar()
    if not 1 <= replica <= p.replicas:
        raise ValueError(f"La réplica a mostrar debe estar entre 1 y {p.replicas}.")
    out = {"p": p, "replica": replica}

    avisar(0)
    res = mc.correr(p)
    out["res"] = res
    out["ind"] = mc.indicadores(res)
    out["clima"] = mc.resumen_clima(res)
    out["equilibrio"] = mc.equilibrio_fondo(res)
    out["dacc"] = referencia_dacc(p.superficie_cultivada_sur)
    valores, absolutas, probs = R.tabla_dias_granizo()
    dias_reales = [d for _, d in R.cargar_serie_granizo() if d is not None]
    out["dias_real"] = {"valores": valores, "absolutas": absolutas, "probs": probs,
                        "media": float(np.mean(dias_reales)), "varianza": float(np.var(dias_reales, ddof=1))}
    cadena = CadenaMarkov(p.p_s_a_g, p.p_g_a_s)
    out["markov"] = {"matriz": cadena.matriz(), "estacionaria": cadena.estacionaria()}
    out["chi"] = prueba_chi_cuadrado(GeneradorLCG(p.semilla, p.lcg_a, p.lcg_c, p.lcg_m).generar(10_000))
    out["mejor"] = sens.elegir_mejor(out["ind"], p.criterio_p5_minimo)
    out["ic_van"] = est.ic_van(res)

    avisar(1)
    out["precios"] = _rango(p.sens_precio_min, p.sens_precio_max, p.sens_precio_paso)
    out["barrido_precio"] = sens.barrido_precio(res, out["precios"])
    out["cortes"] = est.cortes_malla(res.esc, p)

    avisar(2)
    out["factores"] = _rango(p.sens_sev_min, p.sens_sev_max, p.sens_sev_paso)
    out["hectareas"] = np.arange(1, p.sens_ha_max + 1)
    out["severidad"] = sens.analisis_severidad(p, out["factores"], out["precios"], out["hectareas"])
    # corte fino de severidad (Fondo − Sin, con IC), compartido por las pestañas 4 y 5
    out["filas_corte_sev"] = est.ic_corte_severidad(p, _rango(0.25, 0.35, 0.025))
    out["cruce_sev"] = est.cruce_severidad(out["filas_corte_sev"])

    avisar(3)
    out["persistencia"] = sens.persistencia(p, res)

    avisar(4)
    tamanios = sorted({t for t in (100, 500, 1000, 5000, 10_000, p.conv_replicas_max)
                       if t <= p.conv_replicas_max})
    out["convergencia"] = est.convergencia(p, tamanios)

    avisar(5)
    out["diferencias"] = est.ic_diferencias(res, est.corrida_independiente(p))
    out["cortes_tasa"] = est.cortes_por_tasa(res.esc, p, (0.03, 0.05, 0.08))
    out["cortes_tc_doble"] = est.corte_escalando_tipo_de_cambio(res.esc, p, 2.0)
    return out
