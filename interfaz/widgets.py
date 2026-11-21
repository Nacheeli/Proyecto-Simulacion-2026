"""Widgets de la interfaz: tarjetas, indicadores, figuras adaptables, grupos plegables, pestañas y tablas."""

import tkinter as tk
from tkinter import ttk

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from . import estilo as E


def fuente(root, tam=E.TAM_BASE, peso="normal"):
    return (E.familia_disponible(root), tam, peso)


class Tarjeta(tk.Frame):
    """Recuadro blanco plano con borde fino y título opcional."""

    def __init__(self, padre, titulo=None, padding=12, **kw):
        super().__init__(padre, bg=E.TARJETA, highlightthickness=1, highlightbackground=E.BORDE,
                         highlightcolor=E.BORDE, bd=0, **kw)
        if titulo:
            tk.Label(self, text=titulo, bg=E.TARJETA, fg=E.TEXTO, anchor="w",
                     font=fuente(self, 11, "bold")).pack(fill=tk.X, padx=padding, pady=(padding - 2, 4))
        self.cuerpo = tk.Frame(self, bg=E.TARJETA)
        self.cuerpo.pack(fill=tk.BOTH, expand=True, padx=padding, pady=(0 if titulo else padding, padding))


class TarjetaKPI(tk.Frame):
    """Indicador grande: título chico en mayúsculas, valor grande y una línea de detalle."""

    def __init__(self, padre, titulo, color=None):
        super().__init__(padre, bg=E.TARJETA, highlightthickness=1, highlightbackground=E.BORDE,
                         highlightcolor=E.BORDE, bd=0)
        arriba = tk.Frame(self, bg=E.TARJETA)
        arriba.pack(fill=tk.X, padx=14, pady=(10, 0))
        if color:
            c = tk.Canvas(arriba, width=10, height=10, bg=E.TARJETA, highlightthickness=0)
            c.create_rectangle(0, 0, 10, 10, fill=color, outline=color)
            c.pack(side=tk.LEFT, padx=(0, 6))
        self.lbl_titulo = tk.Label(arriba, text=titulo.upper(), bg=E.TARJETA, fg=E.TEXTO_2,
                                   font=fuente(self, 8, "bold"), anchor="w")
        self.lbl_titulo.pack(side=tk.LEFT, fill=tk.X)
        self.lbl_valor = tk.Label(self, text="–", bg=E.TARJETA, fg=E.TEXTO, font=fuente(self, 17, "bold"),
                                  anchor="w")
        self.lbl_valor.pack(fill=tk.X, padx=14)
        self.lbl_detalle = tk.Label(self, text="", bg=E.TARJETA, fg=E.TEXTO_2, font=fuente(self, 9),
                                    anchor="w", justify="left")
        self.lbl_detalle.pack(fill=tk.X, padx=14, pady=(0, 10))

    def poner(self, valor, detalle=""):
        self.lbl_valor.configure(text=valor)
        self.lbl_detalle.configure(text=detalle)


class FilaKPI(tk.Frame):
    def __init__(self, padre, definiciones):
        """definiciones: lista de (clave, título, color o None)."""
        super().__init__(padre, bg=E.FONDO)
        self.kpi = {}
        for k, (clave, titulo, color) in enumerate(definiciones):
            t = TarjetaKPI(self, titulo, color)
            t.grid(row=0, column=k, sticky="nsew", padx=(0 if k == 0 else 8, 0))
            self.columnconfigure(k, weight=1, uniform="kpi")
            self.kpi[clave] = t

    def poner(self, clave, valor, detalle=""):
        self.kpi[clave].poner(valor, detalle)


