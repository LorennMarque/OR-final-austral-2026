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


def diagrama_flujo(ax, pasos, grupos=(), retorno=None):
    """Cajas en fila unidas por flechas.

    `pasos`: lista de (título, detalle). `grupos`: (desde, hasta, texto, color) con índices de paso,
    dibujados como una llave sobre las cajas. `retorno`: (desde, hasta, texto), flecha punteada por debajo.
    """
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    ancho, alto, paso_x = 1.0, 0.78, 1.22
    ax.set_xlim(-0.04, paso_x * (len(pasos) - 1) + ancho + 0.04)
    ax.set_ylim(-0.58, 1.2)
    ax.axis("off")
    for k, (titulo, detalle) in enumerate(pasos):
        x0 = k * paso_x
        ax.add_patch(FancyBboxPatch((x0, 0), ancho, alto, boxstyle="round,pad=0,rounding_size=0.06",
                                    facecolor="white", edgecolor=LINE, linewidth=1.2))
        ax.text(x0 + ancho / 2, alto * 0.70, titulo, ha="center", va="center", fontsize=9.5,
                color=PRIMARY, fontweight="bold")
        ax.text(x0 + ancho / 2, alto * 0.33, detalle, ha="center", va="center", fontsize=8.2,
                color=MUTED, linespacing=1.35)
        if k:
            ax.add_patch(FancyArrowPatch((x0 - paso_x + ancho + 0.03, alto / 2), (x0 - 0.03, alto / 2),
                                         arrowstyle="-|>", mutation_scale=12, color=MUTED, lw=1.2))
    for desde, hasta, texto, color in grupos:
        xa, xb, y = desde * paso_x, hasta * paso_x + ancho, alto + 0.12
        ax.plot([xa, xa, xb, xb], [y - 0.06, y, y, y - 0.06], color=color, lw=1.4)
        ax.text((xa + xb) / 2, y + 0.05, texto, ha="center", va="bottom", fontsize=9, color=color)
    if retorno:
        desde, hasta, retorno = retorno
        xa, xb = desde * paso_x + ancho / 2, hasta * paso_x + ancho / 2
        ax.add_patch(FancyArrowPatch((xa, -0.03), (xb, -0.03), connectionstyle="arc3,rad=-0.07",
                                     arrowstyle="-|>", mutation_scale=12, color=MUTED, lw=1.1, ls=(0, (4, 3))))
        ax.text((xa + xb) / 2, -0.5, retorno, ha="center", va="center", fontsize=8.8, color=MUTED)


def cientifico(x, decimales=2):
    """Número en notación científica legible (7,11 × 10⁻¹⁵); el cero exacto se escribe 0."""
    if x == 0:
        return "0"
    mantisa, exponente = f"{x:.{decimales}e}".split("e")
    superindice = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
    return f"{mantisa.replace('.', ',')} × 10{str(int(exponente)).translate(superindice)}"


TEMAS = {
    "oscuro": {"fondo": "#0E0E0E", "texto": "#ECECEC", "tenue": "#9AA0A6", "separador": "#2A2A2A",
               "borde": "#3A3A3A", "acento": "#ECECEC"},
    "claro": {"fondo": "#FFFFFF", "texto": INK, "tenue": MUTED, "separador": LINE,
              "borde": LINE, "acento": PRIMARY},
}


