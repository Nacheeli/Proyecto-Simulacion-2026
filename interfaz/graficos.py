"""
Gráficos del simulador. Cada función recibe una Figure de matplotlib vacía y
el diccionario de resultados de calculos.calcular_todo(), y dibuja en ella.
Se usan igual para los gráficos embebidos en la app y para exportar los PNG
del informe (GRAFICOS al final del archivo).

Colores, líneas y marcadores salen de interfaz/estilo.py.
"""

import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.ticker import FuncFormatter, NullFormatter

from simulador.finca import ALTERNATIVAS
from simulador.sensibilidad import NINGUNA
from . import estilo as E
from .formato import fmt, fmt_pct

A = E.ALTERNATIVAS_ESTILO
SIMBOLO = {">=": "≥", ">": ">"}


def _linea(a):
    e = A[a]
    return {"color": e["color"], "linestyle": e["linestyle"], "marker": e["marker"]}


def _nota(ax, texto, color=E.TEXTO_2, y=0.97, x=0.99, ha="right"):
    ax.text(x, y, texto, transform=ax.transAxes, ha=ha, va="top", fontsize="small", color=color)


def _m(x):
    return np.asarray(x, dtype=float) / 1e6


# ======================================================== pestaña 1 · clima
def dias_granizo(fig, R):
    ax = fig.add_subplot(111)
    d = R["dias_real"]
    sim = R["clima"]["frecuencia_dias"]
    todos = sorted(set(d["valores"]) | set(sim))
    real = dict(zip(d["valores"], d["probs"]))
    x = np.array(todos)
    ax.bar(x - 0.2, [real.get(k, 0) * 100 for k in todos], 0.4, color=E.REAL, label="Real 1974–2024")
    ax.bar(x + 0.2, [sim.get(k, 0) * 100 for k in todos], 0.4, color=E.SIMULADO, label="Simulado")
    ax.set_xticks(x)
    ax.set_xlabel("días con granizo en el año")
    ax.set_ylabel("% de los años")
    ax.set_title("Días con granizo por año")
    ax.legend(loc="upper right")


def danio_por_granizada(fig, R):
    ax = fig.add_subplot(111)
    ev = R["res"].eventos_danio * 100
    if ev.size:
        positivos = ev[ev > 0]
        ax.hist(positivos, bins=np.arange(0, 101, 5), color=E.SIMULADO, edgecolor="white",
                weights=np.full(positivos.size, 100 / ev.size))
        _nota(ax, f"{fmt(100 * (ev == 0).mean(), 0)} % de las granizadas sin daño\n(no se grafican)", E.SUPUESTO)
    ax.set_xlim(0, 100)
    ax.set_xlabel("daño de la granizada (%)")
    ax.set_ylabel("% de las granizadas")
    ax.set_title("Daño por granizada (supuesto)")


def danio_anual(fig, R):
    ax = fig.add_subplot(111)
    p = R["p"]
    d = R["res"].danio.ravel() * 100
    dacc = R["dacc"]
    ax.axvspan(dacc["con_lucha"] * 100, dacc["sin_lucha"] * 100, facecolor=E.BANDA_DACC, edgecolor=E.SUPUESTO,
               lw=0.9, zorder=0, label="Rango DACC")
    positivos = d[d > 0]
    ax.hist(positivos, bins=np.arange(0, 101, 5), color=E.SIMULADO, edgecolor="white",
            weights=np.full(positivos.size, 100 / d.size))
    ax.axvline(d.mean(), color=E.TEXTO, lw=1.4, label=f"Media {fmt(d.mean(), 1)} %")
    ax.axvline(p.fca_umbral * 100, color=E.TEXTO_2, ls="--", lw=1, label="Umbral Fondo")
    ax.set_xlim(0, 100)
    ax.set_xlabel("daño del año (%)")
    ax.set_ylabel("% de los años")
    ax.set_title("Daño anual simulado")
    fig.legend(loc="outside lower center", ncol=3, fontsize="small", columnspacing=1.0, handlelength=1.5)
    _nota(ax, f"{fmt(100 * (d == 0).mean(), 0)} % de los años sin daño\n(no se grafican)")


