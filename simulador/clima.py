"""
Módulos 2 y 3 – Clima.

2) Cadena de Markov de dos estados (TP5): año con granizo (G) / sin granizo (S).
3) Días con granizo en el año (TP4): tabla empírica real con transformada
   inversa (no Poisson: la varianza 2,33 supera a la media 1,40).

Cómo se combinan: la cadena decide si el año tiene granizo. Si el año es S,
hay 0 días. Si es G, los días se sortean de la tabla empírica condicionada a
"al menos 1 día" (las frecuencias reales de 1 a 7 días, renormalizadas).
Así la frecuencia de 0 días la fija la cadena (estacionaria S = 0,36, contra
0,34 de la tabla real) y la forma de 1 a 7 días la fija la tabla real.
"""


class TablaEmpirica:
    """Variable aleatoria discreta por transformada inversa."""

    def __init__(self, valores, probabilidades):
        if len(valores) != len(probabilidades) or not valores:
            raise ValueError("Valores y probabilidades deben tener el mismo largo")
        total = sum(probabilidades)
        if abs(total - 1) > 1e-6:
            raise ValueError(f"Las probabilidades suman {total}, deben sumar 1")
        self.valores = list(valores)
        self.probabilidades = list(probabilidades)
        self.acumuladas = []
        acumulada = 0.0
        for p in probabilidades:
            acumulada += p
            self.acumuladas.append(acumulada)
        self.acumuladas[-1] = 1.0  # evita errores de redondeo

    def inversa(self, u):
        """Devuelve el primer valor cuya acumulada supera a u."""
        for valor, acumulada in zip(self.valores, self.acumuladas):
            if u < acumulada:
                return valor
        return self.valores[-1]

    def media(self):
        return sum(v * p for v, p in zip(self.valores, self.probabilidades))

    def varianza(self):
        m = self.media()
        return sum(p * (v - m) ** 2 for v, p in zip(self.valores, self.probabilidades))


class CadenaMarkov:
    """Cadena de dos estados: 'S' (sin granizo) y 'G' (con granizo)."""

    def __init__(self, p_s_a_g, p_g_a_s):
        self.p_s_a_g = p_s_a_g
        self.p_g_a_s = p_g_a_s

    def matriz(self):
        return [
            [1 - self.p_s_a_g, self.p_s_a_g],   # desde S: [->S, ->G]
            [self.p_g_a_s, 1 - self.p_g_a_s],   # desde G: [->S, ->G]
        ]

    def estacionaria(self):
        """Devuelve (pi_S, pi_G)."""
        total = self.p_s_a_g + self.p_g_a_s
        if total == 0:
            return 0.5, 0.5
        return self.p_g_a_s / total, self.p_s_a_g / total

    def estado_inicial(self, u, modo="estacionaria"):
        if modo in ("S", "G"):
            return modo
        _, pi_g = self.estacionaria()
        return "G" if u < pi_g else "S"

    def siguiente(self, estado, u):
        if estado == "S":
            return "G" if u < self.p_s_a_g else "S"
        return "S" if u < self.p_g_a_s else "G"


def tabla_dias_condicional(valores, probabilidades):
    """Tabla de días para un año G: la tabla real sin el 0, renormalizada."""
    pares = [(v, p) for v, p in zip(valores, probabilidades) if v > 0]
    total = sum(p for _, p in pares)
    return TablaEmpirica([v for v, _ in pares], [p / total for _, p in pares])
