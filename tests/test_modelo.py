"""
Pruebas del modelo (sin abrir la ventana).  Ejecutar:  python -m pytest
"""

from dataclasses import replace

import numpy as np
import pytest

from simulador import datos_reales as R
from simulador import montecarlo as mc
from simulador import sensibilidad as sens
from simulador.clima import CadenaMarkov, TablaEmpirica
from simulador.danio import TablaDanio, combinar_danios, danios_con_malla, referencia_dacc
from simulador.finca import (compensacion_fondo, costo_malla_por_anio, evaluar,
                             factor_anualidad, van, van_alternativas)
from simulador.generador import GeneradorLCG, prueba_chi_cuadrado
from simulador.parametros import Parametros


@pytest.fixture(scope="module")
def base():
    """Corrida por defecto (10.000 réplicas), compartida por varios tests."""
    return mc.correr(Parametros())


# ---------------------------------------------------------------- generador
def test_lcg_primeros_valores_a_mano():
    g = GeneradorLCG(semilla=1, a=5, c=3, m=16)
    # X1 = (5·1+3) mod 16 = 8 ; X2 = (5·8+3) mod 16 = 11 ; X3 = (5·11+3) mod 16 = 10
    assert [g.siguiente() for _ in range(3)] == [8 / 16, 11 / 16, 10 / 16]


def test_lcg_periodo_completo_hull_dobell():
    g = GeneradorLCG(semilla=0, a=5, c=3, m=16)
    assert len({g.siguiente() for _ in range(16)}) == 16


def test_chi_cuadrado_acepta_uniformidad():
    res = prueba_chi_cuadrado(GeneradorLCG(12345).generar(10_000), intervalos=10)
    assert res["acepta_h0"]
    assert res["critico"] == pytest.approx(16.92, abs=0.05)   # tabla: χ²(9; 0,05) = 16,92


def test_chi_cuadrado_rechaza_numeros_malos():
    assert not prueba_chi_cuadrado([0.05] * 1000)["acepta_h0"]


# ------------------------------------------------------------------- datos
def test_tabla_real_coincide_con_documento():
    valores, absolutas, _ = R.tabla_dias_granizo()
    assert dict(zip(valores, absolutas)) == {0: 16, 1: 13, 2: 9, 3: 5, 4: 2, 5: 1, 7: 1}


def test_matriz_markov_se_reproduce_desde_el_csv():
    serie = dict(R.cargar_serie_granizo())
    pares = {("S", "S"): 0, ("S", "G"): 0, ("G", "S"): 0, ("G", "G"): 0}
    for anio, dias in serie.items():
        sig = serie.get(anio + 1)
        if dias is not None and sig is not None:
            pares[("G" if dias else "S", "G" if sig else "S")] += 1
    p_sg = pares[("S", "G")] / (pares[("S", "S")] + pares[("S", "G")])
    p_gs = pares[("G", "S")] / (pares[("G", "S")] + pares[("G", "G")])
    assert round(p_sg, 2) == R.MARKOV_P_S_A_G
    assert round(p_gs, 2) == R.MARKOV_P_G_A_S


# ------------------------------------------------------------------- clima
def test_estacionaria():
    # Con la matriz redondeada (0,11) da S = 0,355; el 0,36 del documento sale de
    # las fracciones exactas del CSV (3/15 y 3/27), que dan S = 0,357.
    pi_s, pi_g = CadenaMarkov(0.20, 0.11).estacionaria()
    assert pi_s == pytest.approx(0.36, abs=0.01) and pi_g == pytest.approx(0.64, abs=0.01)
    pi_s, _ = CadenaMarkov(3 / 15, 3 / 27).estacionaria()
    assert round(pi_s, 2) == 0.36


def test_transformada_inversa():
    t = TablaEmpirica([0, 1, 2], [0.5, 0.3, 0.2])
    assert [t.inversa(u) for u in (0.0, 0.49, 0.5, 0.79, 0.8, 0.999)] == [0, 0, 1, 1, 2, 2]


def test_simulacion_reproduce_tabla_real_y_estacionaria(base):
    resumen = mc.resumen_clima(base)
    valores, _, probs = R.tabla_dias_granizo()
    for v, q in zip(valores, probs):
        assert abs(resumen["frecuencia_dias"].get(v, 0) - q) < 0.02, v
    assert abs(resumen["proporcion_G"] - 0.645) < 0.01
    assert abs(resumen["media_dias"] - 1.40) < 0.05


def test_multiplicador_uno_no_cambia_nada_y_dos_duplica():
    p = Parametros(replicas=2000)
    a = mc.generar_escenarios(p)
    b = mc.generar_escenarios(replace(p, frecuencia_mult=1.0))
    assert np.array_equal(a.danio, b.danio)
    doble = mc.generar_escenarios(replace(p, frecuencia_mult=2.0))
    assert doble.dias.mean() == pytest.approx(2 * a.dias.mean(), rel=0.05)


