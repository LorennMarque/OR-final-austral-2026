"""Estilo común de gráficos y tablas HTML de los dos notebooks."""

from __future__ import annotations

import inspect

from IPython.display import Markdown

PRIMARY = "#1D24AB"
BLUE = PRIMARY
NOMINAL = "#B7BCDC"
RED = "#C0392B"
ALERT = RED
INK = "#1F2430"
MUTED = "#5C6570"
LINE = "#D5D8E2"
CERO = "#E4E6F2"
NOTE = "#7C4A32"
GRID = "#EEF0F4"
SPINE = "#E2E4EA"


def limpiar(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(SPINE)
    ax.spines["bottom"].set_color(SPINE)
    ax.tick_params(length=0, colors=MUTED, labelsize=10)
    ax.yaxis.grid(True, color=GRID)
    ax.set_axisbelow(True)


def etiqueta(valor: float) -> str:
    """Entero sin decimales; si no, un decimal con coma."""
    return f"{valor:.0f}" if abs(valor - round(valor)) < 1e-6 else f"{valor:.1f}".replace(".", ",")


def miles(valor: float, decimales: int = 0) -> str:
    """Formato argentino: punto de miles y coma decimal."""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


# --- Tablas HTML de doble entrada ------------------------------------------------------

def td(text, color=INK, weight="500", italic=False):
    style = (
        f"border:1px solid {LINE}; padding:8px 16px; text-align:center; background:#fff;"
        f"color:{color}; font-weight:{weight};"
    )
    if italic:
        style += "font-style:italic;"
    return f"<td style='{style}'>{text}</td>"


def th(text, color, italic=True):
    return td(text, color=color, weight="700", italic=italic).replace("td", "th", 2)


ESQUINA = (
    f"<th style='position:relative; min-width:118px; height:56px; border:1px solid {LINE};"
    "background:linear-gradient(to top right,#fff calc(50% - 0.7px),#C5C8D4 calc(50% - 0.7px),"
    f"#C5C8D4 calc(50% + 0.7px),#fff calc(50% + 0.7px));'>"
    f"<span style='position:absolute; top:6px; right:8px; color:{RED}; font-style:italic;'>Hacia</span>"
    f"<span style='position:absolute; bottom:6px; left:8px; color:{BLUE}; font-style:italic;'>Desde</span>"
    "</th>"
)


def tabla_doble_entrada(filas, columnas, celda, extra_col=None, extra_fila=None):
    """`celda(fila, columna)` devuelve el texto; extras opcionales: (titulo, f(fila)) y (titulo, f(columna))."""
    head = "".join(th(c, RED) for c in columnas)
    if extra_col:
        head += th(extra_col[0], BLUE)
    body = []
    for fila in filas:
        row = th(fila, BLUE) + "".join(td(celda(fila, c)) for c in columnas)
        if extra_col:
            row += td(extra_col[1](fila), color=BLUE, weight="700")
        body.append(f"<tr>{row}</tr>")
    if extra_fila:
        row = th(extra_fila[0], RED) + "".join(td(extra_fila[1](c), color=RED, weight="700") for c in columnas)
        row += td("") if extra_col else ""
        body.append(f"<tr>{row}</tr>")
    return (
        "<table style='border-collapse:collapse; font-family:sans-serif; font-size:15px;'>"
        f"<thead><tr>{ESQUINA}{head}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
    )


# --- Formulación escrita con los datos -------------------------------------------------

def x(i, j):
    return f"<span style='color:{BLUE};font-weight:650'>x<sub>{i},{j}</sub></span>"


def s(j):
    return f"<span style='color:{BLUE};font-weight:650'>s<sub>{j}</sub></span>"


def line(body, note=""):
    aside = f"<span style='color:{NOTE};font-style:italic;margin-left:16px'>{note}</span>" if note else ""
    return f"<div style='margin:3px 0;line-height:1.55'>{body}{aside}</div>"


def block(parts):
    return (
        "<div style=\"font-family:Georgia,'Times New Roman',serif;font-size:17px;color:"
        + INK + ";padding:4px 0 8px\">"
        + "".join(parts)
        + "</div>"
    )


def mostrar_codigo(*funciones) -> Markdown:
    """Muestra en el notebook el código fuente de funciones definidas en src/."""
    cuerpo = "\n\n".join(inspect.getsource(f).rstrip() for f in funciones)
    return Markdown(f"```python\n{cuerpo}\n```")
