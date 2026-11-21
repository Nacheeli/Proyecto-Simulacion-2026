"""
Malla antigranizo, seguro o nada: simulación para decidir.
Interfaz gráfica (tkinter + matplotlib).

    simulador/  lógica del modelo (congelada en la v4)
    interfaz/   estilo, widgets, cálculos de la corrida y gráficos

Ejecutar:  python app.py
"""

import os
import tkinter as tk
from tkinter import messagebox

import matplotlib
matplotlib.use("TkAgg")

from interfaz import estilo as E
from interfaz import graficos as G
from interfaz.calculos import PASOS, calcular_todo
from interfaz.formato import fmt, fmt_m, fmt_pct, leer_numero
from interfaz.widgets import (FiguraTarjeta, FilaKPI, GrupoPlegable, PanelDesplazable, Pestanias, Tabla,
                              Tarjeta, boton, fuente, habilitar)
from simulador.finca import ALTERNATIVAS
from simulador.parametros import Parametros
from simulador.sensibilidad import NINGUNA

A = E.ALTERNATIVAS_ESTILO
CORTO = {"sin_proteccion": "Sin", "fondo": "Fondo", "malla": "Malla"}
CARPETA_FIGURAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figuras")
SEP = 16   # separación entre tarjetas

# ---------------------------------------------------------------------------
# Campos del panel izquierdo: (atributo, etiqueta, origen, escala, tipo)
#   origen: "R" dato real, "S" supuesto, "" parámetro de simulación
#   escala: el valor se muestra multiplicado por escala (100 → en %); lista = opciones
# ---------------------------------------------------------------------------
GRUPOS = [
    ("Simulación", False, [
        ("replicas", "Réplicas", "", 1, int),
        ("anios", "Años por réplica", "", 1, int),
        ("semilla", "Semilla", "", 1, int),
        ("replica_mostrar", "Réplica a mostrar en la pestaña 2", "", 1, int),
    ]),
    ("Generador congruencial", False, [
        ("lcg_a", "a (multiplicador)", "", 1, int),
        ("lcg_c", "c (incremento)", "", 1, int),
        ("lcg_m", "m (módulo)", "", 1, int),
    ]),
    ("Finca tipo (INV)", True, [
        ("hectareas", "Hectáreas", "R", 1, float),
        ("rendimiento_min", "Rendimiento mínimo (kg/ha)", "R", 1, float),
        ("rendimiento_max", "Rendimiento máximo (kg/ha)", "R", 1, float),
    ]),
    ("Clima – Markov (San Rafael Aero)", False, [
        ("p_s_a_g", "P(S → G)", "R", 1, float),
        ("p_g_a_s", "P(G → S)", "R", 1, float),
        ("estado_inicial", "Estado del año 1", "S", ["estacionaria", "G", "S"], str),
        ("frecuencia_mult", "Multiplicador de granizadas", "", 1, float),
        ("severidad", "Factor de severidad del daño", "S", 1, float),
    ]),
    ("Economía", True, [
        ("precio_uva", "Precio de la uva ($/kg)", "S", 1, float),
        ("costo_produccion_ha", "Costo de producción ($/ha/año)", "S", 1, float),
        ("tipo_cambio", "Tipo de cambio ($/USD)", "S", 1, float),
        ("tasa_descuento", "Tasa de descuento real (%)", "S", 100, float),
        ("costo_fijo_finca", "Costo fijo por finca ($/año)", "S", 1, float),
    ]),
    ("Fondo Compensador (Específica, Sur)", True, [
        ("fca_aporte_ha", "Aporte ($/ha/año)", "R", 1, float),
        ("fca_compensacion_ha", "Compensación ($/ha)", "R", 1, float),
        ("fca_umbral", "Umbral de daño (%)", "R", 100, float),
        ("fca_modo", "Compensación", "S", ["proporcional", "fijo"], str),
        ("fca_condicion", "Paga si el daño es … umbral", "S", [">=", ">"], str),
        ("fca_max_hectareas", "Máximo de hectáreas", "R", 1, float),
    ]),
    ("Malla antigranizo", True, [
        ("malla_costo_usd_ha", "Costo (USD/ha)", "R", 1, float),
        ("malla_vida_util", "Vida útil (años)", "R", 1, int),
        ("malla_eficacia", "Reducción del daño (%)", "S", 100, float),
        ("malla_modo_pago", "Forma de pago", "S", ["amortizado", "contado", "financiado"], str),
        ("malla_tasa_anual", "Tasa anual del crédito (%)", "S", 100, float),
        ("malla_cuotas", "Cuotas (años)", "S", 1, int),
    ]),
    ("Referencia DACC", False, [
        ("superficie_cultivada_sur", "Superficie cultivada Oasis Sur (ha)", "S", 1, float),
    ]),
    ("Sensibilidad (pestañas 4 y 5)", False, [
        ("sens_replicas", "Réplicas por factor de severidad", "", 1, int),
        ("sens_precio_min", "Precio desde ($/kg)", "", 1, float),
        ("sens_precio_max", "Precio hasta ($/kg)", "", 1, float),
        ("sens_precio_paso", "Precio paso ($/kg)", "", 1, float),
        ("sens_sev_min", "Severidad desde", "", 1, float),
        ("sens_sev_max", "Severidad hasta", "", 1, float),
        ("sens_sev_paso", "Severidad paso", "", 1, float),
        ("sens_ha_max", "Hectáreas hasta (mapa)", "", 1, int),
        ("conv_replicas_max", "Réplicas máximas (convergencia)", "", 1, int),
        ("criterio_p5_minimo", "Criterio: P5 del VAN mayor a ($)", "", 1, float),
    ]),
]


