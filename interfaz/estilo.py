"""
Estilo del programa: paleta, tipografía, tema ttk y configuración de matplotlib.

ÚNICO lugar donde se definen colores. Reglas:
  - Cada alternativa tiene siempre el mismo color, tipo de línea y marcador.
  - El bordó es solo de la interfaz: nunca dentro de un gráfico.
  - Ningún dato depende solo del color (líneas, marcadores y rayados distintos),
    para que se lea impreso en blanco y negro.
  - Las marcas de "mejor" en las tablas van en el color de texto principal.
"""

# ------------------------------------------------------------------ interfaz
FONDO = "#F3F4F6"
TARJETA = "#FFFFFF"
BORDE = "#E5E7EB"
TEXTO = "#374151"
TEXTO_2 = "#6B7280"
ACENTO = "#7B2D3B"          # bordó vino: botón, pestaña activa, títulos de grupo
ACENTO_OSCURO = "#5E2230"   # hover del botón
FILA_ALTERNADA = "#FAFAFB"
DESHABILITADO = "#C9A3AA"

# --------------------------------------------------------------------- datos
REAL = "#374151"            # datos reales (CSV)
SIMULADO = "#9CA3AF"        # simulado
GRANIZO_FUERTE = "#E5E7EB"  # años de granizo fuerte y "ninguna" en los mapas
NINGUNA = "#E5E7EB"
SUPUESTO = "#B45309"        # texto de supuestos (S)
BANDA_DACC = "#FDF3D8"      # rango creíble DACC
MARCA_REAL = "#9CA3AF"      # marca (R)

ALTERNATIVAS_ESTILO = {
    "sin_proteccion": {"color": "#D55E00", "linestyle": "-", "marker": "o", "hatch": "///",
                       "nombre": "Sin protección", "corto": "Sin protección"},
    "fondo": {"color": "#0072B2", "linestyle": "--", "marker": "s", "hatch": "",
              "nombre": "Fondo Compensador", "corto": "Fondo"},
    "malla": {"color": "#009E73", "linestyle": ":", "marker": "^", "hatch": "...",
              "nombre": "Malla antigranizo", "corto": "Malla"},
}
HATCH_LIMITE = "xxx"

# ---------------------------------------------------------------- tipografía
FAMILIAS = ("Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans")
TAM_BASE = 10


def familia_disponible(root=None):
    """Primera familia de FAMILIAS instalada (Segoe UI en Windows)."""
    try:
        import tkinter.font as tkfont
        instaladas = set(tkfont.families(root))
        for f in FAMILIAS:
            if f in instaladas:
                return f
    except Exception:
        pass
    return "TkDefaultFont"


def activar_dpi():
    """Modo DPI-aware en Windows (nitidez con escalado de 125–150 %)."""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def configurar_matplotlib(tam=9):
    import matplotlib
    matplotlib.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": list(FAMILIAS),
        "font.size": tam,
        "axes.titlesize": tam + 1,
        "axes.titleweight": "bold",
        "axes.titlecolor": TEXTO,
        "axes.titlelocation": "left",
        "axes.labelcolor": TEXTO_2,
        "axes.edgecolor": BORDE,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,
        "axes.facecolor": TARJETA,
        "grid.color": BORDE,
        "grid.linewidth": 0.8,
        "xtick.color": TEXTO_2,
        "ytick.color": TEXTO_2,
        "xtick.labelcolor": TEXTO_2,
        "ytick.labelcolor": TEXTO_2,
        "legend.frameon": False,
        "legend.fontsize": tam - 1,
        "figure.facecolor": TARJETA,
        "savefig.facecolor": "white",
        "hatch.color": TEXTO,
        "hatch.linewidth": 0.6,
        "lines.linewidth": 1.8,
        "lines.markersize": 4,
    })


def configurar_ttk(root):
    """Tema 'clam' personalizado: plano, bordes finos, foco bordó."""
    from tkinter import ttk
    familia = familia_disponible(root)
    root.option_add("*Font", (familia, TAM_BASE))
    est = ttk.Style(root)
    est.theme_use("clam")
    base = (familia, TAM_BASE)
    est.configure(".", background=FONDO, foreground=TEXTO, font=base, bordercolor=BORDE,
                  lightcolor=BORDE, darkcolor=BORDE, troughcolor=FONDO, focuscolor=ACENTO)
    est.configure("Tarjeta.TFrame", background=TARJETA)
    est.configure("Fondo.TFrame", background=FONDO)
    est.configure("TLabel", background=FONDO, foreground=TEXTO)
    est.configure("Tarjeta.TLabel", background=TARJETA, foreground=TEXTO)

    # Campos
    for nombre in ("TEntry", "TCombobox"):
        est.configure(nombre, fieldbackground=TARJETA, background=TARJETA, foreground=TEXTO,
                      bordercolor=BORDE, lightcolor=BORDE, darkcolor=BORDE, padding=(4, 2),
                      arrowcolor=TEXTO_2, insertcolor=TEXTO)
        est.map(nombre, bordercolor=[("focus", ACENTO)], lightcolor=[("focus", ACENTO)],
                darkcolor=[("focus", ACENTO)])
    est.map("TCombobox", fieldbackground=[("readonly", TARJETA)], foreground=[("readonly", TEXTO)],
            selectbackground=[("readonly", TARJETA)], selectforeground=[("readonly", TEXTO)])
    root.option_add("*TCombobox*Listbox.font", base)
    root.option_add("*TCombobox*Listbox.selectBackground", ACENTO)

    # Tablas
    est.configure("Treeview", background=TARJETA, fieldbackground=TARJETA, foreground=TEXTO,
                  bordercolor=BORDE, lightcolor=BORDE, darkcolor=BORDE, rowheight=22, font=base)
    est.map("Treeview", background=[("selected", "#EDE3E5")], foreground=[("selected", TEXTO)])
    est.configure("Treeview.Heading", background=FONDO, foreground=TEXTO_2, relief="flat",
                  bordercolor=BORDE, lightcolor=FONDO, darkcolor=FONDO, font=(familia, TAM_BASE - 1, "bold"),
                  padding=(6, 4))
    est.map("Treeview.Heading", background=[("active", BORDE)])

    # Barras de desplazamiento finas, sin flechas
    for orient, eje in (("Vertical", "ns"), ("Horizontal", "ew")):
        nombre = f"Fina.{orient}.TScrollbar"
        est.layout(nombre, [(f"{orient}.Scrollbar.trough", {"sticky": eje, "children": [
            (f"{orient}.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
        est.configure(nombre, troughcolor=FONDO, background="#D1D5DB", bordercolor=FONDO,
                      lightcolor="#D1D5DB", darkcolor="#D1D5DB", arrowsize=8, gripcount=0)
        est.map(nombre, background=[("active", "#9CA3AF")])
    return familia
