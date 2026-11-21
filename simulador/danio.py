"""
Módulo 4 – Daño por granizada (TP4).

La distribución de daño por evento es un SUPUESTO (ver supuestos.py).
Si hay varios eventos en el año, el daño se combina como lo hace el Fondo
Compensador: cada granizada se aplica sobre lo que quedó de la anterior.

    daño del año = 1 − (1 − d1)(1 − d2)…(1 − dk)
"""

from . import datos_reales as R


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
