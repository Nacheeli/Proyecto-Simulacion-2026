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
from simulador import sensibilidad as sens
from simulador import estadistica as est

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
        ("frecuencia_mult", "Multiplicador granizadas", "", 1, float),
        ("severidad", "Factor severidad del daño", "S", 1, float),
    ]),
    ("Economía", [
        ("precio_uva", "Precio uva ($/kg)", "S", 1, float),
        ("costo_produccion_ha", "Costo producción ($/ha/año)", "S", 1, float),
        ("tipo_cambio", "Tipo de cambio ($/USD)", "S", 1, float),
        ("tasa_descuento", "Tasa de descuento real (%)", "S", 100, float),
        ("costo_fijo_finca", "Costo fijo por finca ($/año)", "S", 1, float),
    ]),
    ("Fondo Compensador (Específica, Sur)", [
        ("fca_aporte_ha", "Aporte ($/ha/año)", "R", 1, float),
        ("fca_compensacion_ha", "Compensación ($/ha)", "R", 1, float),
        ("fca_umbral", "Umbral de daño (%)", "R", 100, float),
        ("fca_modo", "Compensación", "S", ["proporcional", "fijo"], str),
        ("fca_condicion", "Paga si daño … umbral", "S", [">=", ">"], str),
        ("fca_max_hectareas", "Máximo de hectáreas", "R", 1, float),
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
    ("Sensibilidad (pestaña 4)", [
        ("sens_replicas", "Réplicas por factor severidad", "", 1, int),
        ("sens_precio_min", "Precio desde ($/kg)", "", 1, float),
        ("sens_precio_max", "Precio hasta ($/kg)", "", 1, float),
        ("sens_precio_paso", "Precio paso ($/kg)", "", 1, float),
        ("sens_sev_min", "Severidad desde", "", 1, float),
        ("sens_sev_max", "Severidad hasta", "", 1, float),
        ("sens_sev_paso", "Severidad paso", "", 1, float),
        ("sens_ha_max", "Hectáreas hasta (mapa)", "", 1, int),
        ("conv_replicas_max", "Réplicas máx. convergencia", "", 1, int),
        ("criterio_p5_minimo", "Criterio: P5 del VAN > ($)", "", 1, float),
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
        self._pestania_decision()
        self._pestania_precision()

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
        desde, hasta, probs = [], [], []
        for var_a, var_b, var_p in self.vars_danio:
            desde.append(leer_numero(var_a.get()) / 100)
            hasta.append(leer_numero(var_b.get()) / 100)
            probs.append(leer_numero(var_p.get()) / 100)
        p.danio_desde, p.danio_hasta, p.danio_probabilidades = desde, hasta, probs
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
        for c, t, w in zip(cols, ("Días", "Años", "Real", "Acum. real", "Simulada"),
                           (38, 42, 68, 72, 78)):
            self.tv_dias.heading(c, text=t)
            self.tv_dias.column(c, width=w, anchor="center")
        self.tv_dias.pack(padx=4, pady=4)

        # Tabla de daño editable
        f_danio = ttk.LabelFrame(arriba, text="Daño por granizada (S)")
        f_danio.pack(side=tk.LEFT, fill=tk.Y, padx=4)
        for col, texto in enumerate(("Desde %", "Hasta %", "Prob. %")):
            ttk.Label(f_danio, text=texto).grid(row=0, column=col, padx=2)
        p = Parametros()
        for i, (a, b, pr) in enumerate(zip(p.danio_desde, p.danio_hasta, p.danio_probabilidades), start=1):
            va, vb = tk.StringVar(value=fmt(a * 100, 0)), tk.StringVar(value=fmt(b * 100, 0))
            vp = tk.StringVar(value=fmt(pr * 100, 1))
            for col, v in enumerate((va, vb, vp)):
                ttk.Entry(f_danio, textvariable=v, width=5, justify="right").grid(row=i, column=col, padx=2, pady=1)
            vp.trace_add("write", lambda *x: self._actualizar_suma_danio())
            self.vars_danio.append((va, vb, vp))
        self.lbl_suma_danio = ttk.Label(f_danio)
        self.lbl_suma_danio.grid(row=len(self.vars_danio) + 1, column=0, columnspan=3, pady=2)
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
            total = sum(leer_numero(vp.get()) for _, _, vp in self.vars_danio)
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
        eq = mc.equilibrio_fondo(res)
        self.lbl_verificacion.configure(text=(
            "Prueba χ² generador\n"
            f" n=10.000 k=10 α=0,05\n"
            f" χ²={fmt(chi['estadistico'])} crít={fmt(chi['critico'])}\n"
            f" {'NO se rechaza' if chi['acepta_h0'] else 'SE RECHAZA'} H0\n"
            "Daño simulado\n"
            f" por granizada {fmt(resumen['danio_medio_evento'] * 100, 1)} %\n"
            f" medio anual   {fmt(resumen['danio_medio_anual'] * 100, 1)} %\n"
            f" anual c/malla {fmt(resumen['danio_medio_anual_malla'] * 100, 1)} %\n"
            f" años > umbral {fmt(resumen['prob_danio_supera_umbral'] * 100, 1)} %\n"
            f" años = umbral {fmt(resumen['prob_danio_igual_umbral'] * 100, 2)} %\n"
            f" DACC Sur {fmt(dacc['con_lucha'] * 100, 1)}–{fmt(dacc['sin_lucha'] * 100, 1)} %\n"
            f"Fondo (daño {p.fca_condicion} {fmt(p.fca_umbral * 100, 0)} %)\n"
            f" P(cobrar) {fmt(eq['prob_cobrar'] * 100, 1)} %/año\n"
            f" pago medio {fmt(eq['pago_medio_anual'] / 1e6)} M\n"
            f" aporte     {fmt(eq['aporte_anual'] / 1e6)} M\n"
            f" pagos/aportes {fmt(eq['pagos_sobre_aportes'])}"
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

        ev = res.eventos_danio * 100
        if ev.size:
            ax2.hist(ev, bins=np.arange(0, 102, 2), color=COLOR_SUPUESTO,
                     weights=np.full(ev.size, 100 / ev.size))
        ax2.set_yscale("log")
        ax2.set_title("Daño por granizada simulado (SUPUESTO)")
        ax2.set_xlabel("daño %")
        ax2.set_ylabel("% de granizadas (escala log)")

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
        self.tv_corrida = ttk.Treeview(tab, columns=cols, show="headings", height=22)
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
        comp = res.compensacion[r]
        anu = {a: res.anuales[a][r] for a in ALTERNATIVAS}
        self.lbl_corrida.configure(text=(
            f"Réplica {replica} de {p.replicas} – semilla {p.semilla}. "
            f"Filas en rojo: años con daño {p.fca_condicion} {fmt(p.fca_umbral * 100, 0)} % (granizo fuerte, paga el Fondo). "
            "Montos en millones de pesos."))
        self.tv_corrida.delete(*self.tv_corrida.get_children())
        for t in range(p.anios):
            fuerte = comp[t] > 0
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
        self.tv_corrida.insert("", tk.END, tags=("total",), values=(
            f"VAN {fmt(p.tasa_descuento * 100, 1)} %", "", "", "", "", "",
            fmt(res.van["sin_proteccion"][r] / 1e6), "",
            fmt(res.van["fondo"][r] / 1e6), fmt(res.van["malla"][r] / 1e6)))

        f = self.fig_corrida
        f.clear()
        ax = f.add_subplot(111)
        anios = np.arange(1, p.anios + 1)
        for t in np.where(comp > 0)[0]:
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
        self.tv_mc = ttk.Treeview(tab, columns=cols, show="headings", height=12)
        self.tv_mc.heading("ind", text="Indicador")
        self.tv_mc.column("ind", width=330, anchor="w")
        for a in ALTERNATIVAS:
            self.tv_mc.heading(a, text=NOMBRES[a])
            self.tv_mc.column(a, width=170, anchor="e")
        self.tv_mc.tag_configure("mejor", foreground="#1e6b1e")
        self.tv_mc.pack(fill=tk.X, padx=6, pady=(0, 6))

    def _dibujar_montecarlo(self, res, p):
        ind = mc.indicadores(res)
        tasa = fmt(p.tasa_descuento * 100, 1)
        filas = [
            (f"VAN medio ({tasa} %) – indicador principal", "van_media", fmt_m, max),
            ("IC 95 % del VAN medio (±)", "van_ic", lambda v: f"± {fmt(v / 1e6, 3)} M", None),
            ("VAN – desvío estándar", "van_desvio", fmt_m, min),
            ("VAN – percentil 5 (P5)", "van_p5", fmt_m, max),
            ("VAN – percentil 95 (P95)", "van_p95", fmt_m, None),
            ("% de réplicas con VAN negativo", "pct_van_negativo", lambda v: f"{fmt(v, 2)} %", min),
            (f"Suma sin descontar {p.anios} años – media", "media", fmt_m, max),
            ("Suma sin descontar – P5", "p5", fmt_m, max),
            ("% de años con pérdida", "pct_anios_perdida", lambda v: f"{fmt(v, 1)} %", min),
            ("Percentil 1 de los resultados anuales", "p1_anual", fmt_m, max),
            ("Peor año (mínimo de todas las réplicas)", "peor_anio", fmt_m, max),
        ]
        for a, ic in est.ic_van(res).items():
            ind[a]["van_ic"] = ic["semiancho"]
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
        todos = np.concatenate([res.van[a] for a in ALTERNATIVAS]) / 1e6
        bins = np.linspace(todos.min(), todos.max(), 60)
        for ax, a in zip(ejes, ALTERNATIVAS):
            v = res.van[a] / 1e6
            ax.hist(v, bins=bins, color=COLORES[a], alpha=0.85)
            ax.axvline(ind[a]["van_media"] / 1e6, color="black", ls="--",
                       label=f"Media {fmt(ind[a]['van_media'] / 1e6, 1)}")
            ax.axvline(ind[a]["van_p5"] / 1e6, color="black", ls=":", label=f"P5 {fmt(ind[a]['van_p5'] / 1e6, 1)}")
            ax.axvline(0, color="#999999", lw=0.8)
            ax.set_title(NOMBRES[a])
            ax.set_xlabel(f"VAN {p.anios} años al {tasa} % (millones $)")
            ax.legend(fontsize=8)
        ejes[0].set_ylabel(f"réplicas (de {p.replicas})")
        self.canvas_mc.draw()

    # --------------------------------------------------------------- pestaña 4
    def _pestania_decision(self):
        tab = ttk.Frame(self.pestanias)
        self.pestanias.add(tab, text="  4 · Decisión  ")
        self.lbl_decision = ttk.Label(tab, justify="left")
        self.lbl_decision.pack(anchor="w", padx=8, pady=(6, 0))
        self.fig_dec = Figure(figsize=(11, 5.6), constrained_layout=True)
        self.canvas_dec = FigureCanvasTkAgg(self.fig_dec, master=tab)
        self.canvas_dec.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        cols = ("ind",) + tuple(f"{a}_{k}" for a in ALTERNATIVAS for k in ("markov", "indep"))
        self.tv_pers = ttk.Treeview(tab, columns=cols, show="headings", height=7)
        self.tv_pers.heading("ind", text="Persistencia: Markov real vs años independientes")
        self.tv_pers.column("ind", width=290, anchor="w")
        for a in ALTERNATIVAS:
            for k, t in (("markov", "Markov"), ("indep", "Indep.")):
                self.tv_pers.heading(f"{a}_{k}", text=f"{NOMBRES[a].split()[0]} – {t}")
                self.tv_pers.column(f"{a}_{k}", width=110, anchor="e")
        self.tv_pers.pack(fill=tk.X, padx=6, pady=(0, 6))

    def _dibujar_decision(self, res, p):
        ind = mc.indicadores(res)
        precios = np.arange(p.sens_precio_min, p.sens_precio_max + p.sens_precio_paso / 2, p.sens_precio_paso)
        barrido = sens.barrido_precio(res, precios)
        factores = np.arange(p.sens_sev_min, p.sens_sev_max + p.sens_sev_paso / 2, p.sens_sev_paso)
        hectareas = np.arange(1, p.sens_ha_max + 1)
        sev = sens.analisis_severidad(p, factores, precios, hectareas)
        pers = sens.persistencia(p, res)

        mejor_base = sens.elegir_mejor(ind, p.criterio_p5_minimo)
        texto_mejor = NOMBRES[ALTERNATIVAS[mejor_base]] if mejor_base != sens.NINGUNA else "ninguna"
        cambios = sens.factor_cambio_fondo(sev)
        texto_cambio = "; ".join(
            f"entre ×{fmt(a)} y ×{fmt(b)} pasa de {NOMBRES[ALTERNATIVAS[m1]] if m1 >= 0 else 'ninguna'} "
            f"a {NOMBRES[ALTERNATIVAS[m2]] if m2 >= 0 else 'ninguna'}" for a, b, m1, m2 in cambios) or "no cambia en el rango"
        self.lbl_decision.configure(text=(
            f"Criterio: mayor VAN medio entre las alternativas disponibles con P5 del VAN > {fmt_m(p.criterio_p5_minimo)}. "
            f"Con los parámetros actuales: {texto_mejor}.\n"
            f"Severidad – el Fondo como mejor alternativa: {texto_cambio}.   "
            f"Barridos de severidad: {sev['replicas']} réplicas por punto, misma semilla. "
            f"Fondo disponible hasta {fmt(p.fca_max_hectareas, 0)} ha."))

        from matplotlib.colors import ListedColormap
        from matplotlib.patches import Patch
        cmap = ListedColormap(["#d9d9d9"] + [COLORES[a] for a in ALTERNATIVAS])
        leyenda_mapa = [Patch(color=COLORES[a], label=NOMBRES[a]) for a in ALTERNATIVAS] + \
                       [Patch(color="#d9d9d9", label="Ninguna")]
        paso_f = p.sens_sev_paso

        f = self.fig_dec
        f.clear()
        (ax1, ax2, ax3), (ax4, ax5, ax6) = f.subplots(2, 3)

        # 1. Rentabilidad vs riesgo
        for a in ALTERNATIVAS:
            ax1.scatter(ind[a]["van_p5"] / 1e6, ind[a]["van_media"] / 1e6, s=80, color=COLORES[a], label=NOMBRES[a])
        ax1.axvline(p.criterio_p5_minimo / 1e6, color="#999999", ls=":")
        ax1.set_xlabel("P5 del VAN (millones $) → menos riesgo")
        ax1.set_ylabel("VAN medio (millones $)")
        ax1.set_title("Rentabilidad vs riesgo")
        ax1.legend(fontsize=7)
        ax1.grid(alpha=0.3)

        # 2. Precio de la uva (severidad base)
        for a in ALTERNATIVAS:
            d = barrido["por_alternativa"][a]
            ax2.plot(precios, np.array(d["van_media"]) / 1e6, color=COLORES[a], marker="o", ms=2, label=f"{NOMBRES[a]} media")
            ax2.plot(precios, np.array(d["van_p5"]) / 1e6, color=COLORES[a], ls=":", label=f"{NOMBRES[a]} P5")
        ax2.axhline(0, color="black", lw=0.8)
        ax2.axvline(p.precio_uva, color="#999999", ls="--")
        ax2.set_xlabel("precio de la uva ($/kg)")
        ax2.set_ylabel("VAN (millones $)")
        ax2.set_title("Sensibilidad al precio")
        ax2.legend(fontsize=6, ncol=2)
        ax2.grid(alpha=0.3)

        # 3. Severidad: daño y equilibrio del Fondo
        ok = sev["dentro_dacc"]
        if ok.any():
            ax3.axvspan(factores[ok].min() - paso_f / 2, factores[ok].max() + paso_f / 2,
                        color="#f2c14e", alpha=0.3, label="pérdida dentro del rango DACC")
        ax3.plot(factores, sev["perdida_media"] * 100, marker="o", ms=3, color="black", label="pérdida media anual %")
        ax3.plot(factores, sev["prob_paga"] * 100, marker="s", ms=3, color="#4f81bd",
                 label=f"P(daño {p.fca_condicion} {fmt(p.fca_umbral * 100, 0)} %) %")
        ax3.set_xlabel("factor de severidad del daño")
        ax3.set_ylabel("%")
        ax3b = ax3.twinx()
        ax3b.plot(factores, sev["pagos_sobre_aportes"], color="#c55a11", ls="--", label="pagos / aportes (eje der.)")
        ax3b.axhline(1, color="#c55a11", lw=0.6, ls=":")
        ax3b.set_ylabel("pagos / aportes del Fondo")
        for a, b, _, _ in cambios:
            ax3.axvline((a + b) / 2, color="red", lw=1)
        ax3.axvline(p.severidad, color="#999999", ls="--")
        lineas = ax3.get_legend_handles_labels()
        lineas_b = ax3b.get_legend_handles_labels()
        ax3.legend(lineas[0] + lineas_b[0], lineas[1] + lineas_b[1], fontsize=6, loc="upper left")
        ax3.set_title("Severidad del daño")
        ax3.grid(alpha=0.3)

        # 4. Mapa precio × severidad
        ax4.imshow(sev["mapa_precio"] + 1, cmap=cmap, vmin=0, vmax=3, aspect="auto", origin="lower",
                   extent=(precios[0] - p.sens_precio_paso / 2, precios[-1] + p.sens_precio_paso / 2,
                           factores[0] - paso_f / 2, factores[-1] + paso_f / 2))
        if ok.any():
            for y in (factores[ok].min() - paso_f / 2, factores[ok].max() + paso_f / 2):
                ax4.axhline(y, color="black", lw=1.2)
        ax4.axvline(p.precio_uva, color="black", ls="--", lw=0.8)
        ax4.axhline(p.severidad, color="black", ls="--", lw=0.8)
        ax4.set_xlabel("precio de la uva ($/kg)")
        ax4.set_ylabel("factor de severidad")
        ax4.set_title("Mejor: precio × severidad")
        ax4.legend(handles=leyenda_mapa, fontsize=6, loc="upper left")

        # 5. Mapa hectáreas × severidad
        ax5.imshow(sev["mapa_ha"] + 1, cmap=cmap, vmin=0, vmax=3, aspect="auto", origin="lower",
                   extent=(hectareas[0] - 0.5, hectareas[-1] + 0.5, factores[0] - paso_f / 2, factores[-1] + paso_f / 2))
        ax5.axvline(p.fca_max_hectareas + 0.5, color="black", lw=1.2)
        ax5.axvline(p.hectareas, color="black", ls="--", lw=0.8)
        ax5.axhline(p.severidad, color="black", ls="--", lw=0.8)
        ax5.set_xlabel(f"hectáreas (costo fijo por finca {fmt_m(p.costo_fijo_finca)})")
        ax5.set_ylabel("factor de severidad")
        ax5.set_title("Mejor: hectáreas × severidad")

        # 6. Persistencia
        x = np.arange(len(ALTERNATIVAS))
        for k, (nombre, desplaz, rel) in enumerate((("markov", -0.2, "Markov real"), ("independiente", 0.2, "Independientes"))):
            ii = pers[nombre]["indicadores"]
            ax6.bar(x + desplaz, [ii[a]["van_media"] / 1e6 for a in ALTERNATIVAS], 0.4,
                    color=["#bfbfbf", "#7f7f7f"][k], label=f"{rel} – media")
            ax6.scatter(x + desplaz, [ii[a]["van_p5"] / 1e6 for a in ALTERNATIVAS], color="black",
                        marker=["v", "^"][k], zorder=3, label=f"{rel} – P5")
        ax6.set_xticks(x, [NOMBRES[a].split()[0] for a in ALTERNATIVAS])
        ax6.set_ylabel("VAN (millones $)")
        ax6.set_title(f"Persistencia (G = {fmt(pers['pi_G'], 3)})")
        ax6.legend(fontsize=6)
        ax6.grid(alpha=0.3, axis="y")
        self.canvas_dec.draw()

        self.tv_pers.delete(*self.tv_pers.get_children())
        filas = [("VAN medio", "van_media", fmt_m), ("VAN P5", "van_p5", fmt_m),
                 ("VAN desvío", "van_desvio", fmt_m),
                 ("% años con pérdida", "pct_anios_perdida", lambda v: f"{fmt(v, 1)} %")]
        for titulo, clave, ff in filas:
            celdas = []
            for a in ALTERNATIVAS:
                for nombre in ("markov", "independiente"):
                    celdas.append(ff(pers[nombre]["indicadores"][a][clave]))
            self.tv_pers.insert("", tk.END, values=(titulo, *celdas))
        m, i = pers["markov"], pers["independiente"]
        racha = (fmt(m["racha_G_media"], 1), fmt(i["racha_G_media"], 1)) * len(ALTERNATIVAS)
        dos = (f"{fmt(m['prob_2_fuertes_seguidos'] * 100, 1)} %",
               f"{fmt(i['prob_2_fuertes_seguidos'] * 100, 1)} %") * len(ALTERNATIVAS)
        self.tv_pers.insert("", tk.END, values=("Racha máx. media de años G (clima)", *racha))
        self.tv_pers.insert("", tk.END, values=("P(2+ años fuertes seguidos) (clima)", *dos))

    # --------------------------------------------------------------- pestaña 5
    def _pestania_precision(self):
        tab = ttk.Frame(self.pestanias)
        self.pestanias.add(tab, text="  5 · Precisión  ")
        self.lbl_precision = ttk.Label(tab, justify="left", wraplength=940)
        self.lbl_precision.pack(anchor="w", padx=8, pady=(6, 0))
        self.fig_prec = Figure(figsize=(11, 3.2), constrained_layout=True)
        self.canvas_prec = FigureCanvasTkAgg(self.fig_prec, master=tab)
        self.canvas_prec.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        abajo = ttk.Frame(tab)
        abajo.pack(fill=tk.X, padx=6, pady=(0, 6))
        cols = ("par", "dif", "nac", "ind", "red", "rho")
        self.tv_dif = ttk.Treeview(abajo, columns=cols, show="headings", height=3)
        for c, t, w in zip(cols, ("Diferencia de VAN medio", "Estimación", "IC 95 % con NAC",
                                  "IC 95 % independientes", "Más angosto", "Correlación"),
                           (200, 90, 150, 150, 90, 85)):
            self.tv_dif.heading(c, text=t)
            self.tv_dif.column(c, width=w, anchor="e" if c != "par" else "w")
        self.tv_dif.pack(side=tk.TOP, fill=tk.X, expand=True, pady=(0, 4))
        cols = ("tasa", "fpk", "fusd", "spk", "susd")
        self.tv_corte = ttk.Treeview(abajo, columns=cols, show="headings", height=4)
        for c, t, w in zip(cols, ("Tasa", "Malla = Fondo $/kg", "USD/kg",
                                  "Malla = Sin $/kg", "USD/kg"), (90, 125, 70, 115, 70)):
            self.tv_corte.heading(c, text=t)
            self.tv_corte.column(c, width=w, anchor="e")
        self.tv_corte.pack(side=tk.TOP, fill=tk.X, expand=True)

    def _dibujar_precision(self, res, p):
        n = p.replicas
        tamanios = sorted({t for t in (100, 500, 1000, 5000, 10_000, p.conv_replicas_max) if t <= p.conv_replicas_max})
        conv = est.convergencia(p, tamanios)
        dif = est.ic_diferencias(res, est.corrida_independiente(p))
        factores = np.round(np.arange(0.25, 0.3501, 0.025), 4)
        filas_sev = est.ic_corte_severidad(p, factores)
        cruce = est.cruce_severidad(filas_sev)
        cortes_tasa = est.cortes_por_tasa(res.esc, p, (0.03, 0.05, 0.08))
        tc_doble = est.corte_escalando_tipo_de_cambio(res.esc, p, 2.0)
        normal = est.cortes_malla(res.esc, p)

        def num(x, d=3):
            return fmt(x, d) if x is not None else "–"

        self.lbl_precision.configure(text=(
            f"IC 95 % = media ± 1,96·s/√n, con n = {fmt(n, 0)} réplicas. NAC = números aleatorios comunes "
            f"(las tres alternativas sobre los mismos escenarios); 'independientes' toma la segunda alternativa "
            f"de una corrida con semilla {p.semilla + 1}.\n"
            f"Corte de severidad (VAN Fondo = VAN Sin): ×{num(cruce['estimado'])}  "
            f"(IC 95 % ×{num(cruce['inferior'])} a ×{num(cruce['superior'])}).   "
            f"Corte de la malla en USD/kg con el tipo de cambio ×2: contra Sin "
            f"{num(normal['sin_proteccion']['usd_kg'])} → {num(tc_doble['sin_proteccion']['usd_kg'])} (no cambia); "
            f"contra el Fondo {num(normal['fondo']['usd_kg'])} → {num(tc_doble['fondo']['usd_kg'])} "
            f"(cambia: el Fondo está fijo en pesos)."))

        f = self.fig_prec
        f.clear()
        ejes = f.subplots(1, 4)
        for ax, a in zip(ejes[:3], ALTERNATIVAS):
            m = conv[a]["media"] / 1e6
            s = conv[a]["semiancho"] / 1e6
            ax.fill_between(conv["tamanios"], m - s, m + s, color=COLORES[a], alpha=0.2)
            ax.plot(conv["tamanios"], m, color=COLORES[a], marker="o", ms=3)
            ax.axhline(m[-1], color="#999999", lw=0.8, ls=":")
            ax.axvline(n, color="black", ls="--", lw=0.8)
            ax.set_xscale("log")
            ax.set_title(f"Convergencia – {NOMBRES[a]}", fontsize=9)
            ax.set_xlabel("réplicas")
            ax.grid(alpha=0.3)
        ejes[0].set_ylabel("VAN medio ± IC 95 % (M$)")
        ax = ejes[3]
        x = [r["factor"] for r in filas_sev]
        med = np.array([r["media"] for r in filas_sev]) / 1e6
        semi = np.array([r["semiancho"] for r in filas_sev]) / 1e6
        ax.fill_between(x, med - semi, med + semi, color="#7f7f7f", alpha=0.3)
        ax.plot(x, med, color="black", marker="o", ms=3)
        ax.axhline(0, color="black", lw=0.8)
        if cruce["estimado"] is not None:
            ax.axvline(cruce["estimado"], color="red", lw=1)
        ax.set_title("VAN Fondo − Sin según severidad (NAC)", fontsize=9)
        ax.set_xlabel("factor de severidad")
        ax.set_ylabel("diferencia ± IC 95 % (M$)")
        ax.grid(alpha=0.3)
        self.canvas_prec.draw()

        self.tv_dif.delete(*self.tv_dif.get_children())
        for (a, b), fila in dif.items():
            nac, ind = fila["nac"], fila["independiente"]
            self.tv_dif.insert("", tk.END, values=(
                f"{NOMBRES[a]} − {NOMBRES[b]}", fmt_m(nac["media"]),
                f"± {fmt(nac['semiancho'] / 1e6, 3)} M", f"± {fmt(ind['semiancho'] / 1e6, 3)} M",
                f"{fmt(fila['reduccion'], 1)} veces", fmt(fila["correlacion"], 3)))
        self.tv_corte.delete(*self.tv_corte.get_children())
        for t, c in cortes_tasa.items():
            self.tv_corte.insert("", tk.END, values=(
                f"{fmt(t * 100, 0)} %", num(c["fondo"]["pesos_kg"], 0), num(c["fondo"]["usd_kg"], 3),
                num(c["sin_proteccion"]["pesos_kg"], 0), num(c["sin_proteccion"]["usd_kg"], 3)))

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
            self.estado.set("Calculando sensibilidad…")
            self.update_idletasks()
            self._dibujar_decision(res, p)
            self.estado.set("Calculando precisión (convergencia e intervalos)…")
            self.update_idletasks()
            self._dibujar_precision(res, p)
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
