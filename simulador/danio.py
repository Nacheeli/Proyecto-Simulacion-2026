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