# ===================================================== pestaña 2 · corrida
def ganancia_acumulada(fig, R):
    ax = fig.add_subplot(111)
    res, p = R["res"], R["p"]
    r = R["replica"] - 1
    anios = np.arange(1, p.anios + 1)
    fuertes = np.where(res.compensacion[r] > 0)[0] if p.hectareas <= p.fca_max_hectareas else \
        np.where(res.danio[r] >= p.fca_umbral)[0]
    for k, t in enumerate(fuertes):
        ax.axvspan(t + 0.5, t + 1.5, color=E.GRANIZO_FUERTE, zorder=0,
                   label="Año de granizo fuerte" if k == 0 else None)
    for a in ALTERNATIVAS:
        ax.plot(anios, _m(np.cumsum(res.anuales[a][r])), label=A[a]["nombre"], **_linea(a))
    ax.axhline(0, color=E.TEXTO_2, lw=0.8)
    ax.set_xticks(anios)
    ax.set_xlim(0.5, p.anios + 0.5)
    ax.set_xlabel("año")
    ax.set_ylabel("ganancia acumulada (M$)")
    ax.set_title(f"Ganancia acumulada – réplica {R['replica']}")
    ax.legend(loc="upper left", ncol=2)


# ================================================== pestaña 3 · Monte Carlo
def histogramas_van(fig, R):
    res, ind, p = R["res"], R["ind"], R["p"]
    ejes = fig.subplots(1, 3, sharex=True, sharey=True)
    todos = _m(np.concatenate([res.van[a] for a in ALTERNATIVAS]))
    bins = np.linspace(todos.min(), todos.max(), 50)
    for ax, a in zip(ejes, ALTERNATIVAS):
        ax.hist(_m(res.van[a]), bins=bins, color=A[a]["color"], edgecolor="white", linewidth=0.3,
                hatch=A[a]["hatch"])
        media, p5 = ind[a]["van_media"] / 1e6, ind[a]["van_p5"] / 1e6
        ax.axvline(media, color=E.TEXTO, lw=1.4)
        ax.axvline(p5, color=E.TEXTO, lw=1.2, ls=":")
        caja = {"boxstyle": "square,pad=0.1", "facecolor": "white", "edgecolor": "none", "alpha": 0.85}
        ax.text(media, 0.98, f" media {fmt(media, 1)}", transform=ax.get_xaxis_transform(),
                ha="left", va="top", fontsize="small", color=E.TEXTO, bbox=caja)
        ax.text(p5, 0.72, f"P5 {fmt(p5, 1)} ", transform=ax.get_xaxis_transform(),
                ha="right", va="top", fontsize="small", color=E.TEXTO, bbox=caja)
        ax.axvline(0, color=E.TEXTO_2, lw=0.6)
        ax.set_title(A[a]["nombre"])
        ax.set_xlabel(f"VAN {p.anios} años al {fmt(p.tasa_descuento * 100, 0)} % (M$)")
    ejes[0].set_ylabel(f"réplicas (de {fmt(p.replicas, 0)})")


