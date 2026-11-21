"""
Reporte de verificación del modelo, para el informe.  Ejecutar:  python verificar.py
"""

from dataclasses import replace

import numpy as np

from simulador import datos_reales as R
from simulador import montecarlo as mc
from simulador import sensibilidad as sens
from simulador import estadistica as est
from simulador.clima import CadenaMarkov
from simulador.danio import referencia_dacc
from simulador.finca import ALTERNATIVAS, NOMBRES, compensacion_fondo, evaluar, van
from simulador.generador import GeneradorLCG, prueba_chi_cuadrado
from simulador.parametros import Parametros

LINEA = "=" * 78


def m(x):
    return f"{x / 1e6:9.2f} M"


def tabla(ind, filas):
    print(f"   {'':26}" + "".join(f"{NOMBRES[a]:>18}" for a in ALTERNATIVAS))
    for clave, titulo in filas:
        if clave.startswith("pct"):
            print(f"   {titulo:26}" + "".join(f"{ind[a][clave]:17.1f}%" for a in ALTERNATIVAS))
        else:
            print(f"   {titulo:26}" + "".join(f"{ind[a][clave] / 1e6:16.2f} M" for a in ALTERNATIVAS))


def main():
    p = Parametros()
    print(LINEA)
    print("1. Generador congruencial – prueba chi-cuadrado")
    chi = prueba_chi_cuadrado(GeneradorLCG(p.semilla, p.lcg_a, p.lcg_c, p.lcg_m).generar(10_000))
    print(f"   a={p.lcg_a}  c={p.lcg_c}  m={p.lcg_m}  semilla={p.semilla}")
    print(f"   χ² = {chi['estadistico']:.3f}   crítico(9; 0,05) = {chi['critico']:.3f}   "
          f"→ {'no se rechaza' if chi['acepta_h0'] else 'SE RECHAZA'} H0")

    print(LINEA)
    print(f"2-3. Clima: {p.replicas} réplicas × {p.anios} años")
    res = mc.correr(p)
    rc = mc.resumen_clima(res)
    pi_s, pi_g = CadenaMarkov(p.p_s_a_g, p.p_g_a_s).estacionaria()
    print(f"   Estacionaria teórica  S={pi_s:.3f} G={pi_g:.3f}   (documento: 0,36 / 0,64)")
    print(f"   Proporción simulada   S={1 - rc['proporcion_G']:.3f} G={rc['proporcion_G']:.3f}")
    valores, _, probs = R.tabla_dias_granizo()
    print("   días   real    simulado")
    for v, q in zip(valores, probs):
        print(f"   {v:>4}  {q:6.3f}   {rc['frecuencia_dias'].get(v, 0):6.3f}")

    print(LINEA)
    print("4. Daño (tabla SUPUESTA, continua por intervalos) vs referencia DACC")
    d = referencia_dacc(p.superficie_cultivada_sur)
    print(f"   daño medio por granizada  {rc['danio_medio_evento']:.4f}")
    print(f"   pérdida media anual       {rc['danio_medio_anual']:.4f}   "
          f"(DACC Sur {d['con_lucha']:.3f} – {d['sin_lucha']:.3f})")
    print(f"   P(daño del año > 50 %)    {rc['prob_danio_supera_umbral']:.4f}")
    print(f"   P(daño del año = 50 %)    {rc['prob_danio_igual_umbral']:.4f}   (debe ser 0)")
    eq = mc.equilibrio_fondo(res)
    print(f"   Fondo: P(cobrar) {eq['prob_cobrar']:.4f}/año · pago medio {m(eq['pago_medio_anual'])} · "
          f"aporte {m(eq['aporte_anual'])} · pagos/aportes {eq['pagos_sobre_aportes']:.2f}")
    otra = mc.indicadores(mc.evaluar_escenarios(res.esc, replace(p, fca_condicion=">")))["fondo"]
    base = mc.indicadores(res)["fondo"]
    print(f"   Condición '>=' vs '>': VAN medio {m(base['van_media'])} vs {m(otra['van_media'])}, "
          f"P5 {m(base['van_p5'])} vs {m(otra['van_p5'])}")

    print(LINEA)
    print("5. Casos a mano (rendimiento 7.350 kg/ha, condición '>=')")
    for danio in (0.0, 0.40, 0.499, 0.50, 0.60):
        r = evaluar([danio], [danio * (1 - p.malla_eficacia)], [7350], p)
        comp = compensacion_fondo([danio], p)[0]
        print(f"   daño {danio * 100:5.1f} %: compensación {m(comp)} | sin {m(r['sin_proteccion'][0])} "
              f"fondo {m(r['fondo'][0])} malla {m(r['malla'][0])}")
    anualidad = 1e6 * (1 - 1.05 ** -20) / 0.05
    print(f"   VAN de 1 M/año, 20 años, 5 %: {van(np.full(20, 1e6), 0.05):,.2f} "
          f"(fórmula de anualidad {anualidad:,.2f})")
    vans = []
    for modo in ("amortizado", "contado", "financiado"):
        pm = replace(p, malla_modo_pago=modo, malla_tasa_anual=p.tasa_descuento)
        vans.append(mc.indicadores(mc.evaluar_escenarios(res.esc, pm))["malla"]["van_media"])
    print("   VAN medio malla (crédito = descuento): " +
          "  ".join(f"{k} {m(v)}" for k, v in zip(("amortizado", "contado", "financiado"), vans)))

    print(LINEA)
    print(f"6. Monte Carlo – indicadores (tasa de descuento {p.tasa_descuento:.0%})")
    ind = mc.indicadores(res)
    tabla(ind, [("van_media", "VAN medio"), ("van_desvio", "VAN desvío"), ("van_p5", "VAN P5"),
                ("pct_van_negativo", "% réplicas VAN < 0"), ("media", "suma sin descontar"),
                ("p5", "suma sin descontar P5"), ("pct_anios_perdida", "% años con pérdida"),
                ("p1_anual", "percentil 1 anual"), ("peor_anio", "peor año")])
    mejor = sens.elegir_mejor(ind, p.criterio_p5_minimo)
    print(f"   Mejor (mayor VAN medio con P5 > 0): {NOMBRES[ALTERNATIVAS[mejor]] if mejor >= 0 else 'ninguna'}")

    print(LINEA)
    print("7. Sensibilidad al precio de la uva")
    precios = np.arange(200, 1201, 50)
    b = sens.barrido_precio(res, precios)
    print("   precio  " + "".join(f"{NOMBRES[a]:>18}" for a in ALTERNATIVAS) + "   mejor")
    for k, pr in enumerate(precios):
        fila = "".join(f"{b['por_alternativa'][a]['van_media'][k] / 1e6:16.1f} M" for a in ALTERNATIVAS)
        mj = b["mejor"][k]
        print(f"   {pr:6.0f}  {fila}   {NOMBRES[ALTERNATIVAS[mj]] if mj >= 0 else 'ninguna'}")

    print(LINEA)
    print("8. Hectáreas: con costo fijo 0 el VAN escala exactamente con las ha")
    for ha in (1, 10, 30):
        otra = mc.evaluar_escenarios(res.esc, replace(p, hectareas=ha))
        err = max(float(np.max(np.abs(otra.van[a] - res.van[a] * ha / p.hectareas))) for a in ALTERNATIVAS)
        print(f"   {ha:3d} ha: error máximo |VAN(ha) − VAN(5,3)·ha/5,3| = {err:.2e} $")
    print(f"   Por encima de {p.fca_max_hectareas:.0f} ha el Fondo no está disponible (límite real).")

    letras = {-1: "·", 0: "S", 1: "F", 2: "M"}
    print(LINEA)
    print(f"9. Severidad del daño ({p.replicas} réplicas por factor)")
    factores = np.round(np.arange(0.25, 3.001, 0.25), 2)
    precios_m = np.arange(200, 1001, 50)
    sev = sens.analisis_severidad(p, factores, precios_m, np.arange(1, 61), replicas=p.replicas)
    print("   factor  P(paga)  pérdida  pagos/aportes  DACC   VAN sin / Fondo / malla (M)      P5 sin / Fondo / malla (M)   mejor")
    for i, fct in enumerate(factores):
        vm = " / ".join(f"{sev['van_media'][a][i] / 1e6:6.1f}" for a in ALTERNATIVAS)
        v5 = " / ".join(f"{sev['van_p5'][a][i] / 1e6:6.1f}" for a in ALTERNATIVAS)
        mj = sev["mejor"][i]
        print(f"   ×{fct:4.2f}  {sev['prob_paga'][i]:7.3f}  {sev['perdida_media'][i]:7.3f}  {sev['pagos_sobre_aportes'][i]:13.2f}  "
              f"{'sí' if sev['dentro_dacc'][i] else 'no':4}   {vm}   {v5}   {letras[mj]}")
    fino = np.round(np.arange(0.20, 0.601, 0.025), 3)
    sev_f = sens.analisis_severidad(p, fino, [p.precio_uva], [p.hectareas], replicas=p.replicas)
    print("   Barrido fino del cruce: " + " ".join(f"×{x:.3f}:{letras[m]}" for x, m in zip(fino, sev_f["mejor"])))
    for a_, b_, m1, m2 in sens.factor_cambio_fondo(sev_f):
        k = list(fino).index(b_)
        print(f"   → el Fondo cambia entre ×{a_:.3f} y ×{b_:.3f} ({letras[m1]} → {letras[m2]}); "
              f"pagos/aportes ≈ {sev_f['pagos_sobre_aportes'][k]:.2f}, pérdida media ≈ {sev_f['perdida_media'][k]:.3f}")
    print("   Mapa precio (200–1000, paso 50) × severidad   (S sin protección, F Fondo, M malla, · ninguna)")
    for i, fct in enumerate(factores):
        print(f"   ×{fct:4.2f}  " + "".join(letras[x] for x in sev["mapa_precio"][i]))
    print("   Mapa hectáreas (1–60) × severidad")
    for i, fct in enumerate(factores):
        print(f"   ×{fct:4.2f}  " + "".join(letras[x] for x in sev["mapa_ha"][i]))

    print(LINEA)
    print("10. Persistencia: cadena de Markov real vs años independientes (misma proporción de G)")
    pers = sens.persistencia(p, res)
    for nombre in ("markov", "independiente"):
        x = pers[nombre]
        print(f"   {nombre:13} G={x['proporcion_G']:.3f}  racha máx. media G={x['racha_G_media']:.1f} años  "
              f"P(2+ años fuertes seguidos)={x['prob_2_fuertes_seguidos']:.3f}")
    print(f"   {'':26}" + "".join(f"{NOMBRES[a][:10] + ' Mk/Ind':>22}" for a in ALTERNATIVAS))
    for clave, titulo in (("van_media", "VAN medio"), ("van_p5", "VAN P5"), ("van_desvio", "VAN desvío")):
        celdas = "".join(f"{pers['markov']['indicadores'][a][clave] / 1e6:10.2f} /{pers['independiente']['indicadores'][a][clave] / 1e6:7.2f} M"
                         for a in ALTERNATIVAS)
        print(f"   {titulo:26}{celdas}")

    print(LINEA)
    print("11. Precisión: intervalos de confianza del 95 % (media ± 1,96·s/√n)")
    for a, ic in est.ic_van(res).items():
        print(f"   {NOMBRES[a]:20} VAN medio {ic['media'] / 1e6:8.3f} M ± {ic['semiancho'] / 1e6:.3f} M "
              f"[{ic['inferior'] / 1e6:.3f} ; {ic['superior'] / 1e6:.3f}]")
    print("   Diferencias de VAN medio: números aleatorios comunes (NAC) vs corridas independientes "
          f"(semilla {p.semilla + 1} para la segunda alternativa)")
    dif = est.ic_diferencias(res, est.corrida_independiente(p))
    for (a, b), fila in dif.items():
        nac, ind_ = fila["nac"], fila["independiente"]
        print(f"   {NOMBRES[a]:18} − {NOMBRES[b]:18} {nac['media'] / 1e6:7.3f} M  NAC ± {nac['semiancho'] / 1e6:.3f}  "
              f"indep. ± {ind_['semiancho'] / 1e6:.3f}  → {fila['reduccion']:.1f} veces más angosto "
              f"(varianza {fila['reduccion'] ** 2:.1f} veces menor), correlación {fila['correlacion']:.3f}")
    print("   Convergencia (prefijos de una corrida de 50.000 réplicas):")
    conv = est.convergencia(p, (100, 500, 1000, 5000, 10_000, 50_000))
    print("   réplicas  " + "".join(f"{NOMBRES[a]:>26}" for a in ALTERNATIVAS))
    for k, n in enumerate(conv["tamanios"]):
        print(f"   {n:8d}  " + "".join(f"{conv[a]['media'][k] / 1e6:15.3f} ± {conv[a]['semiancho'][k] / 1e6:6.3f} M"
                                       for a in ALTERNATIVAS))
    for a in ALTERNATIVAS:
        s = conv[a]["semiancho"]
        print(f"   {NOMBRES[a]:20} semiancho 10.000/50.000 = {s[4] / s[5]:.3f} (√5 = {5 ** 0.5:.3f}); "
              f"100/10.000 = {s[0] / s[4]:.2f} (√100 = 10)")
    print("   Corte de severidad (VAN Fondo − VAN Sin, NAC, 10.000 réplicas por factor):")
    filas = est.ic_corte_severidad(p, np.round(np.arange(0.25, 0.3501, 0.0125), 4))
    for f_ in filas:
        print(f"   ×{f_['factor']:.4f}  {f_['media'] / 1e6:7.3f} M ± {f_['semiancho'] / 1e6:.3f}")
    cr = est.cruce_severidad(filas)
    print(f"   → corte ×{cr['estimado']:.3f}  (IC 95 % ×{cr['inferior']:.3f} a ×{cr['superior']:.3f})")

    print(LINEA)
    print("12. Precio de corte de la malla: $/kg, USD/kg y tasa de descuento")
    for t, c in est.cortes_por_tasa(res.esc, p, (0.03, 0.05, 0.08)).items():
        print(f"   tasa {t:.0%}: malla = Fondo en {c['fondo']['pesos_kg']:7.1f} $/kg = {c['fondo']['usd_kg']:.3f} USD/kg ; "
              f"malla = Sin en {c['sin_proteccion']['pesos_kg']:7.1f} $/kg = {c['sin_proteccion']['usd_kg']:.3f} USD/kg")
    print(f"   Tipo de cambio ×0,5 / ×1 / ×2 (precio en USD/kg de corte):")
    for factor in (0.5, 1.0, 2.0):
        c = est.corte_escalando_tipo_de_cambio(res.esc, p, factor)
        print(f"   TC {p.tipo_cambio * factor:7.0f} $/USD: contra Sin {c['sin_proteccion']['usd_kg']:.4f}  "
              f"contra Fondo {c['fondo']['usd_kg']:.4f}")
    print("   → contra Sin no depende del tipo de cambio; contra el Fondo sí (aporte y compensación fijos en pesos).")

    otra_corrida = mc.indicadores(mc.correr(Parametros(semilla=p.semilla)))
    print(LINEA)
    print(f"Repetibilidad con la misma semilla: {'OK' if otra_corrida == ind else 'FALLA'}")


if __name__ == "__main__":
    main()