def tabla_imagen(ruta, titulo, encabezados, filas, nota="", tema="oscuro",
                 ancho=8.6, x_valores=0.72, destacada=1, total=False):
    """Tabla como imagen PNG para presentaciones e informes, en tema "oscuro" o "claro".

    `encabezados` y cada fila son listas de textos; la primera columna se alinea a la izquierda
    y el resto a la derecha, repartidas entre `x_valores` y el borde derecho. Los encabezados
    admiten saltos de línea. La columna `destacada` va en negrita y color de acento y las
    siguientes en gris; con `destacada=None` todas las celdas van en el color principal.
    Con `total=True` la última fila y la última columna son totales y van en negrita.
    """
    import matplotlib.pyplot as plt

    c = TEMAS[tema]
    alto_fila, n = 0.42, len(filas)
    lineas = max(h.count("\n") + 1 for h in encabezados)
    alto_encabezado = 1 + 0.55 * (lineas - 1)
    alto_total = n + 1.1 + alto_encabezado + (1.0 if nota else 0)
    fig = plt.figure(figsize=(ancho, alto_fila * alto_total / 0.92), facecolor=c["fondo"])
    ax = fig.add_axes([0.04, 0.04, 0.92, 0.92])
    ax.set_facecolor(c["fondo"])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(alto_total, 0)
    columnas_x = [0.0] + [x_valores + (1 - x_valores) * k / max(len(encabezados) - 2, 1)
                          for k in range(len(encabezados) - 1)]
    alineacion = ["left"] + ["right"] * (len(encabezados) - 1)

    def color_y_peso(i, k):
        if total and (i == n - 1 or k == len(encabezados) - 1):
            return c["texto"], "bold"
        if destacada is None or k < destacada:
            return c["texto"], "normal"
        return (c["acento"], "bold") if k == destacada else (c["tenue"], "normal")

    ax.text(0, 0.35, titulo, fontsize=14, color=c["texto"], fontweight="bold", va="center")
    y = 1.0 + alto_encabezado / 2
    for x, h, al in zip(columnas_x, encabezados, alineacion):
        ax.text(x, y, h, fontsize=10.5, color=c["texto"], fontweight="bold", ha=al, va="center", linespacing=1.3)
    y += alto_encabezado / 2 - 0.5
    for i, fila in enumerate(filas):
        linea_total = total and i == n - 1
        ax.plot([0, 1], [y + 0.5, y + 0.5], color=c["tenue"] if linea_total else c["separador"],
                lw=1.3 if linea_total else 1)
        y += 1
        for k, (x, valor, al) in enumerate(zip(columnas_x, fila, alineacion)):
            color, peso = color_y_peso(i, k)
            ax.text(x, y, valor, fontsize=10.5, ha=al, va="center", color=color, fontweight=peso)
    if nota:
        ax.text(0, y + 1.0, nota, fontsize=8.5, color=c["tenue"], va="center", wrap=True)
    fig.savefig(ruta, dpi=200, facecolor=c["fondo"])
    plt.close(fig)


def indicadores_imagen(ruta, titulo, indicadores, tema="oscuro", ancho=8.6, columnas=None, nota=""):
    """Bloque PNG de indicadores en grilla, en tema "oscuro" o "claro".

    `indicadores`: lista de (encabezado, valor, detalle); el encabezado puede ser "". `columnas`
    indicadores por fila (por defecto, todos en una fila). `nota` admite saltos de línea.
    """
    import math

    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    c = TEMAS[tema]
    columnas = columnas or len(indicadores)
    n_filas = math.ceil(len(indicadores) / columnas)
    con_encabezado = any(e for e, _, _ in indicadores)
    margen, x0 = 0.12, 0.4
    alto_titulo = 0.75
    alto_celda = (0.32 if con_encabezado else 0) + 0.95
    alto_nota = 0.2 + 0.2 * (nota.count("\n") + 1) if nota else 0
    alto = margen * 2 + alto_titulo + n_filas * alto_celda + alto_nota + 0.15
    fig = plt.figure(figsize=(ancho, alto), facecolor=c["fondo"])
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(c["fondo"])
    ax.axis("off")
    ax.set_xlim(0, ancho)
    ax.set_ylim(alto, 0)
    ax.add_patch(FancyBboxPatch((margen, margen), ancho - 2 * margen, alto - 2 * margen,
                                boxstyle="round,pad=0,rounding_size=0.12",
                                facecolor=c["fondo"], edgecolor=c["borde"], lw=1.2))
    ax.text(x0, margen + 0.42, titulo, fontsize=12.5, color=c["texto"], va="center")
    paso = (ancho - 2 * x0) / columnas
    for k, (encabezado, valor, detalle) in enumerate(indicadores):
        x = x0 + (k % columnas) * paso
        y = margen + alto_titulo + (k // columnas) * alto_celda
        if con_encabezado:
            ax.text(x, y + 0.1, encabezado, fontsize=9.5, color=c["texto"], fontweight="bold", va="center")
            y += 0.32
        ax.text(x, y + 0.22, valor, fontsize=17, color=c["acento"], fontweight="bold", va="center")
        ax.text(x, y + 0.62, detalle, fontsize=9.5, color=c["tenue"], va="center")
    if nota:
        ax.text(x0, alto - margen - 0.15 - alto_nota / 2 + 0.1, nota, fontsize=8.5, color=c["tenue"],
                va="center", linespacing=1.4)
    fig.savefig(ruta, dpi=200, facecolor=c["fondo"])
    plt.close(fig)


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


def tabla_doble_entrada(filas, columnas, celda, extra_col=None, extra_fila=None, esquina=ESQUINA):
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
        f"<thead><tr>{esquina}{head}</tr></thead>"
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
