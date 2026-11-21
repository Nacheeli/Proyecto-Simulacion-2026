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


def valor_critico_chi2(grados_libertad, alfa=0.05):
    """Valor crítico de chi-cuadrado (aproximación de Wilson–Hilferty)."""
    z = NormalDist().inv_cdf(1 - alfa)
    k = grados_libertad
    return k * (1 - 2 / (9 * k) + z * (2 / (9 * k)) ** 0.5) ** 3


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
        "acepta_h0": estadistico <= critico,
    }
