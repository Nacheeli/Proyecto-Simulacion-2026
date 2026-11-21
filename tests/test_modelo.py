"""
Pruebas del modelo (sin abrir la ventana).  Ejecutar:  python -m pytest
"""

import pytest

from simulador import datos_reales as R
from simulador import montecarlo as mc
from simulador.clima import CadenaMarkov, TablaEmpirica
from simulador.danio import combinar_danios, danios_con_malla
from simulador.finca import compensacion_fondo, costo_malla_por_anio, evaluar
from simulador.generador import GeneradorLCG, prueba_chi_cuadrado
from simulador.parametros import Parametros


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


def test_simulacion_reproduce_tabla_real_y_estacionaria():
    p = Parametros(replicas=10_000)
    res = mc.correr(p)
    resumen = mc.resumen_clima(res)
    valores, _, probs = R.tabla_dias_granizo()
    for v, q in zip(valores, probs):
        assert abs(resumen["frecuencia_dias"].get(v, 0) - q) < 0.02, v
    assert abs(resumen["proporcion_G"] - 0.645) < 0.01
    assert abs(resumen["media_dias"] - 1.40) < 0.05


# -------------------------------------------------------------------- daño
def test_combinacion_de_danios():
    assert combinar_danios([]) == 0
    assert combinar_danios([0.3, 0.5]) == pytest.approx(0.65)   # 1 − 0,7·0,5
    assert combinar_danios(danios_con_malla([0.6], 0.9)) == pytest.approx(0.06)


# ------------------------------------------------------- casos a mano: finca
P = Parametros(hectareas=5.3, precio_uva=400, costo_produccion_ha=2_200_000,
               tipo_cambio=1450, malla_costo_usd_ha=4250, malla_vida_util=15)
REND = 7350.0
INGRESO_SANO = 5.3 * 7350 * 400           # 15.582.000
COSTO_PROD = 5.3 * 2_200_000              # 11.660.000
APORTE = 5.3 * 51_000                     # 270.300
MALLA_ANUAL = 4250 * 1450 * 5.3 / 15      # 2.177.416,67


def test_anio_sin_granizo():
    r = evaluar([0.0], [0.0], [REND], P)
    assert r["sin_proteccion"][0] == pytest.approx(INGRESO_SANO - COSTO_PROD)              # 3.922.000
    assert r["fondo"][0] == pytest.approx(INGRESO_SANO - COSTO_PROD - APORTE)              # 3.651.700
    assert r["malla"][0] == pytest.approx(INGRESO_SANO - COSTO_PROD - MALLA_ANUAL)


def test_anio_con_60_por_ciento_paga_el_fondo():
    r = evaluar([0.60], [0.06], [REND], P)
    compensacion = 2_000_000 * 5.3 * 0.60                                                 # 6.360.000
    assert compensacion_fondo([0.60], P)[0] == pytest.approx(compensacion)
    assert r["sin_proteccion"][0] == pytest.approx(INGRESO_SANO * 0.4 - COSTO_PROD)
    assert r["fondo"][0] == pytest.approx(INGRESO_SANO * 0.4 - COSTO_PROD - APORTE + compensacion)
    assert r["malla"][0] == pytest.approx(INGRESO_SANO * 0.94 - COSTO_PROD - MALLA_ANUAL)


def test_anio_con_40_por_ciento_no_paga_el_fondo():
    r = evaluar([0.40], [0.04], [REND], P)
    assert compensacion_fondo([0.40], P)[0] == 0
    assert r["fondo"][0] == pytest.approx(INGRESO_SANO * 0.6 - COSTO_PROD - APORTE)


def test_umbral_exacto_no_paga_y_modo_fijo():
    assert compensacion_fondo([0.50], P)[0] == 0          # debe SUPERAR el 50 %
    fijo = Parametros(fca_modo="fijo", hectareas=5.3)
    assert compensacion_fondo([0.60], fijo)[0] == pytest.approx(2_000_000 * 5.3)


def test_varios_eventos_combinados_activan_el_fondo():
    # 30 % y 50 % por separado no superan el umbral, combinados dan 65 %
    assert compensacion_fondo([combinar_danios([0.3, 0.5])], P)[0] > 0


def test_formas_de_pago_de_la_malla_cuestan_lo_mismo_sin_interes():
    """20 años, vida 15: amortizado = 20/15 mallas; contado = 2 mallas − residual 10/15."""
    costo = 4250 * 1450 * 5.3
    for modo in ("amortizado", "contado", "financiado"):
        p = Parametros(anios=20, malla_vida_util=15, malla_modo_pago=modo, malla_tasa_anual=0.0,
                       malla_costo_usd_ha=4250, tipo_cambio=1450, hectareas=5.3)
        assert costo_malla_por_anio(p).sum() == pytest.approx(costo * 20 / 15), modo


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
    # el Fondo difiere de "sin protección" solo por el aporte, salvo cuando compensa
    sin_comp = res.danio <= res.parametros.fca_umbral
    aporte = res.parametros.fca_aporte_ha * res.parametros.hectareas
    assert (abs((sin - fondo)[sin_comp] - aporte) < 1e-6).all()