class FiguraTarjeta(tk.Frame):
    """Tarjeta con un gráfico de matplotlib que se ajusta al tamaño real de su recuadro.

    Escucha <Configure> con un pequeño retardo y redimensiona la figura: así el
    gráfico no queda recortado con el escalado de Windows, al cambiar de pestaña
    ni al recalcular.
    """

    RETARDO_MS = 120

    def __init__(self, padre, funcion=None):
        super().__init__(padre, bg=E.TARJETA, highlightthickness=1, highlightbackground=E.BORDE,
                         highlightcolor=E.BORDE, bd=0, width=200, height=150)
        # la tarjeta pide un tamaño chico y fijo: el gráfico ocupa el espacio que le deja la grilla
        self.pack_propagate(False)
        self.funcion = funcion
        self.figura = Figure(figsize=(4, 3), layout="constrained", facecolor=E.TARJETA)
        self.canvas = FigureCanvasTkAgg(self.figura, master=self)
        w = self.canvas.get_tk_widget()
        # tamaño pedido chico: la figura se adapta al espacio que le deja la grilla
        w.configure(bg=E.TARJETA, highlightthickness=0, takefocus=0, width=120, height=90)
        w.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self._pendiente = None
        w.bind("<Configure>", self._programar, add="+")

    def _programar(self, _evento=None):
        if self._pendiente is not None:
            self.after_cancel(self._pendiente)
        self._pendiente = self.after(self.RETARDO_MS, self.ajustar)

    def ajustar(self):
        self._pendiente = None
        w = self.canvas.get_tk_widget()
        ancho, alto = w.winfo_width(), w.winfo_height()
        if ancho < 20 or alto < 20:
            return
        dpi = self.figura.dpi
        self.figura.set_size_inches(ancho / dpi, alto / dpi, forward=False)
        self.canvas.draw_idle()

    def dibujar(self, R):
        self.figura.clear()
        if self.funcion is not None and R is not None:
            self.funcion(self.figura, R)
        self.ajustar()
        self.canvas.draw_idle()


class GrupoPlegable(tk.Frame):
    """Grupo del panel izquierdo con título bordó y flecha para plegarlo."""

    def __init__(self, padre, titulo, abierto=True):
        super().__init__(padre, bg=E.FONDO)
        self.abierto = abierto
        self.titulo = titulo
        self.cabecera = tk.Label(self, bg=E.FONDO, fg=E.ACENTO, anchor="w", cursor="hand2",
                                 font=fuente(self, 10, "bold"))
        self.cabecera.pack(fill=tk.X, pady=(10, 2))
        self.cabecera.bind("<Button-1>", lambda e: self.alternar())
        self.cuerpo = tk.Frame(self, bg=E.TARJETA, highlightthickness=1, highlightbackground=E.BORDE)
        self._refrescar()

    def _refrescar(self):
        self.cabecera.configure(text=("▾  " if self.abierto else "▸  ") + self.titulo)
        if self.abierto:
            self.cuerpo.pack(fill=tk.X)
        else:
            self.cuerpo.pack_forget()

    def alternar(self):
        self.abierto = not self.abierto
        self._refrescar()


class PanelDesplazable(tk.Frame):
    """Marco con desplazamiento vertical (rueda del mouse solo cuando el puntero está encima)."""

    def __init__(self, padre, ancho):
        super().__init__(padre, bg=E.FONDO)
        self.lienzo = tk.Canvas(self, bg=E.FONDO, highlightthickness=0, width=ancho)
        barra = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.lienzo.yview, style="Fina.Vertical.TScrollbar")
        self.interior = tk.Frame(self.lienzo, bg=E.FONDO)
        self.interior.bind("<Configure>", lambda e: self.lienzo.configure(scrollregion=self.lienzo.bbox("all")))
        self._ventana = self.lienzo.create_window((0, 0), window=self.interior, anchor="nw")
        self.lienzo.bind("<Configure>", lambda e: self.lienzo.itemconfigure(self._ventana, width=e.width))
        self.lienzo.configure(yscrollcommand=barra.set)
        self.lienzo.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        barra.pack(side=tk.RIGHT, fill=tk.Y)
        self.bind("<Enter>", lambda e: self._rueda(True))
        self.bind("<Leave>", lambda e: self._rueda(False))

    def _rueda(self, activar):
        if activar:
            self.lienzo.bind_all("<MouseWheel>", lambda e: self.lienzo.yview_scroll(int(-e.delta / 120), "units"))
            self.lienzo.bind_all("<Button-4>", lambda e: self.lienzo.yview_scroll(-1, "units"))
            self.lienzo.bind_all("<Button-5>", lambda e: self.lienzo.yview_scroll(1, "units"))
        else:
            for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                self.lienzo.unbind_all(ev)