# ===================================================== pestaña 4 · decisión
def rentabilidad_riesgo(fig, R):
    ax = fig.add_subplot(111)
    ind, p = R["ind"], R["p"]
    xs, ys = [], []
    for a in ALTERNATIVAS:
        x, y = ind[a]["van_p5"] / 1e6, ind[a]["van_media"] / 1e6
        xs.append(x)
        ys.append(y)
        ax.scatter(x, y, s=70, color=A[a]["color"], marker=A[a]["marker"], zorder=3, edgecolor="white")
        ax.annotate(f"{A[a]['corto']}\nVAN {fmt(y, 1)} · P5 {fmt(x, 1)}", (x, y), textcoords="offset points",
                    xytext=(8, -4), fontsize="small", color=E.TEXTO, va="top")
    ax.axvline(p.criterio_p5_minimo / 1e6, color=E.TEXTO_2, ls=":", lw=1)
    rx, ry = max(xs) - min(xs) or 1, max(ys) - min(ys) or 1
    ax.set_xlim(min(xs) - 0.1 * rx, max(xs) + 0.45 * rx)
    ax.set_ylim(min(ys) - 0.25 * ry, max(ys) + 0.15 * ry)
    ax.set_xlabel("P5 del VAN (M$) → menos riesgo")
    ax.set_ylabel("VAN medio (M$)")
    ax.set_title("Rentabilidad vs riesgo")
    ax.grid(axis="x")


def precio_diferencia(fig, R):
    ax = fig.add_subplot(111)
    p = R["p"]
    precios = np.asarray(R["precios"])
    d = R["barrido_precio"]["por_alternativa"]
    ref = np.asarray(d["fondo"]["van_media"])
    ax.axhline(0, label="Fondo (referencia)", color=A["fondo"]["color"],
               linestyle=A["fondo"]["linestyle"], lw=1.6)
    for a in ("sin_proteccion", "malla"):
        ax.plot(precios, _m(np.asarray(d[a]["van_media"]) - ref), label=A[a]["corto"], markevery=2, **_linea(a))
    cortes = R["cortes"]
    for clave, texto, ha in (("fondo", "malla = Fondo", "left"), ("sin_proteccion", "malla = sin protección", "right")):
        x = cortes[clave]["pesos_kg"]
        if x is not None and precios[0] <= x <= precios[-1]:
            ax.axvline(x, color=E.TEXTO, lw=0.8, ls="-.")
            borde = " " if ha == "left" else ""
            fin = "" if ha == "left" else " "
            ax.text(x, 0.03, f"{borde}${fmt(x, 0)}/kg{fin}\n{borde}{texto}{fin}", transform=ax.get_xaxis_transform(),
                    fontsize="small", color=E.TEXTO, va="bottom", ha=ha)
    ax.axvline(p.precio_uva, color=E.TEXTO_2, ls=":", lw=1)
    ax.set_xlabel("precio de la uva ($/kg)")
    ax.set_ylabel("Δ VAN vs Fondo (M$)")
    ax.set_title("Precio vs Fondo")
    fig.legend(loc="outside lower center", ncol=2, fontsize="small", columnspacing=1.0, handlelength=1.8)


def _banda_dacc(ax, R, etiqueta=True):
    s = R["severidad"]
    f = np.asarray(s["factores"])
    paso = R["p"].sens_sev_paso
    ok = s["dentro_dacc"]
    if ok.any():
        ax.axvspan(f[ok].min() - paso / 2, f[ok].max() + paso / 2, color=E.BANDA_DACC, zorder=0,
                   label="Rango DACC" if etiqueta else None)


def _linea_cruce(ax, R, etiqueta=True):
    c = R["cruce_sev"]
    if c["estimado"] is None:
        return
    if c["inferior"] is not None and c["superior"] is not None:
        ax.axvspan(c["inferior"], c["superior"], color="#D1D5DB", zorder=1)
    ax.axvline(c["estimado"], color=E.TEXTO, lw=1, ls="-.",
               label=f"Corte ×{fmt(c['estimado'], 3)}" if etiqueta else None)


