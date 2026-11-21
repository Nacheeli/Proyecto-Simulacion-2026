"""
Reporte de verificación del modelo, para el informe.  Ejecutar:  python verificar.py
"""

from simulador import datos_reales as R
from simulador import montecarlo as mc
from simulador.clima import CadenaMarkov
from simulador.danio import referencia_dacc
from simulador.finca import ALTERNATIVAS, NOMBRES, compensacion_fondo, evaluar
from simulador.generador import GeneradorLCG, prueba_chi_cuadrado
from simulador.parametros import Parametros


def m(x):
    return f"{x / 1e6:12.3f} M"


def main():
    p = Parametros()
    print("=" * 70)
    print("1. Generador congruencial – prueba chi-cuadrado")
    chi = prueba_chi_cuadrado(GeneradorLCG(p.semilla, p.lcg_a, p.lcg_c, p.lcg_m).generar(10_000))
    print(f"   a={p.lcg_a}  c={p.lcg_c}  m={p.lcg_m}  semilla={p.semilla}")
    print(f"   observadas: {chi['observadas']}  (esperada {chi['esperada']:.0f})")
    print(f"   χ² = {chi['estadistico']:.3f}   crítico(9; 0,05) = {chi['critico']:.3f}   "
          f"→ {'no se rechaza' if chi['acepta_h0'] else 'SE RECHAZA'} H0")

    print("=" * 70)
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
    print(f"   media {1.404:6.3f}   {rc['media_dias']:6.3f}   varianza 2,333 / {rc['varianza_dias']:.3f}")

    print("=" * 70)
    print("4. Daño (tabla SUPUESTA) vs referencia DACC")
    d = referencia_dacc(p.superficie_cultivada_sur)
    print(f"   daño medio por granizada {rc['danio_medio_evento']:.3f}")
    print(f"   pérdida media anual      {rc['danio_medio_anual']:.3f}   "
          f"(DACC Sur {d['con_lucha']:.3f} – {d['sin_lucha']:.3f})")
    print(f"   P(daño del año > 50 %)   {rc['prob_danio_supera_umbral']:.3f}")

    print("=" * 70)
    print("5. Casos a mano (rendimiento 7.350 kg/ha)")
    for danio in (0.0, 0.40, 0.60):
        r = evaluar([danio], [danio * (1 - p.malla_eficacia)], [7350], p)
        comp = compensacion_fondo([danio], p)[0]
        print(f"   daño {danio:4.0%}: compensación {m(comp)} | sin {m(r['sin_proteccion'][0])} "
              f"fondo {m(r['fondo'][0])} malla {m(r['malla'][0])}")

    print("=" * 70)
    print("6. Monte Carlo – indicadores")
    ind = mc.indicadores(res)
    print(f"   {'':22}" + "".join(f"{NOMBRES[a]:>20}" for a in ALTERNATIVAS))
    for clave, titulo in (("media", "media 20 años"), ("desvio", "desvío"), ("p5", "P5"),
                          ("peor_anio", "peor año")):
        print(f"   {titulo:22}" + "".join(f"{ind[a][clave] / 1e6:18.2f} M" for a in ALTERNATIVAS))
    print(f"   {'% años con pérdida':22}" + "".join(f"{ind[a]['pct_anios_perdida']:19.1f}%" for a in ALTERNATIVAS))

    otra = mc.indicadores(mc.correr(Parametros(semilla=p.semilla)))
    print("=" * 70)
    print(f"Repetibilidad con la misma semilla: {'OK' if otra == ind else 'FALLA'}")


if __name__ == "__main__":
    main()