# -------------------------------------------------------------------- daño
def test_tabla_danio_continua_a_mano():
    t = TablaDanio([0, 0, 0.4], [0, 0.1, 0.6], [0.5, 0.3, 0.2])
    assert t.inversa(0.2) == 0                           # punto en 0
    assert t.inversa(0.65) == pytest.approx(0.05)        # mitad del intervalo 0–10 %
    assert t.inversa(0.9) == pytest.approx(0.5)          # mitad del intervalo 40–60 %
    assert t.media() == pytest.approx(0.3 * 0.05 + 0.2 * 0.5)


def test_combinacion_de_danios():
    assert combinar_danios([]) == 0
    assert combinar_danios([0.3, 0.5]) == pytest.approx(0.65)   # 1 − 0,7·0,5
    assert combinar_danios(danios_con_malla([0.6], 0.9)) == pytest.approx(0.06)


def test_no_hay_anios_con_danio_exactamente_en_el_umbral(base):
    assert mc.resumen_clima(base)["prob_danio_igual_umbral"] == 0


def test_condicion_mayor_o_mayor_igual_difieren_poco(base):
    otra = mc.evaluar_escenarios(base.esc, replace(base.parametros, fca_condicion=">"))
    a, b = mc.indicadores(base)["fondo"], mc.indicadores(otra)["fondo"]
    assert abs(a["van_media"] - b["van_media"]) / abs(a["van_media"]) < 0.005
    assert abs(a["van_p5"] - b["van_p5"]) / abs(a["van_p5"]) < 0.005


def test_perdida_media_anual_dentro_del_rango_dacc(base):
    ref = referencia_dacc(base.parametros.superficie_cultivada_sur)
    perdida = mc.resumen_clima(base)["danio_medio_anual"]
    assert ref["con_lucha"] <= perdida <= ref["sin_lucha"]
    assert perdida == pytest.approx(0.13, abs=0.01)


# ------------------------------------------------------- casos a mano: finca
P = Parametros(hectareas=5.3, precio_uva=400, costo_produccion_ha=2_200_000,
               tipo_cambio=1450, malla_costo_usd_ha=4250, malla_vida_util=15,
               tasa_descuento=0.05, fca_condicion=">=")
REND = 7350.0
INGRESO_SANO = 5.3 * 7350 * 400           # 15.582.000
COSTO_PROD = 5.3 * 2_200_000              # 11.660.000
APORTE = 5.3 * 51_000                     # 270.300
C_MALLA = 4250 * 1450 * 5.3               # 32.661.250
CAE_MALLA = C_MALLA * 0.05 / (1 - 1.05 ** -15)   # costo anual equivalente ≈ 3.146.693


def test_anio_sin_granizo():
    r = evaluar([0.0], [0.0], [REND], P)
    assert r["sin_proteccion"][0] == pytest.approx(INGRESO_SANO - COSTO_PROD)              # 3.922.000
    assert r["fondo"][0] == pytest.approx(INGRESO_SANO - COSTO_PROD - APORTE)              # 3.651.700
    assert r["malla"][0] == pytest.approx(INGRESO_SANO - COSTO_PROD - CAE_MALLA)


def test_anio_con_60_por_ciento_paga_el_fondo():
    r = evaluar([0.60], [0.06], [REND], P)
    compensacion = 2_000_000 * 5.3 * 0.60                                                 # 6.360.000
    assert compensacion_fondo([0.60], P)[0] == pytest.approx(compensacion)
    assert r["fondo"][0] == pytest.approx(INGRESO_SANO * 0.4 - COSTO_PROD - APORTE + compensacion)
    assert r["malla"][0] == pytest.approx(INGRESO_SANO * 0.94 - COSTO_PROD - CAE_MALLA)


def test_anio_con_40_por_ciento_no_paga_el_fondo():
    r = evaluar([0.40], [0.04], [REND], P)
    assert compensacion_fondo([0.40], P)[0] == 0
    assert r["fondo"][0] == pytest.approx(INGRESO_SANO * 0.6 - COSTO_PROD - APORTE)


def test_umbral_499_no_paga_50_paga_con_mayor_igual():
    assert compensacion_fondo([0.499], P)[0] == 0
    assert compensacion_fondo([0.50], P)[0] == pytest.approx(2_000_000 * 5.3 * 0.5)
    estricto = replace(P, fca_condicion=">")
    assert compensacion_fondo([0.50], estricto)[0] == 0
    fijo = replace(P, fca_modo="fijo")
    assert compensacion_fondo([0.60], fijo)[0] == pytest.approx(2_000_000 * 5.3)


def test_varios_eventos_combinados_activan_el_fondo():
    # 30 % y 50 % por separado: el de 30 % no alcanza; combinados dan 65 %
    assert compensacion_fondo([combinar_danios([0.3, 0.5])], P)[0] > 0