def severidad(fig, R):
    s, p = R["severidad"], R["p"]
    f = np.asarray(s["factores"])
    ax1, ax2 = fig.subplots(2, 1, sharex=True, height_ratios=[3, 2])
    for ax in (ax1, ax2):
        _banda_dacc(ax, R, etiqueta=ax is ax1)
        _linea_cruce(ax, R, etiqueta=ax is ax1)
        ax.axvline(p.severidad, color=E.TEXTO_2, ls=":", lw=1)
    ax1.plot(f, s["perdida_media"] * 100, color=E.TEXTO, marker="o", label="Pérdida media %")
    ax1.plot(f, s["prob_paga"] * 100, color=E.TEXTO_2, ls="--", marker="s",
             label=f"P(daño {SIMBOLO[p.fca_condicion]} {fmt(p.fca_umbral * 100, 0)} %)")
    ax1.set_ylabel("%")
    ax1.set_title("Severidad del daño")
    fig.legend(loc="outside lower center", ncol=2, fontsize="small")
    ax2.plot(f, s["pagos_sobre_aportes"], color=E.TEXTO, marker="^")
    ax2.axhline(1, color=E.TEXTO_2, ls=":", lw=1)
    ax2.set_ylabel("pagos/aportes")
    ax2.set_xlabel("factor de severidad del daño")


def _mapa(ax, matriz, xs, ys, dx, dy, limite=None):
    """Mapa categórico de la mejor alternativa: color + rayado por alternativa."""
    cmap = ListedColormap([E.NINGUNA] + [A[a]["color"] for a in ALTERNATIVAS])
    ax.imshow(np.asarray(matriz) + 1, cmap=cmap, vmin=0, vmax=3, aspect="auto", origin="lower",
              interpolation="nearest",
              extent=(xs[0] - dx / 2, xs[-1] + dx / 2, ys[0] - dy / 2, ys[-1] + dy / 2))
    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            v = matriz[i][j]
            patron = A[ALTERNATIVAS[v]]["hatch"] if v != NINGUNA else ""
            if limite is not None and limite[i][j]:
                patron = E.HATCH_LIMITE
            if patron:
                ax.add_patch(Rectangle((x - dx / 2, y - dy / 2), dx, dy, fill=False, hatch=patron,
                                       lw=0, edgecolor="white" if patron != E.HATCH_LIMITE else E.TEXTO))
    ax.grid(False)


def _leyenda_mapa(fig, extra=()):
    h = [Patch(facecolor=A[a]["color"], hatch=A[a]["hatch"], edgecolor="white", label=A[a]["corto"])
         for a in ALTERNATIVAS]
    h.append(Patch(facecolor=E.NINGUNA, edgecolor=E.BORDE, label="Ninguna"))
    fig.legend(handles=h + list(extra), loc="outside lower center", ncol=3, fontsize="small",
               columnspacing=1.0, handlelength=1.5)


def _atenuar_fuera_dacc(ax, R, x0, x1):
    s = R["severidad"]
    f = np.asarray(s["factores"])
    paso = R["p"].sens_sev_paso
    for k, ok in enumerate(s["dentro_dacc"]):
        if not ok:
            ax.add_patch(Rectangle((x0, f[k] - paso / 2), x1 - x0, paso, facecolor="white",
                                   alpha=0.55, lw=0, zorder=2))


def mapa_precio_severidad(fig, R):
    ax = fig.add_subplot(111)
    s, p = R["severidad"], R["p"]
    xs, ys = np.asarray(R["precios"]), np.asarray(s["factores"])
    dx, dy = p.sens_precio_paso, p.sens_sev_paso
    _mapa(ax, s["mapa_precio"], xs, ys, dx, dy)
    _atenuar_fuera_dacc(ax, R, xs[0] - dx / 2, xs[-1] + dx / 2)
    ax.plot(p.precio_uva, p.severidad, marker="*", ms=13, color="white", mec=E.TEXTO, mew=1, zorder=5)
    ax.set_xlabel("precio de la uva ($/kg)")
    ax.set_ylabel("severidad")
    ax.set_title("Mejor: precio × severidad")
    _leyenda_mapa(fig, [Patch(facecolor="white", alpha=0.55, edgecolor=E.BORDE, label="Fuera de DACC"),
                        Line2D([], [], marker="*", ls="", ms=10, color="white", mec=E.TEXTO, label="Caso base")])


