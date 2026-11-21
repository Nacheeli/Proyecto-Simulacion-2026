"""
Módulo 1 – Números aleatorios (TP2).

Generador congruencial lineal mixto:  X(n+1) = (a·X(n) + c) mod m,  U = X / m.
Todo el proyecto usa este generador; no se usa random ni numpy.random.
"""

from statistics import NormalDist

# Parámetros por defecto (Numerical Recipes). Cumplen Hull–Dobell para m = 2^32:
# c impar y a − 1 múltiplo de 4, así que el período es completo (m).
A_DEFECTO = 1_664_525
C_DEFECTO = 1_013_904_223
M_DEFECTO = 2 ** 32


class GeneradorLCG:
    def __init__(self, semilla=12345, a=A_DEFECTO, c=C_DEFECTO, m=M_DEFECTO):
        if m <= 0 or not (0 < a < m) or not (0 <= c < m):
            raise ValueError("Parámetros del congruencial inválidos")
        self.a, self.c, self.m = int(a), int(c), int(m)
        self.semilla = int(semilla) % self.m
        self.x = self.semilla
        self.cantidad_generada = 0

    def siguiente(self):
        """Devuelve el próximo número pseudoaleatorio en [0, 1)."""
        self.x = (self.a * self.x + self.c) % self.m
        self.cantidad_generada += 1
        return self.x / self.m

    def generar(self, n):
        return [self.siguiente() for _ in range(n)]

    def uniforme(self, minimo, maximo):
        return minimo + (maximo - minimo) * self.siguiente()


# Valores críticos de chi-cuadrado de tabla (cola derecha), gl 1 a 30.
TABLA_CHI2 = {
    0.05: [3.841, 5.991, 7.815, 9.488, 11.070, 12.592, 14.067, 15.507, 16.919, 18.307,
           19.675, 21.026, 22.362, 23.685, 24.996, 26.296, 27.587, 28.869, 30.144, 31.410,
           32.671, 33.924, 35.172, 36.415, 37.652, 38.885, 40.113, 41.337, 42.557, 43.773],
    0.01: [6.635, 9.210, 11.345, 13.277, 15.086, 16.812, 18.475, 20.090, 21.666, 23.209,
           24.725, 26.217, 27.688, 29.141, 30.578, 32.000, 33.409, 34.805, 36.191, 37.566,
           38.932, 40.289, 41.638, 42.980, 44.314, 45.642, 46.963, 48.278, 49.588, 50.892],
}


def critico_wilson_hilferty(grados_libertad, alfa=0.05):
    """Aproximación de Wilson–Hilferty al valor crítico de chi-cuadrado."""
    z = NormalDist().inv_cdf(1 - alfa)
    k = grados_libertad
    return k * (1 - 2 / (9 * k) + z * (2 / (9 * k)) ** 0.5) ** 3


def valor_critico_chi2(grados_libertad, alfa=0.05):
    """Valor crítico de chi-cuadrado: de tabla si está (gl 1–30, α 0,05 o 0,01),
    si no, aproximación de Wilson–Hilferty."""
    tabla = TABLA_CHI2.get(alfa)
    if tabla is not None and 1 <= grados_libertad <= len(tabla):
        return tabla[grados_libertad - 1]
    return critico_wilson_hilferty(grados_libertad, alfa)


def origen_critico_chi2(grados_libertad, alfa=0.05):
    tabla = TABLA_CHI2.get(alfa)
    return "tabla" if tabla is not None and 1 <= grados_libertad <= len(tabla) else "Wilson–Hilferty"


def prueba_chi_cuadrado(numeros, intervalos=10, alfa=0.05):
    """Prueba de frecuencias (bondad de ajuste a la uniforme) con chi-cuadrado.

    H0: los números provienen de una U(0,1).
    """
    n = len(numeros)
    observadas = [0] * intervalos
    for u in numeros:
        observadas[min(int(u * intervalos), intervalos - 1)] += 1
    esperada = n / intervalos
    estadistico = sum((o - esperada) ** 2 / esperada for o in observadas)
    gl = intervalos - 1
    critico = valor_critico_chi2(gl, alfa)
    return {
        "n": n,
        "intervalos": intervalos,
        "observadas": observadas,
        "esperada": esperada,
        "estadistico": estadistico,
        "grados_libertad": gl,
        "alfa": alfa,
        "critico": critico,
        "origen_critico": origen_critico_chi2(gl, alfa),
        "acepta_h0": estadistico <= critico,
    }
