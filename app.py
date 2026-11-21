"""
Malla antigranizo, seguro o nada: simulación para decidir.
Interfaz gráfica (tkinter + matplotlib). La lógica está en el paquete simulador/.

Ejecutar:  python app.py
"""

import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from simulador import datos_reales as R
from simulador.parametros import Parametros
from simulador.clima import CadenaMarkov
from simulador.danio import referencia_dacc
from simulador.finca import ALTERNATIVAS, NOMBRES
from simulador.generador import GeneradorLCG, prueba_chi_cuadrado
from simulador import montecarlo as mc

COLORES = {"sin_proteccion": "#c0504d", "fondo": "#4f81bd", "malla": "#5a9e3a"}
COLOR_REAL = "#7f7f7f"
COLOR_SUPUESTO = "#c55a11"


# ---------------------------------------------------------------------------
# Formato de números en castellano
# ---------------------------------------------------------------------------
def fmt(x, dec=2):
    s = f"{x:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_m(x, dec=2):
    """Pesos en millones."""
    return f"$ {fmt(x / 1e6, dec)} M"


def leer_numero(texto):
    s = texto.strip().replace("$", "").replace(" ", "")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    return float(s)


# ---------------------------------------------------------------------------
# Campos del panel izquierdo: (atributo, etiqueta, origen, escala, tipo)
#   origen: "R" dato real, "S" supuesto, "" parámetro de simulación
#   escala: el valor se muestra multiplicado por escala (100 → en %)
# ---------------------------------------------------------------------------
GRUPOS = [
    ("Simulación", [
        ("replicas", "Réplicas", "", 1, int),
        ("anios", "Años por réplica", "", 1, int),
        ("semilla", "Semilla", "", 1, int),
        ("replica_mostrar", "Réplica a mostrar (pestaña 2)", "", 1, int),
    ]),
    ("Generador congruencial", [
        ("lcg_a", "a (multiplicador)", "", 1, int),
        ("lcg_c", "c (incremento)", "", 1, int),
        ("lcg_m", "m (módulo)", "", 1, int),
    ]),
    ("Finca tipo (INV)", [
        ("hectareas", "Hectáreas", "R", 1, float),
        ("rendimiento_min", "Rendimiento mín. (kg/ha)", "R", 1, float),
        ("rendimiento_max", "Rendimiento máx. (kg/ha)", "R", 1, float),
    ]),
    ("Clima – Markov (San Rafael Aero)", [
        ("p_s_a_g", "P(S → G)", "R", 1, float),
        ("p_g_a_s", "P(G → S)", "R", 1, float),
        ("estado_inicial", "Estado del año 1", "S", ["estacionaria", "G", "S"], str),
    ]),
    ("Economía", [
        ("precio_uva", "Precio uva ($/kg)", "S", 1, float),
        ("costo_produccion_ha", "Costo producción ($/ha/año)", "S", 1, float),
        ("tipo_cambio", "Tipo de cambio ($/USD)", "S", 1, float),
    ]),
    ("Fondo Compensador (Específica, Sur)", [
        ("fca_aporte_ha", "Aporte ($/ha/año)", "R", 1, float),
        ("fca_compensacion_ha", "Compensación ($/ha)", "R", 1, float),
        ("fca_umbral", "Umbral de daño (%)", "R", 100, float),
        ("fca_modo", "Compensación", "S", ["proporcional", "fijo"], str),
    ]),
    ("Malla antigranizo", [
        ("malla_costo_usd_ha", "Costo (USD/ha)", "R", 1, float),
        ("malla_vida_util", "Vida útil (años)", "R", 1, int),
        ("malla_eficacia", "Reducción del daño (%)", "S", 100, float),
        ("malla_modo_pago", "Forma de pago", "S", ["amortizado", "contado", "financiado"], str),
        ("malla_tasa_anual", "Tasa anual crédito (%)", "S", 100, float),
        ("malla_cuotas", "Cuotas (años)", "S", 1, int),
    ]),
    ("Referencia DACC", [
        ("superficie_cultivada_sur", "Sup. cultivada Oasis Sur (ha)", "S", 1, float),
    ]),
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Malla antigranizo, seguro o nada – Simulación (UTN FRSR 2026)")
        self.geometry("1400x860")
        self.minsize(1100, 700)
        self.variables = {}
        self.vars_danio = []
        self.resultado = None

        estilo = ttk.Style(self)
        if "clam" in estilo.theme_names():
            estilo.theme_use("clam")
        estilo.configure("Treeview", rowheight=20)
        estilo.configure("Calcular.TButton", font=("Segoe UI", 11, "bold"))

        principal = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        principal.pack(fill=tk.BOTH, expand=True)
        principal.add(self._panel_datos(principal), weight=0)

        self.pestanias = ttk.Notebook(principal)
        principal.add(self.pestanias, weight=1)
        self._pestania_clima()
        self._pestania_corrida()
        self._pestania_montecarlo()

        self.estado = tk.StringVar(value="Listo. Presioná «Calcular».")
        ttk.Label(self, textvariable=self.estado, anchor="w", relief="sunken").pack(fill=tk.X)

        self.after(100, self.calcular)

    # ------------------------------------------------------------------ panel
    def _panel_datos(self, padre):
        marco = ttk.Frame(padre, width=380)
        ttk.Button(marco, text="Calcular", style="Calcular.TButton",
                   command=self.calcular).pack(fill=tk.X, padx=6, pady=6)
        leyenda = ttk.Frame(marco)
        leyenda.pack(fill=tk.X, padx=8)
        tk.Label(leyenda, text="(R) dato real", fg=COLOR_REAL).pack(side=tk.LEFT)
        tk.Label(leyenda, text="   (S) SUPUESTO", fg=COLOR_SUPUESTO,
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)

        lienzo = tk.Canvas(marco, highlightthickness=0, width=370)
        barra = ttk.Scrollbar(marco, orient=tk.VERTICAL, command=lienzo.yview)
        interior = ttk.Frame(lienzo)
        interior.bind("<Configure>", lambda e: lienzo.configure(scrollregion=lienzo.bbox("all")))
        lienzo.create_window((0, 0), window=interior, anchor="nw")
        lienzo.configure(yscrollcommand=barra.set)
        lienzo.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        barra.pack(side=tk.RIGHT, fill=tk.Y)
        lienzo.bind_all("<MouseWheel>", lambda e: self._rueda(e, lienzo))

        p = Parametros()
        for titulo, campos in GRUPOS:
            grupo = ttk.LabelFrame(interior, text=titulo)
            grupo.pack(fill=tk.X, padx=2, pady=4)
            for fila, (attr, etiqueta, origen, escala, tipo) in enumerate(campos):
                ttk.Label(grupo, text=etiqueta, width=25).grid(row=fila, column=0, sticky="w", padx=4, pady=1)
                if attr == "replica_mostrar":
                    valor = 1
                else:
                    valor = getattr(p, attr)
                var = tk.StringVar()
                if isinstance(escala, list):
                    var.set(valor)
                    w = ttk.Combobox(grupo, textvariable=var, values=escala,
                                     state="readonly", width=12)
                else:
                    v = valor * escala
                    var.set(str(int(v)) if tipo is int or float(v).is_integer() else fmt(v, 2))
                    w = ttk.Entry(grupo, textvariable=var, width=12, justify="right")
                w.grid(row=fila, column=1, padx=4, pady=1)
                if origen:
                    tk.Label(grupo, text=f"({origen})",
                             fg=COLOR_SUPUESTO if origen == "S" else COLOR_REAL,
                             font=("Segoe UI", 8, "bold" if origen == "S" else "normal")
                             ).grid(row=fila, column=2, padx=(0, 4))
                self.variables[attr] = (var, escala, tipo)
        interior.update_idletasks()
        lienzo.configure(width=interior.winfo_reqwidth())
        return marco

    @staticmethod
    def _rueda(evento, lienzo):
        if str(evento.widget).startswith(str(lienzo)):
            lienzo.yview_scroll(int(-evento.delta / 120), "units")

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
        valores, probs = [], []
        for var_d, var_p in self.vars_danio:
            valores.append(leer_numero(var_d.get()) / 100)
            probs.append(leer_numero(var_p.get()) / 100)
        p.danio_valores, p.danio_probabilidades = valores, probs
        p.validar()
        if not 1 <= replica <= p.replicas:
            raise ValueError(f"La réplica a mostrar debe estar entre 1 y {p.replicas}.")
        return p, replica

    # --------------------------------------------------------------- pestaña 1
    def _pestania_clima(self):
        tab = ttk.Frame(self.pestanias)
        self.pestanias.add(tab, text="  1 · Clima y granizo  ")
        arriba = ttk.Frame(tab)
        arriba.pack(fill=tk.X, padx=6, pady=6)

        # Matriz de Markov
        f_markov = ttk.LabelFrame(arriba, text="Cadena de Markov (R)")
        f_markov.pack(side=tk.LEFT, fill=tk.Y, padx=4)
        self.lbl_markov = ttk.Label(f_markov, font=("Consolas", 10), justify="left")
        self.lbl_markov.pack(padx=6, pady=4, anchor="w")

        # Tabla de días
        f_dias = ttk.LabelFrame(arriba, text="Días con granizo por año (R): real vs simulado")
        f_dias.pack(side=tk.LEFT, fill=tk.Y, padx=4)
        cols = ("dias", "anios", "real", "acum", "sim")
        self.tv_dias = ttk.Treeview(f_dias, columns=cols, show="headings", height=8)
        for c, t, w in zip(cols, ("Días", "Años", "Frec. real", "Acum. real", "Frec. simul."),
                           (45, 50, 80, 85, 105)):
            self.tv_dias.heading(c, text=t)
            self.tv_dias.column(c, width=w, anchor="center")
        self.tv_dias.pack(padx=4, pady=4)

        # Tabla de daño editable
        f_danio = ttk.LabelFrame(arriba, text="Daño por granizada (S)")
        f_danio.pack(side=tk.LEFT, fill=tk.Y, padx=4)
        ttk.Label(f_danio, text="Daño %").grid(row=0, column=0, padx=4)
        ttk.Label(f_danio, text="Prob. %").grid(row=0, column=1, padx=4)
        p = Parametros()
        for i, (d, pr) in enumerate(zip(p.danio_valores, p.danio_probabilidades), start=1):
            vd, vp = tk.StringVar(value=fmt(d * 100, 0)), tk.StringVar(value=fmt(pr * 100, 1))
            ttk.Entry(f_danio, textvariable=vd, width=7, justify="right").grid(row=i, column=0, padx=4, pady=1)
            ttk.Entry(f_danio, textvariable=vp, width=7, justify="right").grid(row=i, column=1, padx=4, pady=1)
            vp.trace_add("write", lambda *a: self._actualizar_suma_danio())
            self.vars_danio.append((vd, vp))
        self.lbl_suma_danio = ttk.Label(f_danio)
        self.lbl_suma_danio.grid(row=len(self.vars_danio) + 1, column=0, columnspan=2, pady=2)
        self._actualizar_suma_danio()

        # Verificación
        f_ver = ttk.LabelFrame(arriba, text="Verificación")
        f_ver.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        self.lbl_verificacion = ttk.Label(f_ver, font=("Consolas", 9), justify="left")
        self.lbl_verificacion.pack(padx=6, pady=4, anchor="nw")

        self.fig_clima = Figure(figsize=(10, 4), constrained_layout=True)
        self.canvas_clima = FigureCanvasTkAgg(self.fig_clima, master=tab)
        self.canvas_clima.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

    def _actualizar_suma_danio(self):
        try:
            total = sum(leer_numero(vp.get()) for _, vp in self.vars_danio)
            ok = abs(total - 100) < 1e-6
            self.lbl_suma_danio.configure(text=f"Suma: {fmt(total, 1)} %" + ("" if ok else "  ≠ 100"),
                                          foreground="black" if ok else "red")
        except ValueError:
            self.lbl_suma_danio.configure(text="Suma: valor inválido", foreground="red")

    def _dibujar_clima(self, res, p):
        valores, absolutas, probs = R.tabla_dias_granizo()
        resumen = mc.resumen_clima(res)
        sim = resumen["frecuencia_dias"]

        cadena = CadenaMarkov(p.p_s_a_g, p.p_g_a_s)
        m = cadena.matriz()
        pi_s, pi_g = cadena.estacionaria()
        self.lbl_markov.configure(text=(
            "        → S     → G\n"
            f"  S   {fmt(m[0][0])}   {fmt(m[0][1])}\n"
            f"  G   {fmt(m[1][0])}   {fmt(m[1][1])}\n\n"
            "Estacionaria (teórica):\n"
            f"  S = {fmt(pi_s, 3)}   G = {fmt(pi_g, 3)}\n"
            "Proporción simulada:\n"
            f"  S = {fmt(1 - resumen['proporcion_G'], 3)}   G = {fmt(resumen['proporcion_G'], 3)}"
        ))

        self.tv_dias.delete(*self.tv_dias.get_children())
        todos = sorted(set(valores) | set(sim))
        acum = 0
        real = dict(zip(valores, probs))
        anios = dict(zip(valores, absolutas))
        for k in todos:
            acum += real.get(k, 0)
            self.tv_dias.insert("", tk.END, values=(
                k, anios.get(k, 0), f"{fmt(real.get(k, 0) * 100, 1)} %",
                f"{fmt(acum * 100, 1)} %", f"{fmt(sim.get(k, 0) * 100, 1)} %"))
        media_r = sum(v * q for v, q in zip(valores, probs))
        dias_reales = [d for _, d in R.cargar_serie_granizo() if d is not None]
        var_r = float(np.var(dias_reales, ddof=1))
        self.tv_dias.insert("", tk.END, values=("Media", "", fmt(media_r), "", fmt(resumen["media_dias"])))
        self.tv_dias.insert("", tk.END, values=("Var.", "", fmt(var_r), "", fmt(resumen["varianza_dias"])))

        # Verificación: chi-cuadrado y calibración DACC
        gen = GeneradorLCG(p.semilla, p.lcg_a, p.lcg_c, p.lcg_m)
        chi = prueba_chi_cuadrado(gen.generar(10_000), intervalos=10)
        dacc = referencia_dacc(p.superficie_cultivada_sur)
        self.lbl_verificacion.configure(text=(
            "Prueba χ² del generador\n"
            f" n=10.000  k=10  α=0,05\n"
            f" χ²={fmt(chi['estadistico'])}  crít.={fmt(chi['critico'])}\n"
            f" → {'NO se rechaza' if chi['acepta_h0'] else 'SE RECHAZA'} H0\n\n"
            "Daño simulado\n"
            f" por granizada: {fmt(resumen['danio_medio_evento'] * 100, 1)} %\n"
            f" medio anual:   {fmt(resumen['danio_medio_anual'] * 100, 1)} %\n"
            f" anual c/malla: {fmt(resumen['danio_medio_anual_malla'] * 100, 1)} %\n"
            f" años > {fmt(p.fca_umbral * 100, 0)} %:    {fmt(resumen['prob_danio_supera_umbral'] * 100, 1)} %\n\n"
            "Ref. DACC Sur anual\n"
            f" {fmt(dacc['con_lucha'] * 100, 1)} % a {fmt(dacc['sin_lucha'] * 100, 1)} %"
        ))

        f = self.fig_clima
        f.clear()
        ax1, ax2, ax3 = f.subplots(1, 3)
        x = np.array(todos)
        ax1.bar(x - 0.2, [real.get(k, 0) for k in todos], 0.4, color=COLOR_REAL, label="Real 1974–2024")
        ax1.bar(x + 0.2, [sim.get(k, 0) for k in todos], 0.4, color="#4f81bd", label="Simulado")
        ax1.set_title("Días con granizo por año")
        ax1.set_xlabel("días")
        ax1.set_ylabel("frecuencia relativa")
        ax1.set_xticks(x)
        ax1.legend()

        dv = np.array(p.danio_valores) * 100
        ax2.bar(np.arange(len(dv)), p.danio_probabilidades, color=COLOR_SUPUESTO)
        ax2.set_xticks(np.arange(len(dv)), [fmt(v, 0) for v in dv])
        ax2.set_title("Daño por granizada (SUPUESTO)")
        ax2.set_xlabel("daño %")
        ax2.set_ylabel("probabilidad")

        danio = res.danio.ravel() * 100
        ax3.hist(danio, bins=np.arange(0, 102, 5), color="#4f81bd",
                 weights=np.full(danio.size, 100 / danio.size))
        ax3.axvspan(dacc["con_lucha"] * 100, dacc["sin_lucha"] * 100, color="#f2c14e", alpha=0.35,
                    label="Rango DACC Sur")
        ax3.axvline(danio.mean(), color="black", ls="--", label=f"Media {fmt(danio.mean(), 1)} %")
        ax3.axvline(p.fca_umbral * 100, color="#4f81bd", ls=":", label="Umbral Fondo")
        ax3.set_yscale("log")
        ax3.set_title("Daño anual simulado")
        ax3.set_xlabel("daño del año %")
        ax3.set_ylabel("% de años (escala log)")
        ax3.legend(fontsize=8)
        self.canvas_clima.draw()

    # --------------------------------------------------------------- pestaña 2
    def _pestania_corrida(self):
        tab = ttk.Frame(self.pestanias)
        self.pestanias.add(tab, text="  2 · Una corrida  ")
        self.lbl_corrida = ttk.Label(tab, font=("Segoe UI", 10, "bold"))
        self.lbl_corrida.pack(anchor="w", padx=8, pady=(6, 0))
        cols = ("anio", "estado", "dias", "danio", "danio_m", "rend", "sin", "comp", "fondo", "malla")
        titulos = ("Año", "Estado", "Granizadas", "Daño %", "Daño malla %", "Rend. kg/ha",
                   "Sin protección", "Compensación", "Fondo Comp.", "Malla")
        self.tv_corrida = ttk.Treeview(tab, columns=cols, show="headings", height=21)
        for c, t in zip(cols, titulos):
            self.tv_corrida.heading(c, text=t)
            self.tv_corrida.column(c, width=105 if c in ("sin", "comp", "fondo", "malla", "danio_m") else 75,
                                   anchor="e" if c not in ("anio", "estado", "dias") else "center")
        self.tv_corrida.tag_configure("fuerte", background="#f8d7d3")
        self.tv_corrida.tag_configure("total", font=("Segoe UI", 9, "bold"))
        self.tv_corrida.pack(fill=tk.X, padx=6, pady=4)
        self.fig_corrida = Figure(figsize=(10, 3.4), constrained_layout=True)
        self.canvas_corrida = FigureCanvasTkAgg(self.fig_corrida, master=tab)
        self.canvas_corrida.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

    def _dibujar_corrida(self, res, p, replica):
        r = replica - 1
        danio = res.danio[r]
        comp = np.where(danio > p.fca_umbral,
                        p.fca_compensacion_ha * p.hectareas * (danio if p.fca_modo == "proporcional" else 1), 0)
        anu = {a: res.anuales[a][r] for a in ALTERNATIVAS}
        self.lbl_corrida.configure(text=(
            f"Réplica {replica} de {p.replicas} – semilla {p.semilla}. "
            f"Filas en rojo: años con daño mayor al {fmt(p.fca_umbral * 100, 0)} % (granizo fuerte). "
            "Montos en millones de pesos."))
        self.tv_corrida.delete(*self.tv_corrida.get_children())
        for t in range(p.anios):
            fuerte = danio[t] > p.fca_umbral
            self.tv_corrida.insert("", tk.END, tags=("fuerte",) if fuerte else (), values=(
                t + 1, "G" if res.estados[r, t] else "S", int(res.dias[r, t]),
                fmt(danio[t] * 100, 1), fmt(res.danio_malla[r, t] * 100, 1),
                fmt(res.rendimiento[r, t], 0),
                fmt(anu["sin_proteccion"][t] / 1e6), fmt(comp[t] / 1e6),
                fmt(anu["fondo"][t] / 1e6), fmt(anu["malla"][t] / 1e6)))
        self.tv_corrida.insert("", tk.END, tags=("total",), values=(
            "Total", "", int(res.dias[r].sum()), "", "", "",
            fmt(anu["sin_proteccion"].sum() / 1e6), fmt(comp.sum() / 1e6),
            fmt(anu["fondo"].sum() / 1e6), fmt(anu["malla"].sum() / 1e6)))

        f = self.fig_corrida
        f.clear()
        ax = f.add_subplot(111)
        anios = np.arange(1, p.anios + 1)
        for t in np.where(danio > p.fca_umbral)[0]:
            ax.axvspan(t + 0.5, t + 1.5, color="#f8d7d3", zorder=0)
        for a in ALTERNATIVAS:
            ax.plot(anios, np.cumsum(anu[a]) / 1e6, marker="o", ms=4, color=COLORES[a], label=NOMBRES[a])
        ax.axhline(0, color="black", lw=0.8)
        ax.set_xticks(anios)
        ax.set_xlabel("año")
        ax.set_ylabel("ganancia acumulada (millones $)")
        ax.set_title("Ganancia acumulada – años sombreados: granizo fuerte")
        ax.legend(loc="upper left")
        ax.grid(alpha=0.3)
        self.canvas_corrida.draw()

    # --------------------------------------------------------------- pestaña 3
    def _pestania_montecarlo(self):
        tab = ttk.Frame(self.pestanias)
        self.pestanias.add(tab, text="  3 · Monte Carlo  ")
        self.fig_mc = Figure(figsize=(10, 4.6), constrained_layout=True)
        self.canvas_mc = FigureCanvasTkAgg(self.fig_mc, master=tab)
        self.canvas_mc.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        cols = ("ind",) + ALTERNATIVAS
        self.tv_mc = ttk.Treeview(tab, columns=cols, show="headings", height=9)
        self.tv_mc.heading("ind", text="Indicador")
        self.tv_mc.column("ind", width=330, anchor="w")
        for a in ALTERNATIVAS:
            self.tv_mc.heading(a, text=NOMBRES[a])
            self.tv_mc.column(a, width=170, anchor="e")
        self.tv_mc.tag_configure("mejor", foreground="#1e6b1e")
        self.tv_mc.pack(fill=tk.X, padx=6, pady=(0, 6))

    def _dibujar_montecarlo(self, res, p):
        ind = mc.indicadores(res)
        filas = [
            (f"Ganancia media en {p.anios} años", "media", fmt_m, max),
            ("Desvío estándar", "desvio", fmt_m, min),
            ("Percentil 5 (P5) – escenario malo", "p5", fmt_m, max),
            ("Percentil 95 (P95)", "p95", fmt_m, None),
            ("Ganancia media por año", "media_anual", fmt_m, max),
            ("% de años con pérdida", "pct_anios_perdida", lambda v: f"{fmt(v, 1)} %", min),
            (f"% de réplicas con pérdida en {p.anios} años", "pct_replicas_perdida", lambda v: f"{fmt(v, 2)} %", min),
            ("Peor año (mínimo de todas las réplicas)", "peor_anio", fmt_m, max),
        ]
        self.tv_mc.delete(*self.tv_mc.get_children())
        for titulo, clave, f_fmt, mejor in filas:
            valores = [ind[a][clave] for a in ALTERNATIVAS]
            celdas = [f_fmt(v) for v in valores]
            if mejor is not None:
                i = valores.index(mejor(valores))
                celdas[i] = "★ " + celdas[i]
            self.tv_mc.insert("", tk.END, values=(titulo, *celdas))

        f = self.fig_mc
        f.clear()
        ejes = f.subplots(1, 3, sharex=True, sharey=True)
        todos = np.concatenate([res.totales[a] for a in ALTERNATIVAS]) / 1e6
        bins = np.linspace(todos.min(), todos.max(), 60)
        for ax, a in zip(ejes, ALTERNATIVAS):
            tot = res.totales[a] / 1e6
            ax.hist(tot, bins=bins, color=COLORES[a], alpha=0.85)
            ax.axvline(ind[a]["media"] / 1e6, color="black", ls="--", label=f"Media {fmt(ind[a]['media'] / 1e6, 1)}")
            ax.axvline(ind[a]["p5"] / 1e6, color="black", ls=":", label=f"P5 {fmt(ind[a]['p5'] / 1e6, 1)}")
            ax.axvline(0, color="#999999", lw=0.8)
            ax.set_title(NOMBRES[a])
            ax.set_xlabel(f"ganancia total {p.anios} años (millones $)")
            ax.legend(fontsize=8)
        ejes[0].set_ylabel(f"réplicas (de {p.replicas})")
        self.canvas_mc.draw()

    # ---------------------------------------------------------------- calcular
    def calcular(self):
        try:
            p, replica = self._leer_parametros()
        except ValueError as e:
            messagebox.showerror("Datos inválidos", str(e))
            return
        self.estado.set("Calculando…")
        self.config(cursor="watch")
        self.update_idletasks()
        try:
            res = mc.correr(p)
            self.resultado = res
            self._dibujar_clima(res, p)
            self._dibujar_corrida(res, p, replica)
            self._dibujar_montecarlo(res, p)
            self.estado.set(
                f"Listo: {fmt(p.replicas, 0)} réplicas × {p.anios} años, semilla {p.semilla}, "
                f"{fmt(res.numeros_usados, 0)} números aleatorios usados.")
        except Exception as e:  # noqa: BLE001 – se muestra al usuario
            messagebox.showerror("Error al calcular", str(e))
            self.estado.set("Error.")
        finally:
            self.config(cursor="")


if __name__ == "__main__":
    App().mainloop()
