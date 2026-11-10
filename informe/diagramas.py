"""Genera los diagramas del informe tecnico con Pillow:
docs/diagramas/arquitectura.png y docs/diagramas/flujo_actualizacion.png.

Uso: python informe/diagramas.py"""

import pathlib

from PIL import Image, ImageDraw, ImageFont

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "docs" / "diagramas"

FUENTES = ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
           "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf")
FUENTES_NEGRITA = ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf")

TINTA = "#1f2937"
GRIS = "#6b7280"
COLORES = {"archivo": "#fef3c7", "proceso": "#dbeafe", "logica": "#dcfce7", "ui": "#f3e8ff", "log": "#fee2e2"}


def fuente(tamano, negrita=False):
    for ruta in (FUENTES_NEGRITA if negrita else FUENTES):
        if pathlib.Path(ruta).exists():
            return ImageFont.truetype(ruta, tamano)
    return ImageFont.load_default(size=tamano)


def caja(d, x, y, w, h, titulo, detalle, tipo):
    d.rounded_rectangle((x, y, x + w, y + h), radius=10, fill=COLORES[tipo], outline=TINTA, width=2)
    d.text((x + w / 2, y + 22), titulo, fill=TINTA, font=fuente(17, True), anchor="mm")
    for i, linea in enumerate(detalle.split("\n")):
        d.text((x + w / 2, y + 46 + i * 19), linea, fill=TINTA, font=fuente(14), anchor="mm")
    return (x, y, w, h)


def flecha(d, inicio, fin, texto="", color=TINTA, desplazar=(0, -12)):
    (x0, y0), (x1, y1) = inicio, fin
    d.line((x0, y0, x1, y1), fill=color, width=3)
    import math
    a = math.atan2(y1 - y0, x1 - x0)
    punta = [(x1, y1), (x1 - 14 * math.cos(a - 0.4), y1 - 14 * math.sin(a - 0.4)),
             (x1 - 14 * math.cos(a + 0.4), y1 - 14 * math.sin(a + 0.4))]
    d.polygon(punta, fill=color)
    if texto:
        d.text(((x0 + x1) / 2 + desplazar[0], (y0 + y1) / 2 + desplazar[1]), texto, fill=GRIS, font=fuente(13),
               anchor="mm")


def lado(c, cual):
    x, y, w, h = c
    return {"izq": (x, y + h / 2), "der": (x + w, y + h / 2), "arr": (x + w / 2, y), "aba": (x + w / 2, y + h)}[cual]


def arquitectura():
    img = Image.new("RGB", (1500, 980), "white")
    d = ImageDraw.Draw(img)
    d.text((750, 34), "Arquitectura del cluster F40: entrada, procesamiento, presentacion y persistencia",
           fill=TINTA, font=fuente(22, True), anchor="mm")

    sim = caja(d, 40, 90, 300, 95, "Proceso productor externo", "tools/simulador.py\ntools/escribir_dato.py", "proceso")
    dat = caja(d, 430, 90, 300, 95, "datos/vehiculo.conf", "clave=valor\nescritura atomica (os.replace)", "archivo")
    cfg = caja(d, 1120, 90, 330, 95, "config/cluster.ini", "rutas, intervalos, rangos\nrotacion de bitacoras", "archivo")

    lec = caja(d, 430, 260, 300, 115, "Hilo lector (productor)", "sistema/lector.py\nlee cada 100 ms y valida\nconserva el ultimo valido", "proceso")
    buz = caja(d, 820, 270, 230, 95, "Buzon", "queue.Queue(maxsize=1)\nsolo el dato mas reciente", "proceso")
    ccf = caja(d, 1120, 260, 330, 115, "Configuracion", "sistema/config.py: valida rutas\nrelativas y rangos; la usan\nmain, lector y bitacora", "logica")

    con = caja(d, 820, 450, 230, 115, "Consumidor", "hilo de la interfaz\nTk after() cada 50 ms", "ui")
    est = caja(d, 430, 450, 300, 115, "Modelo y validador", "logic/estado.py\nEstadoCluster: R01-R08\nultimo estado valido", "logica")
    rel = caja(d, 40, 460, 300, 95, "Reloj", "logic/reloj.py\nreal o simulado (pruebas)", "logica")

    pre = caja(d, 430, 650, 300, 95, "Presentacion", "ui/presentacion.py\nestado -> colores y agujas", "ui")
    tab = caja(d, 820, 640, 300, 115, "Interfaz 8-bit", "ui/tablero.py (Tkinter)\n10 elementos, solo dibuja", "ui")
    mon = caja(d, 40, 650, 300, 95, "Monitor de eventos", "sistema/monitor.py\ntestigos 9 y 10 primero", "proceso")

    bit = caja(d, 40, 830, 300, 95, "Registrador", "sistema/bitacora.py\nrotacion por tamano", "log")
    ev = caja(d, 430, 830, 300, 95, "logs/eventos.log", "INFO y WARN\nfecha nivel componente evento", "log")
    er = caja(d, 820, 830, 300, 95, "logs/errores.log", "solo ERROR\ndatos invalidos, archivos, permisos", "log")

    flecha(d, lado(sim, "der"), lado(dat, "izq"), "escribe")
    flecha(d, lado(dat, "aba"), lado(lec, "arr"), "lee completo", desplazar=(55, 0))
    flecha(d, lado(cfg, "aba"), lado(ccf, "arr"))
    flecha(d, lado(lec, "der"), lado(buz, "izq"), "publica")
    flecha(d, lado(buz, "aba"), lado(con, "arr"), "toma", desplazar=(30, 0))
    flecha(d, lado(con, "izq"), lado(est, "der"), "set_* (valida)")
    flecha(d, lado(rel, "der"), lado(est, "izq"), "tiempo")
    flecha(d, lado(est, "aba"), lado(pre, "arr"), "vista()", desplazar=(40, 0))
    flecha(d, lado(pre, "der"), lado(tab, "izq"), "dibujo")
    flecha(d, (est[0], est[1] + est[3] - 10), lado(mon, "der"), "revisar()", desplazar=(-48, -8))
    flecha(d, lado(mon, "aba"), lado(bit, "arr"), "WARN prioritario", desplazar=(70, 0))
    flecha(d, lado(bit, "der"), lado(ev, "izq"), "INFO y WARN")
    # Errores: por debajo de eventos.log para no cruzarla.
    d.line((190, 925, 190, 955, 970, 955, 970, 940), fill=TINTA, width=3)
    flecha(d, (970, 945), (970, 925))
    d.text((580, 945), "solo ERROR", fill=GRIS, font=fuente(13), anchor="mm")
    # El lector tambien registra: baja por el pasillo entre columnas.
    d.line((430, 340, 390, 340, 390, 805, 300, 805), fill=TINTA, width=3)
    flecha(d, (300, 805), (300, 830))
    d.text((396, 768), "lectura:", fill=GRIS, font=fuente(13), anchor="lm")
    d.text((396, 785), "INFO/ERROR", fill=GRIS, font=fuente(13), anchor="lm")
    DESTINO.mkdir(parents=True, exist_ok=True)
    img.save(DESTINO / "arquitectura.png")