def test_peor_anio_del_fondo_es_la_perdida_maxima_no_cubierta(base):
    """Daño apenas debajo del 50 % con rendimiento mínimo: −4,40 M."""
    p = base.parametros
    cota = 5.3 * 7100 * 400 * 0.5 - COSTO_PROD - APORTE
    assert mc.indicadores(base)["fondo"]["peor_anio"] >= cota - 1
    assert mc.indicadores(base)["fondo"]["peor_anio"] == pytest.approx(cota, abs=0.05e6)


# --------------------------------------------------------------------- VAN
def test_van_flujos_constantes_igual_a_anualidad():
    i, T, flujo = 0.05, 20, 1_000_000
    esperado = flujo * (1 - 1.05 ** -20) / 0.05          # 12.462.210,34
    assert van(np.full(T, flujo), i) == pytest.approx(esperado)
    assert factor_anualidad(T, i) == pytest.approx(12.4622103, rel=1e-8)


def test_van_con_tasa_cero_es_la_suma():
    flujos = np.array([1.0, -2.0, 3.5])
    assert van(flujos, 0.0) == pytest.approx(flujos.sum())


def test_van_inversion_al_inicio_no_se_descuenta_el_primer_anio():
    # 100 al inicio del año 1 = −100 sin descontar; 110 al fin del año 1 a 10 % = 100
    assert van([10.0], 0.10, inversion_inicio=[100.0]) == pytest.approx(-100 + 110 / 1.1)


@pytest.mark.parametrize("tasa", [0.0, 0.05, 0.10])
def test_formas_de_pago_de_la_malla_mismo_van(tasa):
    """Con tasa del crédito = tasa de descuento, amortizado = contado = financiado."""
    vans = []
    for modo in ("amortizado", "contado", "financiado"):
        p = replace(P, malla_modo_pago=modo, malla_tasa_anual=tasa, tasa_descuento=tasa)
        anuales = evaluar(np.zeros(p.anios), np.zeros(p.anios), np.full(p.anios, REND), p)
        vans.append(van_alternativas(anuales, p)["malla"])
    assert vans[0] == pytest.approx(vans[1]) and vans[0] == pytest.approx(vans[2])


def test_amortizado_sin_interes_es_costo_sobre_vida():
    p = replace(P, tasa_descuento=0.0)
    inicio, fin = costo_malla_por_anio(p)
    assert inicio.sum() == 0 and fin[0] == pytest.approx(C_MALLA / 15)


# ------------------------------------------------------------- Monte Carlo
def test_misma_semilla_mismos_resultados():
    a = mc.indicadores(mc.correr(Parametros(replicas=500, semilla=777)))
    b = mc.indicadores(mc.correr(Parametros(replicas=500, semilla=777)))
    c = mc.indicadores(mc.correr(Parametros(replicas=500, semilla=778)))
    assert a == b
    assert a != c


def test_las_tres_alternativas_comparten_el_clima():
    res = mc.correr(Parametros(replicas=200))
    sin, fondo = res.anuales["sin_proteccion"], res.anuales["fondo"]
    no_cobra = res.compensacion == 0
    aporte = res.parametros.fca_aporte_ha * res.parametros.hectareas
    assert (abs((sin - fondo)[no_cobra] - aporte) < 1e-6).all()


def test_equilibrio_del_fondo(base):
    eq = mc.equilibrio_fondo(base)
    assert eq["aporte_anual"] == pytest.approx(APORTE)
    assert eq["pago_medio_anual"] == pytest.approx(base.compensacion.mean())
    assert eq["prob_cobrar"] == pytest.approx((base.danio >= 0.5).mean())


# ------------------------------------------------------------ sensibilidad
def test_criterio_de_mejor():
    ind = {"sin_proteccion": {"van_media": 30, "van_p5": -1},
           "fondo": {"van_media": 20, "van_p5": 5},
           "malla": {"van_media": 10, "van_p5": 8}}
    assert sens.elegir_mejor(ind, 0) == 1           # sin protección queda afuera por P5 < 0
    assert sens.elegir_mejor(ind, 6) == 2
    assert sens.elegir_mejor(ind, 100) == sens.NINGUNA


def test_barrido_de_precio_en_el_precio_base_coincide(base):
    b = sens.barrido_precio(base, [base.parametros.precio_uva])
    assert b["por_alternativa"]["fondo"]["van_media"][0] == pytest.approx(
        mc.indicadores(base)["fondo"]["van_media"])


def test_persistencia_misma_proporcion_de_G(base):
    pers = sens.persistencia(base.parametros, base)
    assert pers["independiente"]["proporcion_G"] == pytest.approx(pers["markov"]["proporcion_G"], abs=0.01)
    assert pers["markov"]["racha_G_media"] > pers["independiente"]["racha_G_media"]