def mejor_texto(k):
    return A[ALTERNATIVAS[k]]["nombre"] if k != NINGUNA else "Ninguna"


def texto_ic_cruce(cr):
    if cr["inferior"] is None or cr["superior"] is None:
        return "IC 95 % fuera de ×0,25–×0,35"
    return f"IC 95 % ×{fmt(cr['inferior'], 3)}–×{fmt(cr['superior'], 3)}"


def mejor_corto(k):
    return A[ALTERNATIVAS[k]]["corto"] if k != NINGUNA else "Ninguna"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Malla antigranizo, seguro o nada – Simulación (UTN FRSR 2026)")
        self.configure(bg=E.FONDO)
        E.configurar_ttk(self)
        E.configurar_matplotlib()
        self.geometry("1400x860")
        self.minsize(1200, 720)
        try:
            self.state("zoomed")
        except tk.TclError:
            try:
                self.attributes("-zoomed", True)
            except tk.TclError:
                pass

        # escala de pantalla (1 = 96 dpi; 1,25 con el escalado de Windows al 125 %)
        try:
            self.escala = max(1.0, self.winfo_fpixels("1i") / 96.0)
        except tk.TclError:
            self.escala = 1.0
        self.variables, self.vars_danio = {}, []
        self.R = None
        self.figuras = {}          # clave -> FiguraTarjeta
        self.figuras_pestania = {}  # índice de pestaña -> [FiguraTarjeta]

        self.estado = tk.StringVar(value="Listo. Presioná «Calcular».")
        barra = tk.Label(self, textvariable=self.estado, anchor="w", bg=E.TARJETA, fg=E.TEXTO_2,
                         font=fuente(self, 9), padx=12, pady=4, highlightthickness=1, highlightbackground=E.BORDE)
        barra.pack(side=tk.BOTTOM, fill=tk.X)
        self._panel_izquierdo()
        self.pestanias = Pestanias(self, al_cambiar=self._al_cambiar_pestania)
        self.pestanias.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._pestania_clima(self.pestanias.agregar("1 · Clima y granizo"))
        self._pestania_corrida(self.pestanias.agregar("2 · Una corrida"))
        self._pestania_montecarlo(self.pestanias.agregar("3 · Monte Carlo"))
        self._pestania_decision(self.pestanias.agregar("4 · Decisión"))
        self._pestania_precision(self.pestanias.agregar("5 · Precisión"))
        self.after(200, self.calcular)

    # ================================================================ panel
    def _panel_izquierdo(self):
        panel = tk.Frame(self, bg=E.FONDO, width=int(345 * self.escala))
        panel.pack(side=tk.LEFT, fill=tk.Y)
        panel.pack_propagate(False)
        tk.Frame(self, bg=E.BORDE, width=1).pack(side=tk.LEFT, fill=tk.Y)
        arriba = tk.Frame(panel, bg=E.FONDO)
        arriba.pack(fill=tk.X, padx=SEP, pady=(SEP, 4))
        self.btn_calcular = boton(arriba, "Calcular", self.calcular)
        self.btn_calcular.pack(fill=tk.X)
        self.btn_exportar = boton(arriba, "Exportar gráficos", self.exportar, primario=False)
        self.btn_exportar.pack(fill=tk.X, pady=(8, 0))
        habilitar(self.btn_exportar, False, primario=False)
        ley = tk.Frame(arriba, bg=E.FONDO)
        ley.pack(fill=tk.X, pady=(10, 0))
        tk.Label(ley, text="(R) dato real", bg=E.FONDO, fg=E.MARCA_REAL, font=fuente(self, 9)).pack(side=tk.LEFT)
        tk.Label(ley, text="  ·  ", bg=E.FONDO, fg=E.TEXTO_2, font=fuente(self, 9)).pack(side=tk.LEFT)
        tk.Label(ley, text="(S) supuesto", bg=E.FONDO, fg=E.SUPUESTO, font=fuente(self, 9, "bold")).pack(side=tk.LEFT)

        desp = PanelDesplazable(panel, ancho=int(305 * self.escala))
        desp.pack(fill=tk.BOTH, expand=True, padx=(SEP, 4), pady=(0, SEP))
        p = Parametros()
        for titulo, abierto, campos in GRUPOS:
            g = GrupoPlegable(desp.interior, titulo, abierto)
            g.pack(fill=tk.X, padx=(0, 8))
            cuerpo = g.cuerpo
            cuerpo.columnconfigure(0, weight=1)
            for fila, (attr, etiqueta, origen, escala, tipo) in enumerate(campos):
                tk.Label(cuerpo, text=etiqueta, bg=E.TARJETA, fg=E.TEXTO, anchor="w", justify="left",
                         wraplength=int(128 * self.escala), font=fuente(self, 9)).grid(row=fila, column=0, sticky="w", padx=(10, 4), pady=3)
                valor = 1 if attr == "replica_mostrar" else getattr(p, attr)
                var = tk.StringVar()
                if isinstance(escala, list):
                    var.set(valor)
                    w = tk.ttk.Combobox(cuerpo, textvariable=var, values=escala, state="readonly", width=10)
                else:
                    v = valor * escala
                    var.set(str(int(v)) if tipo is int or float(v).is_integer() else fmt(v, 2))
                    w = tk.ttk.Entry(cuerpo, textvariable=var, width=11, justify="right")
                w.grid(row=fila, column=1, padx=2, pady=3, sticky="e")
                marca = tk.Label(cuerpo, text=f"({origen})" if origen else "", bg=E.TARJETA, width=3,
                                 fg=E.SUPUESTO if origen == "S" else E.MARCA_REAL,
                                 font=fuente(self, 8, "bold" if origen == "S" else "normal"))
                marca.grid(row=fila, column=2, padx=(0, 8))
                self.variables[attr] = (var, escala, tipo)

    def _leer_parametros(self):
        p = Parametros()
        replica = 1
        for attr, (var, escala, tipo) in self.variables.items():
            texto = var.get()
            try:
                if tipo is str:
                    valor = texto
                else:
                    valor = leer_numero(texto)
                    if not isinstance(escala, list):
                        valor = valor / escala
                    valor = int(round(valor)) if tipo is int else valor
            except ValueError:
                raise ValueError(f"Valor inválido en «{attr}»: {texto!r}")
            if attr == "replica_mostrar":
                replica = valor
            else:
                setattr(p, attr, valor)
        desde, hasta, probs = [], [], []
        for va, vb, vp in self.vars_danio:
            desde.append(leer_numero(va.get()) / 100)
            hasta.append(leer_numero(vb.get()) / 100)
            probs.append(leer_numero(vp.get()) / 100)
        p.danio_desde, p.danio_hasta, p.danio_probabilidades = desde, hasta, probs
        p.validar()
        return p, replica

    # ========================================================== utilidades
    def _figura(self, padre, clave, pestania):
        funcion = next(g[3] for g in G.GRAFICOS if g[0] == clave)
        f = FiguraTarjeta(padre, funcion)
        self.figuras[clave] = f
        self.figuras_pestania.setdefault(pestania, []).append(f)
        return f

    def _al_cambiar_pestania(self, i):
        for f in self.figuras_pestania.get(i, []):
            f.ajustar()

    @staticmethod
    def _pagina(pagina):
        cont = tk.Frame(pagina, bg=E.FONDO)
        cont.pack(fill=tk.BOTH, expand=True, padx=SEP, pady=SEP)
        return cont

    @staticmethod
    def _clave_valor(padre, filas, fila0=0):
        """Filas (clave, valor) alineadas: clave gris a la izquierda, valor a la derecha."""
        labels = []
        for k, texto in enumerate(filas):
            tk.Label(padre, text=texto, bg=E.TARJETA, fg=E.TEXTO_2, anchor="w",
                     font=fuente(padre, 9)).grid(row=fila0 + k, column=0, sticky="w")
            v = tk.Label(padre, text="–", bg=E.TARJETA, fg=E.TEXTO, anchor="e", font=fuente(padre, 9, "bold"))
            v.grid(row=fila0 + k, column=1, sticky="e", padx=(10, 0))
            labels.append(v)
        padre.columnconfigure(1, weight=1)
        return labels

    # ======================================================= pestaña 1
    def _pestania_clima(self, pagina):
        c = self._pagina(pagina)
        self.kpi1 = FilaKPI(c, [("g", "Años con granizo (G)", None), ("dias", "Granizadas por año", None),
                                ("perdida", "Pérdida media anual", None), ("eq", "Pagos / aportes del Fondo", None)])
        self.kpi1.pack(fill=tk.X)
        fila = tk.Frame(c, bg=E.FONDO)
        fila.pack(fill=tk.X, pady=(SEP, 0))

        self._verificacion(fila)
        t = Tarjeta(fila, "Cadena de Markov (R)")
        t.pack(side=tk.LEFT, fill=tk.Y)
        g = tk.Frame(t.cuerpo, bg=E.TARJETA)
        g.pack(anchor="w")
        for j, txt in enumerate(("", "→ S", "→ G")):
            tk.Label(g, text=txt, bg=E.TARJETA, fg=E.TEXTO_2, font=fuente(self, 9, "bold"), width=4).grid(row=0, column=j)
        self.lbl_markov = {}
        for i, est in enumerate(("S", "G")):
            tk.Label(g, text=est, bg=E.TARJETA, fg=E.TEXTO_2, font=fuente(self, 9, "bold")).grid(row=i + 1, column=0)
            for j in range(2):
                l = tk.Label(g, text="–", bg=E.TARJETA, fg=E.TEXTO, font=fuente(self, 10))
                l.grid(row=i + 1, column=j + 1, pady=2)
                self.lbl_markov[(i, j)] = l
        sub = tk.Frame(t.cuerpo, bg=E.TARJETA)
        sub.pack(fill=tk.X, pady=(10, 0))
        self.lbl_estacionaria = self._clave_valor(sub, ["G teórico", "G simulado", "S teórico", "S simulado"])

        t = Tarjeta(fila, "Días con granizo por año (R)")
        t.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(SEP, 0))
        self.tabla_dias = Tabla(t.cuerpo, [("dias", "Días", 36, "center"), ("anios", "Años", 40, "e"),
                                           ("real", "Real", 58, "e"), ("sim", "Simul.", 62, "e")], alto=8)
        self.tabla_dias.pack(fill=tk.BOTH, expand=True)

        t = Tarjeta(fila, "Daño por granizada (S)")
        t.pack(side=tk.RIGHT, fill=tk.Y, padx=(SEP, 0), before=self._tarjeta_ver)
        for col, texto in enumerate(("Desde %", "Hasta %", "Prob. %")):
            tk.Label(t.cuerpo, text=texto, bg=E.TARJETA, fg=E.TEXTO_2, font=fuente(self, 9, "bold")).grid(
                row=0, column=col, padx=3, pady=(0, 2))
        p = Parametros()
        for i, (a, b, pr) in enumerate(zip(p.danio_desde, p.danio_hasta, p.danio_probabilidades), start=1):
            vs = (tk.StringVar(value=fmt(a * 100, 0)), tk.StringVar(value=fmt(b * 100, 0)),
                  tk.StringVar(value=fmt(pr * 100, 1)))
            for col, v in enumerate(vs):
                tk.ttk.Entry(t.cuerpo, textvariable=v, width=5, justify="right").grid(row=i, column=col, padx=2, pady=1)
            vs[2].trace_add("write", lambda *x: self._actualizar_suma_danio())
            self.vars_danio.append(vs)
        self.lbl_suma_danio = tk.Label(t.cuerpo, bg=E.TARJETA, font=fuente(self, 9))
        self.lbl_suma_danio.grid(row=len(self.vars_danio) + 1, column=0, columnspan=3, pady=(4, 0))
        self._actualizar_suma_danio()

        graf = tk.Frame(c, bg=E.FONDO)
        graf.pack(fill=tk.BOTH, expand=True, pady=(SEP, 0))
        for k, clave in enumerate(("dias", "danio_evento", "danio_anual")):
            self._figura(graf, clave, 0).grid(row=0, column=k, sticky="nsew", padx=(0 if k == 0 else SEP, 0))
            graf.columnconfigure(k, weight=1, uniform="g1")
        graf.rowconfigure(0, weight=1)

    def _verificacion(self, fila):
        t = Tarjeta(fila, "Verificación")
        t.pack(side=tk.RIGHT, fill=tk.Y, padx=(SEP, 0))
        self._tarjeta_ver = t
        self.ver = {}
        fila0 = 0
        for nombre, titulo, filas in (
                ("chi", "Prueba χ² del generador", ["χ² (n=10.000, k=10)", "Crítico de tabla", "Decisión"]),
                ("danio", "Daño simulado", ["Por granizada", "Anual con malla", "Años ≥ umbral", "Años = umbral"]),
                ("fondo", "Equilibrio del Fondo", ["P(cobrar) por año", "Pago medio por año", "Aporte por año"])):
            tk.Label(t.cuerpo, text=titulo, bg=E.TARJETA, fg=E.TEXTO, anchor="w",
                     font=fuente(self, 9, "bold")).grid(row=fila0, column=0, columnspan=2, sticky="w",
                                                        pady=(0 if fila0 == 0 else 6, 0))
            self.ver[nombre] = self._clave_valor(t.cuerpo, filas, fila0 + 1)
            fila0 += len(filas) + 1

    def _actualizar_suma_danio(self):
        try:
            total = sum(leer_numero(vs[2].get()) for vs in self.vars_danio)
            ok = abs(total - 100) < 1e-6
            self.lbl_suma_danio.configure(text=f"Suma: {fmt(total, 1)} %" + ("" if ok else "  (debe ser 100)"),
                                          fg=E.TEXTO_2 if ok else "#B91C1C")
        except ValueError:
            self.lbl_suma_danio.configure(text="Suma: valor inválido", fg="#B91C1C")

    def _mostrar_clima(self, R):
        p, cl, d = R["p"], R["clima"], R["dias_real"]
        pi_s, pi_g = R["markov"]["estacionaria"]
        self.kpi1.poner("g", fmt_pct(cl["proporcion_G"]), f"estacionaria teórica {fmt_pct(pi_g)}")
        self.kpi1.poner("dias", fmt(cl["media_dias"]), f"real {fmt(d['media'])} · var. {fmt(cl['varianza_dias'])} "
                                                        f"/ {fmt(d['varianza'])}")
        self.kpi1.poner("perdida", fmt_pct(cl["danio_medio_anual"]),
                        f"DACC {fmt_pct(R['dacc']['con_lucha'])} – {fmt_pct(R['dacc']['sin_lucha'])}")
        eq = R["equilibrio"]
        self.kpi1.poner("eq", fmt(eq["pagos_sobre_aportes"]), f"P(cobrar) {fmt_pct(eq['prob_cobrar'])} por año")
        m = R["markov"]["matriz"]
        for i in range(2):
            for j in range(2):
                self.lbl_markov[(i, j)].configure(text=fmt(m[i][j]))
        for lbl, v in zip(self.lbl_estacionaria, (pi_g, cl["proporcion_G"], pi_s, 1 - cl["proporcion_G"])):
            lbl.configure(text=fmt(v, 3))
        sim = cl["frecuencia_dias"]
        real = dict(zip(d["valores"], d["probs"]))
        anios = dict(zip(d["valores"], d["absolutas"]))
        filas, acum = [], 0
        for k in sorted(set(d["valores"]) | set(sim)):
            acum += real.get(k, 0)
            filas.append(((k, anios.get(k, 0), fmt_pct(real.get(k, 0)), fmt_pct(sim.get(k, 0))), ()))
        self.tabla_dias.llenar(filas)
        chi = R["chi"]
        origen = "tabla" if chi["origen_critico"] == "tabla" else "aprox. Wilson–Hilferty"
        for lbl, txt in zip(self.ver["chi"], (fmt(chi["estadistico"]), fmt(chi['critico']) + ("" if origen == "tabla" else " (aprox.)"),
                                               "no rechaza H0" if chi["acepta_h0"] else "rechaza H0")):
            lbl.configure(text=txt)
        for lbl, txt in zip(self.ver["danio"], (fmt_pct(cl["danio_medio_evento"]), fmt_pct(cl["danio_medio_anual_malla"]),
                                                 fmt_pct(cl["prob_danio_paga"]), fmt_pct(cl["prob_danio_igual_umbral"], 2))):
            lbl.configure(text=txt)
        for lbl, txt in zip(self.ver["fondo"], (fmt_pct(eq["prob_cobrar"]), fmt_m(eq["pago_medio_anual"]),
                                                 fmt_m(eq["aporte_anual"]))):
            lbl.configure(text=txt)

    # ======================================================= pestaña 2
    def _pestania_corrida(self, pagina):
        c = self._pagina(pagina)
        self.kpi2 = FilaKPI(c, [(a, A[a]["corto"], A[a]["color"]) for a in ALTERNATIVAS]
                            + [("fuertes", "Años de granizo fuerte", None)])
        self.kpi2.pack(fill=tk.X)
        cuerpo = tk.Frame(c, bg=E.FONDO)
        cuerpo.pack(fill=tk.BOTH, expand=True, pady=(SEP, 0))
        t = Tarjeta(cuerpo, "Resultados año por año (millones de $)")
        t.grid(row=0, column=0, sticky="nsew")
        cols = [("anio", "Año", 50, "center"), ("estado", "Estado", 60, "center"), ("dias", "Granizadas", 80, "e"),
                ("danio", "Daño %", 70, "e"), ("danio_m", "Daño malla %", 95, "e"), ("rend", "Rend. kg/ha", 90, "e"),
                ("sin", "Sin protección", 110, "e"), ("comp", "Compensación", 110, "e"),
                ("fondo", "Fondo", 90, "e"), ("malla", "Malla", 90, "e")]
        self.tabla_corrida = Tabla(t.cuerpo, cols, alto=12, desplazable=True)
        self.tabla_corrida.pack(fill=tk.BOTH, expand=True)
        self._figura(cuerpo, "acumulada", 1).grid(row=1, column=0, sticky="nsew", pady=(SEP, 0))
        cuerpo.columnconfigure(0, weight=1)
        cuerpo.rowconfigure(0, weight=1)
        cuerpo.rowconfigure(1, weight=1)

    def _mostrar_corrida(self, R):
        res, p = R["res"], R["p"]
        r = R["replica"] - 1
        anu = {a: res.anuales[a][r] for a in ALTERNATIVAS}
        comp = res.compensacion[r]
        fuerte = comp > 0 if p.hectareas <= p.fca_max_hectareas else res.danio[r] >= p.fca_umbral
        filas = []
        for t in range(p.anios):
            filas.append(((t + 1, "G" if res.estados[r, t] else "S", int(res.dias[r, t]), fmt(res.danio[r, t] * 100, 1),
                           fmt(res.danio_malla[r, t] * 100, 1), fmt(res.rendimiento[r, t], 0),
                           fmt(anu["sin_proteccion"][t] / 1e6), fmt(comp[t] / 1e6), fmt(anu["fondo"][t] / 1e6),
                           fmt(anu["malla"][t] / 1e6)), ("fuerte",) if fuerte[t] else ()))
        filas.append((("Total", "", int(res.dias[r].sum()), "", "", "", fmt(anu["sin_proteccion"].sum() / 1e6),
                       fmt(comp.sum() / 1e6), fmt(anu["fondo"].sum() / 1e6), fmt(anu["malla"].sum() / 1e6)), ("total",)))
        filas.append(((f"VAN {fmt(p.tasa_descuento * 100, 0)} %", "", "", "", "", "",
                       fmt(res.van["sin_proteccion"][r] / 1e6), "", fmt(res.van["fondo"][r] / 1e6),
                       fmt(res.van["malla"][r] / 1e6)), ("total",)))
        self.tabla_corrida.llenar(filas)
        for a in ALTERNATIVAS:
            self.kpi2.poner(a, fmt_m(res.van[a][r]), f"VAN de la réplica · suma {fmt(anu[a].sum() / 1e6)} M")
        self.kpi2.poner("fuertes", str(int(fuerte.sum())), f"de {p.anios} años · réplica {R['replica']} (en gris)")

    # ======================================================= pestaña 3
    def _pestania_montecarlo(self, pagina):
        c = self._pagina(pagina)
        self.kpi3 = FilaKPI(c, [(a, A[a]["corto"], A[a]["color"]) for a in ALTERNATIVAS]
                            + [("mejor", "Mejor alternativa", None)])
        self.kpi3.pack(fill=tk.X)
        cuerpo = tk.Frame(c, bg=E.FONDO)
        cuerpo.pack(fill=tk.BOTH, expand=True, pady=(SEP, 0))
        self._figura(cuerpo, "histogramas", 2).grid(row=0, column=0, sticky="nsew")
        t = Tarjeta(cuerpo, "Indicadores")
        t.grid(row=1, column=0, sticky="nsew", pady=(SEP, 0))
        self.tabla_mc = Tabla(t.cuerpo, [("ind", "Indicador", 330, "w")] +
                              [(a, A[a]["nombre"], 170, "e") for a in ALTERNATIVAS], alto=12)
        self.tabla_mc.pack(fill=tk.BOTH, expand=True)
        cuerpo.columnconfigure(0, weight=1)
        cuerpo.rowconfigure(0, weight=3)
        cuerpo.rowconfigure(1, weight=2)

    def _mostrar_montecarlo(self, R):
        ind, p, ic = R["ind"], R["p"], R["ic_van"]
        for a in ALTERNATIVAS:
            self.kpi3.poner(a, fmt_m(ind[a]["van_media"]), f"VAN medio ± {fmt(ic[a]['semiancho'] / 1e6, 2)} M (IC 95 %)")
        self.kpi3.poner("mejor", mejor_corto(R["mejor"]), f"mayor VAN medio con P5 > {fmt_m(p.criterio_p5_minimo, 0)}")
        tasa = fmt(p.tasa_descuento * 100, 1)
        pct = lambda v: f"{fmt(v, 1)} %"
        definicion = [
            (f"VAN medio ({tasa} %) – indicador principal", "van_media", fmt_m, max),
            ("IC 95 % del VAN medio (±)", None, None, None),
            ("VAN – desvío estándar", "van_desvio", fmt_m, min),
            ("VAN – percentil 5 (P5)", "van_p5", fmt_m, max),
            ("VAN – percentil 95 (P95)", "van_p95", fmt_m, None),
            ("% de réplicas con VAN negativo", "pct_van_negativo", lambda v: f"{fmt(v, 2)} %", min),
            (f"Suma sin descontar {p.anios} años – media", "media", fmt_m, max),
            ("Suma sin descontar – P5", "p5", fmt_m, max),
            ("% de años con pérdida", "pct_anios_perdida", pct, min),
            ("Percentil 1 de los resultados anuales", "p1_anual", fmt_m, max),
            ("Peor año (mínimo de todas las réplicas)", "peor_anio", fmt_m, max),
        ]
        filas = []
        for titulo, clave, f_fmt, mejor in definicion:
            if clave is None:
                celdas = [f"± {fmt(ic[a]['semiancho'] / 1e6, 3)} M" for a in ALTERNATIVAS]
            else:
                valores = [ind[a][clave] for a in ALTERNATIVAS]
                celdas = [f_fmt(v) for v in valores]
                if mejor is not None:
                    i = valores.index(mejor(valores))
                    celdas[i] = "★ " + celdas[i]
            filas.append(((titulo, *celdas), ()))
        self.tabla_mc.llenar(filas)

    # ======================================================= pestaña 4
    def _pestania_decision(self, pagina):
        desp = PanelDesplazable(pagina, ancho=400)
        desp.pack(fill=tk.BOTH, expand=True)
        c = tk.Frame(desp.interior, bg=E.FONDO)
        c.pack(fill=tk.BOTH, expand=True, padx=SEP, pady=SEP)
        self.kpi4 = FilaKPI(c, [("mejor", "Mejor alternativa", None), ("sev", "Corte de severidad", None),
                                ("pf", "Malla = Fondo", None), ("ps", "Malla = Sin protección", None)])
        self.kpi4.pack(fill=tk.X)
        graf = tk.Frame(c, bg=E.FONDO)
        graf.pack(fill=tk.BOTH, expand=True, pady=(SEP, 0))
        for k, clave in enumerate(("riesgo", "precio", "severidad", "mapa_precio", "mapa_ha", "persistencia")):
            fila, col = divmod(k, 3)
            self._figura(graf, clave, 3).grid(row=fila, column=col, sticky="nsew",
                                              padx=(0 if col == 0 else SEP, 0), pady=(0 if fila == 0 else SEP, 0))
        for k in range(3):
            graf.columnconfigure(k, weight=1, uniform="g4")
        for k in range(2):
            # altura fija: al abrir la tabla de persistencia la pestaña se desplaza, los gráficos no se aplastan
            graf.rowconfigure(k, minsize=int(300 * self.escala))
        grupo = GrupoPlegable(c, "Tabla de persistencia: Markov real contra años independientes", abierto=False)
        self.grupo_pers = grupo
        grupo.pack(fill=tk.X, pady=(6, 0))
        t = Tarjeta(grupo.cuerpo, None, padding=10)
        t.pack(fill=tk.X)
        cols = [("ind", "Indicador", 200, "w")]
        for a in ALTERNATIVAS:
            cols += [(f"{a}_m", f"{A[a]['corto']} – Markov", 130, "e"), (f"{a}_i", f"{A[a]['corto']} – indep.", 130, "e")]
        self.tabla_pers = Tabla(t.cuerpo, cols, alto=4)
        self.tabla_pers.pack(fill=tk.X)
        self.lbl_pers = tk.Label(t.cuerpo, bg=E.TARJETA, fg=E.TEXTO_2, anchor="w", justify="left", font=fuente(self, 9))
        self.lbl_pers.pack(fill=tk.X, pady=(6, 0))
        t.cuerpo.bind("<Configure>", lambda e: self.lbl_pers.configure(wraplength=max(200, e.width - 10)), add="+")

    def _mostrar_decision(self, R):
        p, cr, cortes = R["p"], R["cruce_sev"], R["cortes"]
        self.kpi4.poner("mejor", mejor_corto(R["mejor"]), f"mayor VAN medio con P5 > {fmt_m(p.criterio_p5_minimo, 0)}")
        if cr["estimado"] is not None:
            self.kpi4.poner("sev", f"×{fmt(cr['estimado'], 3)}", texto_ic_cruce(cr))
        else:
            self.kpi4.poner("sev", "–", "no cruza entre ×0,25 y ×0,35")
        for clave, k in (("pf", "fondo"), ("ps", "sin_proteccion")):
            x = cortes[k]
            if x["pesos_kg"] is not None:
                self.kpi4.poner(clave, f"$ {fmt(x['pesos_kg'], 0)}/kg",
                                f"USD {fmt(x['usd_kg'], 3)}/kg · tasa {fmt(p.tasa_descuento * 100, 0)} %")
        pers = R["persistencia"]
        filas = []
        for titulo, clave, ff in (("VAN medio", "van_media", fmt_m), ("VAN P5", "van_p5", fmt_m),
                                  ("VAN desvío", "van_desvio", fmt_m),
                                  ("% de años con pérdida", "pct_anios_perdida", lambda v: f"{fmt(v, 1)} %")):
            celdas = []
            for a in ALTERNATIVAS:
                for nombre in ("markov", "independiente"):
                    celdas.append(ff(pers[nombre]["indicadores"][a][clave]))
            filas.append(((titulo, *celdas), ()))
        self.tabla_pers.llenar(filas)
        m, i = pers["markov"], pers["independiente"]
        self.lbl_pers.configure(text=(
            f"Clima (igual para las tres alternativas): racha máxima media de años con granizo {fmt(m['racha_G_media'], 1)} "
            f"con Markov contra {fmt(i['racha_G_media'], 1)} con años independientes · P(2 o más años fuertes seguidos) "
            f"{fmt_pct(m['prob_2_fuertes_seguidos'])} contra {fmt_pct(i['prob_2_fuertes_seguidos'])}. "
            f"Misma proporción de años G ({fmt(pers['pi_G'], 3)})."))

    # ======================================================= pestaña 5
    def _pestania_precision(self, pagina):
        c = self._pagina(pagina)
        self.kpi5 = FilaKPI(c, [("error", "Error del VAN medio", None), ("nac", "Ganancia de los NAC", None),
                                ("sev", "Corte de severidad", None), ("conv", "Convergencia 1/√n", None)])
        self.kpi5.pack(fill=tk.X)
        t = Tarjeta(c, None, padding=10)
        t.pack(fill=tk.X, pady=(SEP, 0))
        self.lbl_prec = tk.Label(t.cuerpo, bg=E.TARJETA, fg=E.TEXTO_2, justify="left", anchor="w",
                                 font=fuente(self, 9))
        self.lbl_prec.pack(fill=tk.X)
        t.cuerpo.bind("<Configure>", lambda e: self.lbl_prec.configure(wraplength=max(200, e.width - 10)))
        graf = tk.Frame(c, bg=E.FONDO)
        graf.pack(fill=tk.BOTH, expand=True, pady=(SEP, 0))
        self._figura(graf, "convergencia", 4).grid(row=0, column=0, sticky="nsew")
        self._figura(graf, "corte_sev", 4).grid(row=0, column=1, sticky="nsew", padx=(SEP, 0))
        graf.columnconfigure(0, weight=2)
        graf.columnconfigure(1, weight=1)
        graf.rowconfigure(0, weight=1)
        abajo = tk.Frame(c, bg=E.FONDO)
        abajo.pack(fill=tk.X, pady=(SEP, 0))
        t = Tarjeta(abajo, "Diferencias de VAN medio: IC 95 %", padding=10)
        t.grid(row=0, column=0, sticky="nsew")
        self.tabla_dif = Tabla(t.cuerpo, [("par", "Diferencia", 110, "w"), ("est", "Estimación", 85, "e"),
                                          ("nac", "IC con NAC", 80, "e"), ("ind", "IC indep.", 75, "e"),
                                          ("red", "Ganancia", 75, "e"), ("rho", "Correlación", 80, "e")], alto=3)
        self.tabla_dif.pack(fill=tk.X)
        t = Tarjeta(abajo, "Precio de corte de la malla (malla = …)", padding=10)
        t.grid(row=0, column=1, sticky="nsew", padx=(SEP, 0))
        self._tarjeta_tasas = t
        self.tabla_tasas = Tabla(t.cuerpo, [("tasa", "Tasa", 50, "e"), ("fp", "Fondo $/kg", 80, "e"),
                                            ("fu", "USD/kg", 60, "e"), ("sp", "Sin $/kg", 70, "e"),
                                            ("su", "USD/kg", 60, "e")], alto=3)
        self.tabla_tasas.pack(fill=tk.X)
        abajo.columnconfigure(0, weight=5)
        abajo.columnconfigure(1, weight=3)

    def _mostrar_precision(self, R):
        p, ic, dif, cr = R["p"], R["ic_van"], R["diferencias"], R["cruce_sev"]
        error = max(ic[a]["semiancho"] / abs(ic[a]["media"]) for a in ALTERNATIVAS if ic[a]["media"])
        self.kpi5.poner("error", f"≤ {fmt(error * 100, 1)} %", f"IC 95 % con {fmt(p.replicas, 0)} réplicas")
        fs = dif[("fondo", "sin_proteccion")]
        self.kpi5.poner("nac", f"{fmt(fs['reduccion'], 1)} veces", f"IC Fondo − Sin más angosto")
        if cr["estimado"] is not None:
            self.kpi5.poner("sev", f"×{fmt(cr['estimado'], 3)}", texto_ic_cruce(cr))
        conv = R["convergencia"]
        n = conv["tamanios"]
        if len(n) >= 2:
            s = conv["fondo"]["semiancho"]
            self.kpi5.poner("conv", f"{fmt(s[-2] / s[-1], 2)}",
                            f"{fmt(n[-2], 0)}→{fmt(n[-1], 0)} · √{fmt(n[-1] / n[-2], 0)} = "
                            f"{fmt((n[-1] / n[-2]) ** 0.5, 2)}")
        filas = []
        for (a, b), fila in dif.items():
            filas.append(((f"{CORTO[a]} − {CORTO[b]}", fmt_m(fila["nac"]["media"]),
                           f"± {fmt(fila['nac']['semiancho'] / 1e6, 3)}", f"± {fmt(fila['independiente']['semiancho'] / 1e6, 3)}",
                           f"{fmt(fila['reduccion'], 1)} veces", fmt(fila["correlacion"], 3)), ()))
        self.tabla_dif.llenar(filas)
        filas = []
        num = lambda x, d: fmt(x, d) if x is not None else "–"
        for t, c in R["cortes_tasa"].items():
            filas.append(((f"{fmt(t * 100, 0)} %", num(c["fondo"]["pesos_kg"], 0), num(c["fondo"]["usd_kg"], 3),
                           num(c["sin_proteccion"]["pesos_kg"], 0), num(c["sin_proteccion"]["usd_kg"], 3)), ()))
        self.tabla_tasas.llenar(filas)
        tc, base = R["cortes_tc_doble"], R["cortes"]
        self.lbl_prec.configure(text=(
            f"IC 95 % = media ± 1,96·s/√n. NAC = números aleatorios comunes: las tres alternativas se evalúan sobre "
            f"los mismos escenarios; «independientes» toma la segunda alternativa de una corrida con semilla "
            f"{p.semilla + 1}. Convergencia: prefijos de una corrida de {fmt(p.conv_replicas_max, 0)} réplicas "
            f"(línea vertical = réplicas usadas). Con el tipo de cambio ×2 el corte en USD/kg contra no protegerse "
            f"no cambia ({num(base['sin_proteccion']['usd_kg'], 3)} → {num(tc['sin_proteccion']['usd_kg'], 3)}), "
            f"pero contra el Fondo sí ({num(base['fondo']['usd_kg'], 3)} → {num(tc['fondo']['usd_kg'], 3)}), "
            f"porque el aporte y la compensación del Fondo están fijos en pesos."))

    # ============================================================ acciones
    def _progreso(self, texto, i, total):
        self.estado.set(f"Calculando… paso {i + 1} de {total}: {texto}")
        self.update_idletasks()

    def calcular(self):
        try:
            p, replica = self._leer_parametros()
        except ValueError as e:
            messagebox.showerror("Datos inválidos", str(e))
            return
        habilitar(self.btn_calcular, False)
        habilitar(self.btn_exportar, False, primario=False)
        self.config(cursor="watch")
        self.update_idletasks()
        try:
            R = calcular_todo(p, replica, self._progreso)
            self.estado.set("Dibujando…")
            self.update_idletasks()
            self.R = R
            self._mostrar_clima(R)
            self._mostrar_corrida(R)
            self._mostrar_montecarlo(R)
            self._mostrar_decision(R)
            self._mostrar_precision(R)
            for f in self.figuras.values():
                f.dibujar(R)
            self.estado.set(f"Listo: {fmt(p.replicas, 0)} réplicas × {p.anios} años, semilla {p.semilla}, "
                            f"{fmt(R['res'].numeros_usados, 0)} números aleatorios en la corrida principal.")
        except Exception as e:  # noqa: BLE001 – se muestra al usuario
            messagebox.showerror("Error al calcular", str(e))
            self.estado.set("Error.")
        finally:
            self.config(cursor="")
            habilitar(self.btn_calcular, True)
            habilitar(self.btn_exportar, self.R is not None, primario=False)

    def exportar(self):
        if self.R is None:
            return
        self.estado.set("Exportando gráficos…")
        self.config(cursor="watch")
        self.update_idletasks()
        try:
            rutas = G.exportar(self.R, CARPETA_FIGURAS)
            self.estado.set(f"Se exportaron {len(rutas)} gráficos a {CARPETA_FIGURAS}")
            messagebox.showinfo("Gráficos exportados",
                                f"Se guardaron {len(rutas)} gráficos PNG (200 dpi, 16 cm de ancho) en:\n{CARPETA_FIGURAS}")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Error al exportar", str(e))
        finally:
            self.config(cursor="")


if __name__ == "__main__":
    E.activar_dpi()
    App().mainloop()