def flujo():
    carriles = ["Simulador\n(proceso)", "vehiculo.conf\n(archivo)", "Hilo lector", "Buzon", "Interfaz\n(after 50 ms)",
                "EstadoCluster", "Monitor", "Bitacoras"]
    pasos = [
        (0, 1, "1 escribe temporal y os.replace (atomico)"),
        (2, 1, "2 cada 100 ms: stat + lectura completa"),
        (2, 7, "3 INFO valor_actualizado / ERROR dato_invalido"),
        (2, 3, "4 publica snapshot (descarta el anterior)"),
        (4, 3, "5 get_nowait() sin bloquear"),
        (4, 5, "6 set_*(): valida tipo y rango"),
        (4, 5, "7 tick(): ciclos 100/500 ms, R01-R08"),
        (4, 6, "8 revisar(estado): transiciones"),
        (6, 7, "9 WARN testigo_9_encendido (prioritario)"),
        (4, 4, "10 refrescar(): dibuja agujas y testigos"),
    ]
    ancho, separacion, y0 = 1500, 180, 150
    img = Image.new("RGB", (ancho, y0 + len(pasos) * 62 + 80), "white")
    d = ImageDraw.Draw(img)
    d.text((ancho / 2, 34), "Secuencia de una actualizacion: del archivo de datos a la pantalla y la bitacora",
           fill=TINTA, font=fuente(22, True), anchor="mm")
    xs = [110 + i * separacion for i in range(len(carriles))]
    for x, nombre in zip(xs, carriles):
        d.rounded_rectangle((x - 80, 70, x + 80, 125), radius=8, fill=COLORES["proceso"], outline=TINTA, width=2)
        for i, linea in enumerate(nombre.split("\n")):
            d.text((x, 88 + i * 18), linea, fill=TINTA, font=fuente(14, True), anchor="mm")
        d.line((x, 125, x, img.height - 30), fill="#d1d5db", width=2)
    for k, (a, b, texto) in enumerate(pasos):
        y = y0 + k * 62
        if a == b:
            d.rectangle((xs[a] - 6, y - 14, xs[a] + 6, y + 14), fill=COLORES["ui"], outline=TINTA)
            d.text((xs[a] + 16, y), texto, fill=TINTA, font=fuente(14), anchor="lm")
        else:
            flecha(d, (xs[a], y), (xs[b], y), "")
            d.text(((xs[a] + xs[b]) / 2, y - 14), texto, fill=TINTA, font=fuente(14), anchor="mm")
    img.save(DESTINO / "flujo_actualizacion.png")


def main():
    arquitectura()
    flujo()
    print("OK docs/diagramas/arquitectura.png y docs/diagramas/flujo_actualizacion.png")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