def mapa_hectareas_severidad(fig, R):
    ax = fig.add_subplot(111)
    s, p = R["severidad"], R["p"]
    xs, ys = np.asarray(R["hectareas"]), np.asarray(s["factores"])
    dy = p.sens_sev_paso
    _mapa(ax, s["mapa_ha"], xs, ys, 1, dy, limite=s["limite_ha"])
    ax.axvline(p.fca_max_hectareas + 0.5, ymin=0, ymax=0.86, color=E.TEXTO, lw=1.2)
    ax.text(p.fca_max_hectareas + 0.5, 0.89, f"límite del Fondo ({fmt(p.fca_max_hectareas, 0)} ha)",
            transform=ax.get_xaxis_transform(), fontsize="small", color=E.TEXTO, va="bottom", ha="center",
            zorder=6, bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": E.BORDE, "lw": 0.6})
    ax.plot(p.hectareas, p.severidad, marker="*", ms=13, color="white", mec=E.TEXTO, mew=1, zorder=5)
    ax.set_xlabel("hectáreas" + (f" (costo fijo ${fmt(p.costo_fijo_finca / 1e6, 2)} M)" if p.costo_fijo_finca else ""))
    ax.set_ylabel("severidad")
    ax.set_title("Mejor: hectáreas × severidad")
    _leyenda_mapa(fig, [Patch(facecolor="white", hatch=E.HATCH_LIMITE, edgecolor=E.TEXTO,
                              label="Caso límite")])


def persistencia(fig, R):
    ax = fig.add_subplot(111)
    pers = R["persistencia"]
    x = np.arange(len(ALTERNATIVAS))
    for k, (nombre, desp) in enumerate((("markov", -0.2), ("independiente", 0.2))):
        ii = pers[nombre]["indicadores"]
        for j, a in enumerate(ALTERNATIVAS):
            ax.bar(x[j] + desp, ii[a]["van_media"] / 1e6, 0.38, color=A[a]["color"],
                   alpha=1 if k == 0 else 0.45, hatch="" if k == 0 else "//", edgecolor="white")
            ax.plot(x[j] + desp, ii[a]["van_p5"] / 1e6, marker="v" if k == 0 else "^", color=E.TEXTO, ms=6)
    ax.set_xticks(x, [A[a]["corto"] for a in ALTERNATIVAS])
    ax.set_ylabel("VAN (M$)")
    ax.set_title("Persistencia del clima")
    fig.legend(handles=[Patch(facecolor=E.TEXTO_2, label="Markov real – media"),
                       Patch(facecolor=E.TEXTO_2, alpha=0.45, hatch="//", edgecolor="white",
                             label="Independientes – media"),
                       Line2D([], [], marker="v", ls="", color=E.TEXTO, label="P5 Markov"),
                       Line2D([], [], marker="^", ls="", color=E.TEXTO, label="P5 indep.")],
              loc="outside lower center", ncol=2, fontsize="small")


# ==================================================== pestaña 5 · precisión
def convergencia(fig, R):
    conv, p = R["convergencia"], R["p"]
    ejes = fig.subplots(1, 3)
    n = np.asarray(conv["tamanios"])
    for ax, a in zip(ejes, ALTERNATIVAS):
        m, s = _m(conv[a]["media"]), _m(conv[a]["semiancho"])
        ax.fill_between(n, m - s, m + s, color=A[a]["color"], alpha=0.18, lw=0)
        ax.plot(n, m, **_linea(a))
        ax.axhline(m[-1], color=E.TEXTO_2, ls=":", lw=0.8)
        ax.axvline(p.replicas, color=E.TEXTO_2, ls="--", lw=0.8)
        ax.set_xscale("log")
        ax.set_xticks([100, 1000, 10_000])
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: {100: "100", 1000: "1 mil", 10_000: "10 mil"}.get(int(v), "")))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_title(A[a]["corto"])
        ax.set_xlabel("réplicas")
    ejes[0].set_ylabel("VAN medio ± IC 95 % (M$)")