class Pestanias(tk.Frame):
    """Pestañas planas: texto gris y subrayado bordó en la activa."""

    def __init__(self, padre, al_cambiar=None):
        super().__init__(padre, bg=E.FONDO)
        self.barra = tk.Frame(self, bg=E.FONDO)
        self.barra.pack(fill=tk.X, padx=16, pady=(8, 0))
        tk.Frame(self, bg=E.BORDE, height=1).pack(fill=tk.X, padx=16)
        self.contenedor = tk.Frame(self, bg=E.FONDO)
        self.contenedor.pack(fill=tk.BOTH, expand=True)
        self.contenedor.rowconfigure(0, weight=1)
        self.contenedor.columnconfigure(0, weight=1)
        self.paginas, self.botones = [], []
        self.activa = None
        self.al_cambiar = al_cambiar

    def agregar(self, titulo):
        k = len(self.paginas)
        caja = tk.Frame(self.barra, bg=E.FONDO)
        caja.pack(side=tk.LEFT, padx=(0, 22))
        lbl = tk.Label(caja, text=titulo, bg=E.FONDO, fg=E.TEXTO_2, cursor="hand2", font=fuente(self, 10, "bold"))
        lbl.pack(pady=(4, 6))
        linea = tk.Frame(caja, bg=E.FONDO, height=3)
        linea.pack(fill=tk.X)
        for w in (caja, lbl):
            w.bind("<Button-1>", lambda e, i=k: self.mostrar(i))
        lbl.bind("<Enter>", lambda e, i=k: self._hover(i, True))
        lbl.bind("<Leave>", lambda e, i=k: self._hover(i, False))
        pagina = tk.Frame(self.contenedor, bg=E.FONDO)
        pagina.grid(row=0, column=0, sticky="nsew")
        self.paginas.append(pagina)
        self.botones.append((lbl, linea))
        if self.activa is None:
            self.mostrar(0)
        return pagina

    def _hover(self, i, dentro):
        if i != self.activa:
            self.botones[i][0].configure(fg=E.TEXTO if dentro else E.TEXTO_2)

    def mostrar(self, i):
        self.activa = i
        for k, (lbl, linea) in enumerate(self.botones):
            lbl.configure(fg=E.ACENTO if k == i else E.TEXTO_2)
            linea.configure(bg=E.ACENTO if k == i else E.FONDO)
        self.paginas[i].tkraise()
        if self.al_cambiar:
            self.after(30, lambda: self.al_cambiar(i))


class Tabla(tk.Frame):
    """Treeview con encabezado gris claro, filas alternadas y números a la derecha."""

    def __init__(self, padre, columnas, alto=6, desplazable=False):
        """columnas: lista de (clave, título, ancho, alineación 'w' | 'e' | 'center')."""
        super().__init__(padre, bg=E.TARJETA)
        claves = [c[0] for c in columnas]
        self.tv = ttk.Treeview(self, columns=claves, show="headings", height=alto)
        for clave, titulo, ancho, alin in columnas:
            self.tv.heading(clave, text=titulo, anchor=alin if alin != "e" else "e")
            self.tv.column(clave, width=ancho, minwidth=40, anchor=alin, stretch=True)
        self.tv.tag_configure("par", background=E.FILA_ALTERNADA)
        self.tv.tag_configure("fuerte", background=E.GRANIZO_FUERTE)
        self.tv.tag_configure("total", font=fuente(self, E.TAM_BASE, "bold"))
        self.tv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        if desplazable:
            barra = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tv.yview, style="Fina.Vertical.TScrollbar")
            self.tv.configure(yscrollcommand=barra.set)
            barra.pack(side=tk.RIGHT, fill=tk.Y)

    def llenar(self, filas):
        """filas: lista de (valores, etiquetas extra)."""
        self.tv.delete(*self.tv.get_children())
        for k, (valores, extra) in enumerate(filas):
            tags = tuple(extra) or (("par",) if k % 2 else ())
            self.tv.insert("", tk.END, values=valores, tags=tags)


def boton(padre, texto, comando, primario=True):
    """Botón plano: primario en bordó con texto blanco, secundario con borde bordó."""
    if primario:
        b = tk.Button(padre, text=texto, command=comando, bg=E.ACENTO, fg="white", activebackground=E.ACENTO_OSCURO,
                      activeforeground="white", relief="flat", bd=0, cursor="hand2", font=fuente(padre, 11, "bold"),
                      pady=8, disabledforeground="#F3E8EA")
        b.bind("<Enter>", lambda e: b.configure(bg=E.ACENTO_OSCURO) if b["state"] != "disabled" else None)
        b.bind("<Leave>", lambda e: b.configure(bg=E.ACENTO if b["state"] != "disabled" else E.DESHABILITADO))
    else:
        b = tk.Button(padre, text=texto, command=comando, bg=E.TARJETA, fg=E.ACENTO, activebackground="#F7EEF0",
                      activeforeground=E.ACENTO, relief="flat", bd=0, cursor="hand2", font=fuente(padre, 10, "bold"),
                      pady=6, highlightthickness=1, highlightbackground=E.ACENTO, disabledforeground="#C9A3AA")
    return b


def habilitar(b, si, primario=True):
    b.configure(state="normal" if si else "disabled", cursor="hand2" if si else "arrow")
    if primario:
        b.configure(bg=E.ACENTO if si else E.DESHABILITADO)
