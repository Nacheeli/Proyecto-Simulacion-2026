"""
Módulo 4 – Daño por granizada (TP4).

La distribución de daño por evento es un SUPUESTO (ver supuestos.py). Es
continua por intervalos: cada intervalo [desde, hasta] tiene una probabilidad
y dentro de él el daño es uniforme. Se sortea con UN número aleatorio por la
transformada inversa de la función de distribución, que es lineal por tramos:

    si F(i-1) <= u < F(i):   daño = desde_i + (u − F(i-1)) / p_i · (hasta_i − desde_i)

Un intervalo con desde = hasta es un valor puntual (el daño 0).

Si hay varios eventos en el año, el daño se combina como lo hace el Fondo
Compensador: cada granizada se aplica sobre lo que quedó de la anterior.

    daño del año = 1 − (1 − d1)(1 − d2)…(1 − dk)
"""

from . import datos_reales as R


class TablaDanio:
    def __init__(self, desde, hasta, probabilidades):
        if not (len(desde) == len(hasta) == len(probabilidades)) or not desde:
            raise ValueError("La tabla de daño tiene columnas de distinto largo")
        if abs(sum(probabilidades) - 1) > 1e-6:
            raise ValueError(f"Las probabilidades suman {sum(probabilidades)}, deben sumar 1")
        for a, b in zip(desde, hasta):
            if not 0 <= a <= b <= 1:
                raise ValueError("Cada intervalo debe cumplir 0 <= desde <= hasta <= 1")
        self.desde, self.hasta, self.probabilidades = list(desde), list(hasta), list(probabilidades)
        self.acumuladas = []
        acumulada = 0.0
        for p in probabilidades:
            acumulada += p
            self.acumuladas.append(acumulada)
        self.acumuladas[-1] = 1.0

    def inversa(self, u):
        anterior = 0.0
        for a, b, p, acumulada in zip(self.desde, self.hasta, self.probabilidades, self.acumuladas):
            if u < acumulada:
                if b == a or p == 0:
                    return a
                return a + (u - anterior) / p * (b - a)
            anterior = acumulada
        return self.hasta[-1]

    def media(self):
        return sum(p * (a + b) / 2 for a, b, p in zip(self.desde, self.hasta, self.probabilidades))


DANIO_ALTO_DESDE = 0.40   # intervalos que escala el factor de severidad (40–60, 60–80, 80–100 %)


def aplicar_severidad(desde, probabilidades, factor, alto_desde=DANIO_ALTO_DESDE):
    """Factor de severidad (SUPUESTO): multiplica la probabilidad de los intervalos
    de daño alto (los que empiezan en 40 % o más) y renormaliza el resto para que
    la suma siga siendo 1. factor = 1 deja la tabla igual.
    """
    altos = [a >= alto_desde for a in desde]
    p_alto = sum(p for p, es in zip(probabilidades, altos) if es)
    p_resto = 1 - p_alto
    nuevo_alto = factor * p_alto
    if nuevo_alto > 1 + 1e-12 or (p_resto <= 0 and factor != 1):
        raise ValueError(f"Factor de severidad {factor} demasiado alto: los daños altos superan el 100 %")
    escala_resto = (1 - nuevo_alto) / p_resto if p_resto > 0 else 0.0
    return [p * factor if es else p * escala_resto for p, es in zip(probabilidades, altos)]


def combinar_danios(danios):
    """Daño total del año a partir de los daños de cada evento (fracciones 0–1)."""
    sano = 1.0
    for d in danios:
        sano *= (1 - d)
    return 1 - sano


def danios_con_malla(danios, eficacia):
    """La malla reduce cada granizada en 'eficacia' (0,90 = deja pasar el 10 %)."""
    return [d * (1 - eficacia) for d in danios]


def referencia_dacc(superficie_cultivada_sur):
    """Tasas anuales de daño de referencia (fracción de la superficie llevada al 100 %).

    Usa las ha dañadas del Oasis Sur con y sin lucha antigranizo dividido por la
    superficie cultivada del oasis (este último es un SUPUESTO).
    """
    return {
        "con_lucha": R.DACC_HA_SUR_CON_LUCHA / superficie_cultivada_sur,
        "sin_lucha": R.DACC_HA_SUR_SIN_LUCHA / superficie_cultivada_sur,
    }