def corte_severidad(fig, R):
    ax = fig.add_subplot(111)
    filas = R["filas_corte_sev"]
    x = np.array([f["factor"] for f in filas])
    med = _m([f["media"] for f in filas])
    semi = _m([f["semiancho"] for f in filas])
    ax.fill_between(x, med - semi, med + semi, color="#D1D5DB", lw=0, label="IC 95 %")
    ax.plot(x, med, color=E.TEXTO, marker="o", label="VAN Fondo − VAN Sin")
    ax.axhline(0, color=E.TEXTO_2, lw=0.8)
    c = R["cruce_sev"]
    if c["estimado"] is not None:
        ax.axvline(c["estimado"], color=E.TEXTO, ls="-.", lw=1)
        ic = (f"\n IC ×{fmt(c['inferior'], 3)}–×{fmt(c['superior'], 3)}"
              if c["inferior"] is not None and c["superior"] is not None else "\n IC fuera del rango")
        ax.text(c["estimado"], 0.97, f" ×{fmt(c['estimado'], 3)}{ic}",
                transform=ax.get_xaxis_transform(), fontsize="small", va="top", color=E.TEXTO)
    ax.set_xlabel("factor de severidad")
    ax.set_ylabel("diferencia de VAN (M$)")
    ax.set_title("Corte de severidad: Fondo − Sin")
    ax.legend(loc="lower right")


# =============================================================== registro
# (clave, pestaña, archivo, función, alto en cm para exportar a 16 cm de ancho)
GRAFICOS = [
    ("dias", 1, "1_dias_granizo_real_vs_simulado", dias_granizo, 8),
    ("danio_evento", 1, "1_danio_por_granizada", danio_por_granizada, 8),
    ("danio_anual", 1, "1_danio_anual_simulado", danio_anual, 8),
    ("acumulada", 2, "2_ganancia_acumulada_replica", ganancia_acumulada, 8),
    ("histogramas", 3, "3_histogramas_van", histogramas_van, 7),
    ("riesgo", 4, "4_rentabilidad_vs_riesgo", rentabilidad_riesgo, 8),
    ("precio", 4, "4_sensibilidad_precio_diferencia_fondo", precio_diferencia, 8),
    ("severidad", 4, "4_severidad_danio_y_fondo", severidad, 10),
    ("mapa_precio", 4, "4_mapa_precio_severidad", mapa_precio_severidad, 11),
    ("mapa_ha", 4, "4_mapa_hectareas_severidad", mapa_hectareas_severidad, 11),
    ("persistencia", 4, "4_persistencia_markov_vs_independientes", persistencia, 8),
    ("convergencia", 5, "5_convergencia_van", convergencia, 7),
    ("corte_sev", 5, "5_corte_severidad_fondo_sin", corte_severidad, 8),
]


def exportar(R, carpeta, ancho_cm=16, dpi=200):
    """Guarda cada gráfico como PNG (fondo blanco, ancho A4 útil). Devuelve las rutas."""
    import os
    import matplotlib
    from matplotlib.figure import Figure
    os.makedirs(carpeta, exist_ok=True)
    rutas = []
    with matplotlib.rc_context({"font.size": 8, "axes.titlesize": 9, "legend.fontsize": 7}):
        for _, _, archivo, funcion, alto_cm in GRAFICOS:
            fig = Figure(figsize=(ancho_cm / 2.54, alto_cm / 2.54), dpi=dpi, layout="constrained",
                         facecolor="white")
            funcion(fig, R)
            ruta = os.path.join(carpeta, archivo + ".png")
            fig.savefig(ruta, dpi=dpi, facecolor="white")
            rutas.append(ruta)
    return rutas
