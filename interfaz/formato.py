"""Formato de números en castellano (coma decimal, punto de miles)."""


def fmt(x, dec=2):
    s = f"{x:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_m(x, dec=2):
    """Pesos en millones, con el signo antes del símbolo: −$ 4,40 M."""
    signo = "−" if x < 0 else ""
    return f"{signo}$ {fmt(abs(x) / 1e6, dec)} M"


def fmt_pct(x, dec=1):
    """x es una fracción (0,131 → 13,1 %)."""
    return f"{fmt(x * 100, dec)} %"


def leer_numero(texto):
    s = texto.strip().replace("$", "").replace(" ", "").replace("−", "-")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    return float(s)
