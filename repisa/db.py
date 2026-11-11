"""Base de datos SQLite de Repisa: edificios, vecinos, objetos, reservas y tienda.

Todos los datos de ejemplo son sintéticos: los vecinos se identifican solo por
su número de departamento y los edificios son direcciones genéricas de Lima.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "repisa.db"

CATEGORIAS = [
    "Juegos de mesa",
    "Herramientas",
    "Camping y aire libre",
    "Cocina y fiestas",
    "Bebés y niños",
    "Deporte",
    "Tecnología",
    "Hogar y limpieza",
    "Otros",
]

ESQUEMA = """
CREATE TABLE IF NOT EXISTS edificios (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    direccion TEXT NOT NULL,
    distrito TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS vecinos (
    id INTEGER PRIMARY KEY,
    depto TEXT NOT NULL,
    edificio_id INTEGER NOT NULL REFERENCES edificios(id),
    reputacion REAL NOT NULL DEFAULT 5.0
);
CREATE TABLE IF NOT EXISTS objetos (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    categoria TEXT NOT NULL,
    descripcion TEXT,
    estado TEXT NOT NULL,
    valor_soles INTEGER NOT NULL,
    deposito_soles INTEGER NOT NULL DEFAULT 0,
    reglas TEXT,
    accesorios TEXT,            -- JSON: lista de accesorios sugeridos
    emoji TEXT DEFAULT '📦',
    dueno_id INTEGER NOT NULL REFERENCES vecinos(id),
    catalogado_por TEXT NOT NULL DEFAULT 'vecino'   -- 'ia', 'reglas' o 'vecino'
);
CREATE TABLE IF NOT EXISTS reservas (
    id INTEGER PRIMARY KEY,
    objeto_id INTEGER NOT NULL REFERENCES objetos(id),
    vecino_id INTEGER NOT NULL REFERENCES vecinos(id),
    desde TEXT NOT NULL,
    hasta TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'confirmada'
);
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    categoria TEXT NOT NULL,
    precio_soles REAL NOT NULL,
    emoji TEXT DEFAULT '🛍️'
);
"""

EDIFICIOS = [
    (1, "Residencial Los Olivos de Salaverry", "Av. Salaverry cdra. 24", "Jesús María", -12.0832, -77.0478),
    (2, "Edificio Mariscal", "Jr. Mariscal Las Heras cdra. 3", "Lince", -12.0851, -77.0352),
    (3, "Condominio Parque Habich", "Av. Habich cdra. 5", "San Miguel", -12.0772, -77.0880),
]

# (depto, edificio)
VECINOS = [
    ("101", 1), ("204", 1), ("302", 1), ("405", 1), ("502", 1),
    ("A-11", 2), ("B-23", 2), ("C-31", 2),
    ("1A", 3), ("3C", 3), ("5B", 3),
]

# nombre, categoría, descripción, estado, valor, depósito, reglas, accesorios, emoji, dueño (índice 1-based)
OBJETOS = [
    ("Catan (edición base)", "Juegos de mesa", "Completo, con expansión 5-6 jugadores.", "Bueno", 180, 30,
     "Máximo 1 semana. Contar las piezas al devolver.", ["Fundas para cartas", "Organizador de fichas"], "🎲", 1),
    ("Dixit", "Juegos de mesa", "Ideal para reuniones familiares.", "Como nuevo", 150, 20,
     "Máximo 1 semana.", ["Expansión de cartas"], "🃏", 2),
    ("Ticket to Ride", "Juegos de mesa", "Mapa de Europa.", "Bueno", 220, 30,
     "Máximo 1 semana. Revisar vagones.", ["Fundas para cartas"], "🚂", 6),
    ("Pandemic", "Juegos de mesa", "Cooperativo, 2 a 4 jugadores.", "Usado", 160, 20,
     "Máximo 10 días.", ["Fundas para cartas"], "🦠", 9),
    ("Jenga gigante", "Juegos de mesa", "Bloques de madera de 25 cm, para exteriores.", "Bueno", 140, 20,
     "Solo uso en áreas comunes.", [], "🧱", 3),
    ("Taladro percutor Bosch", "Herramientas", "Con maletín y juego de brocas.", "Bueno", 280, 50,
     "Máximo 3 días. Devolver con la batería cargada.", ["Tarugos y tornillos", "Brocas para concreto"], "🔩", 4),
    ("Escalera de aluminio 6 pasos", "Herramientas", "Soporta 120 kg.", "Bueno", 260, 40,
     "Máximo 2 días.", [], "🪜", 5),
    ("Caja de herramientas completa", "Herramientas", "Martillo, desarmadores, llaves, alicates.", "Usado", 200, 30,
     "Máximo 3 días. Revisar que esté todo.", [], "🧰", 7),
    ("Hidrolavadora Kärcher K2", "Hogar y limpieza", "Ideal para terrazas y autos.", "Bueno", 450, 80,
     "Máximo 2 días. Vaciar el agua al devolver.", ["Detergente para hidrolavadora"], "💦", 10),
    ("Carpa para 4 personas", "Camping y aire libre", "Impermeable, armado en 10 minutos.", "Bueno", 380, 60,
     "Máximo 1 semana. Devolver seca.", ["Bolsa de dormir", "Linterna frontal"], "⛺", 1),
    ("Cooler 45 litros", "Camping y aire libre", "Mantiene el frío por 2 días.", "Usado", 190, 20,
     "Máximo 5 días. Devolver limpio.", ["Gel refrigerante"], "🧊", 8),
    ("Sillas plegables (x6)", "Cocina y fiestas", "Seis sillas de plástico reforzado.", "Bueno", 240, 30,
     "Máximo 3 días.", [], "🪑", 11),
    ("Olla arrocera industrial", "Cocina y fiestas", "Para 40 porciones.", "Bueno", 320, 50,
     "Máximo 2 días. Devolver lavada.", [], "🍚", 2),
    ("Parrilla a carbón", "Cocina y fiestas", "Con tapa y termómetro.", "Usado", 350, 50,
     "Solo en azoteas y terrazas autorizadas.", ["Carbón 5 kg", "Set de utensilios para parrilla"], "🔥", 6),
    ("Mesa plegable 1.80 m", "Cocina y fiestas", "Para 8 personas.", "Bueno", 230, 30,
     "Máximo 3 días.", [], "🍽️", 9),
    ("Coche de bebé Chicco", "Bebés y niños", "Reclinable, para 0 a 3 años.", "Bueno", 650, 100,
     "Máximo 2 semanas.", [], "👶", 3),
    ("Silla de auto para bebé", "Bebés y niños", "Grupo 0+, con base Isofix.", "Como nuevo", 550, 100,
     "Máximo 1 semana.", [], "🚼", 10),
    ("Bicicleta de niño aro 16", "Bebés y niños", "Con rueditas de apoyo.", "Usado", 300, 40,
     "Máximo 1 semana.", ["Casco infantil"], "🚲", 7),
    ("Mancuernas ajustables 2-20 kg", "Deporte", "Par de mancuernas con discos.", "Bueno", 420, 60,
     "Máximo 2 semanas.", [], "🏋️", 5),
    ("Mat de yoga y bloques", "Deporte", "Mat de 6 mm y dos bloques.", "Bueno", 120, 10,
     "Máximo 1 semana. Limpiar al devolver.", [], "🧘", 8),
    ("Proyector Full HD", "Tecnología", "Con cable HDMI y ecran portátil.", "Bueno", 900, 150,
     "Máximo 3 días.", ["Parlante bluetooth"], "📽️", 4),
    ("Parlante Bluetooth JBL", "Tecnología", "Batería de 12 horas.", "Bueno", 380, 60,
     "Máximo 3 días. Volumen moderado después de las 10 p. m.", [], "🔊", 11),
    ("Máquina de coser Singer", "Hogar y limpieza", "Con pedal y accesorios básicos.", "Usado", 480, 80,
     "Máximo 1 semana.", ["Hilos de colores"], "🧵", 9),
    ("Aspiradora de agua y polvo", "Hogar y limpieza", "20 litros.", "Bueno", 340, 50,
     "Máximo 2 días. Vaciar el tanque.", [], "🌀", 2),
]

PRODUCTOS = [
    ("Fundas para cartas (100 u.)", "Juegos de mesa", 25, "🃏"),
    ("Organizador de fichas", "Juegos de mesa", 45, "🗃️"),
    ("Expansión de cartas", "Juegos de mesa", 90, "🎴"),
    ("Tarugos y tornillos (kit)", "Herramientas", 18, "🔩"),
    ("Brocas para concreto (set)", "Herramientas", 35, "🛠️"),
    ("Detergente para hidrolavadora", "Hogar y limpieza", 40, "🧴"),
    ("Bolsa de dormir", "Camping y aire libre", 120, "🛌"),
    ("Linterna frontal", "Camping y aire libre", 35, "🔦"),
    ("Gel refrigerante (x4)", "Camping y aire libre", 28, "❄️"),
    ("Carbón 5 kg", "Cocina y fiestas", 22, "⚫"),
    ("Set de utensilios para parrilla", "Cocina y fiestas", 65, "🍖"),
    ("Casco infantil", "Bebés y niños", 70, "⛑️"),
    ("Parlante bluetooth", "Tecnología", 150, "🔊"),
    ("Hilos de colores (24 u.)", "Hogar y limpieza", 30, "🧵"),
]


def conectar(path: Path | str = DB_PATH) -> sqlite3.Connection:
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        import tempfile
        path = Path(tempfile.gettempdir()) / "repisa.db"
    con = sqlite3.connect(str(path), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def inicializar(con: sqlite3.Connection, hoy: date | None = None) -> None:
    """Crea las tablas y carga los datos sintéticos si la base está vacía."""
    con.executescript(ESQUEMA)
    if con.execute("SELECT COUNT(*) FROM edificios").fetchone()[0]:
        return
    hoy = hoy or date.today()
    con.executemany("INSERT INTO edificios VALUES (?,?,?,?,?,?)", EDIFICIOS)
    con.executemany("INSERT INTO vecinos (depto, edificio_id) VALUES (?,?)", VECINOS)
    for (nombre, cat, desc, estado, valor, dep, reglas, acc, emoji, dueno) in OBJETOS:
        con.execute(
            "INSERT INTO objetos (nombre, categoria, descripcion, estado, valor_soles, deposito_soles,"
            " reglas, accesorios, emoji, dueno_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (nombre, cat, desc, estado, valor, dep, reglas, json.dumps(acc, ensure_ascii=False), emoji, dueno),
        )
    con.executemany(
        "INSERT INTO productos (nombre, categoria, precio_soles, emoji) VALUES (?,?,?,?)", PRODUCTOS
    )
    # Historial sintético de préstamos de las últimas semanas, para que el panel tenga datos.
    historial = [
        (1, 3, -20, -14), (6, 1, -18, -16), (10, 2, -15, -9), (12, 7, -12, -10),
        (21, 9, -10, -8), (2, 5, -9, -2), (9, 4, -7, -6), (16, 8, -6, 4),
        (14, 11, -4, -3), (3, 10, -3, 2), (19, 6, -2, 9), (7, 2, 1, 2),
    ]
    for objeto, vecino, d0, d1 in historial:
        con.execute(
            "INSERT INTO reservas (objeto_id, vecino_id, desde, hasta) VALUES (?,?,?,?)",
            (objeto, vecino, (hoy + timedelta(days=d0)).isoformat(), (hoy + timedelta(days=d1)).isoformat()),
        )
    con.commit()


# ---------------------------------------------------------------- consultas

def objetos(con, edificio_id: int | None = None, categoria: str | None = None, texto: str = ""):
    sql = (
        "SELECT o.*, v.depto, v.reputacion, e.nombre AS edificio, e.id AS edificio_id, e.distrito"
        " FROM objetos o JOIN vecinos v ON v.id = o.dueno_id JOIN edificios e ON e.id = v.edificio_id"
        " WHERE 1=1"
    )
    params: list = []
    if edificio_id:
        sql += " AND e.id = ?"
        params.append(edificio_id)
    if categoria:
        sql += " AND o.categoria = ?"
        params.append(categoria)
    if texto:
        sql += " AND (o.nombre LIKE ? OR o.descripcion LIKE ? OR o.categoria LIKE ?)"
        params += [f"%{texto}%"] * 3
    return [dict(r) for r in con.execute(sql + " ORDER BY o.categoria, o.nombre", params)]


def ocupado_entre(con, objeto_id: int, desde: date, hasta: date) -> bool:
    """True si el objeto tiene una reserva que se cruza con [desde, hasta]."""
    fila = con.execute(
        "SELECT 1 FROM reservas WHERE objeto_id = ? AND estado = 'confirmada'"
        " AND NOT (hasta < ? OR desde > ?) LIMIT 1",
        (objeto_id, desde.isoformat(), hasta.isoformat()),
    ).fetchone()
    return fila is not None


def disponible_hoy(con, objeto_id: int, hoy: date | None = None) -> bool:
    hoy = hoy or date.today()
    return not ocupado_entre(con, objeto_id, hoy, hoy)


def reservar(con, objeto_id: int, vecino_id: int, desde: date, hasta: date) -> tuple[bool, str]:
    if hasta < desde:
        return False, "La fecha de devolución es anterior a la de recojo."
    if (hasta - desde).days > 14:
        return False, "Los préstamos duran como máximo 14 días."
    dueno = con.execute("SELECT dueno_id FROM objetos WHERE id = ?", (objeto_id,)).fetchone()
    if dueno is None:
        return False, "El objeto no existe."
    if dueno[0] == vecino_id:
        return False, "Ese objeto ya es tuyo 🙂"
    if ocupado_entre(con, objeto_id, desde, hasta):
        return False, "Ya está reservado en esas fechas. Prueba con otras."
    con.execute(
        "INSERT INTO reservas (objeto_id, vecino_id, desde, hasta) VALUES (?,?,?,?)",
        (objeto_id, vecino_id, desde.isoformat(), hasta.isoformat()),
    )
    con.commit()
    return True, "¡Reserva confirmada!"


def reservas_de_objeto(con, objeto_id: int):
    return [dict(r) for r in con.execute(
        "SELECT r.*, v.depto FROM reservas r JOIN vecinos v ON v.id = r.vecino_id"
        " WHERE r.objeto_id = ? AND r.hasta >= date('now', '-1 day') ORDER BY r.desde",
        (objeto_id,),
    )]


def agregar_objeto(con, ficha: dict, dueno_id: int, catalogado_por: str) -> int:
    cur = con.execute(
        "INSERT INTO objetos (nombre, categoria, descripcion, estado, valor_soles, deposito_soles,"
        " reglas, accesorios, emoji, dueno_id, catalogado_por) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            ficha["nombre"], ficha["categoria"], ficha.get("descripcion", ""), ficha["estado"],
            int(ficha["valor_estimado_soles"]), int(ficha["deposito_sugerido_soles"]),
            ficha.get("reglas_prestamo", ""),
            json.dumps(ficha.get("accesorios_sugeridos", []), ensure_ascii=False),
            ficha.get("emoji", "📦"), dueno_id, catalogado_por,
        ),
    )
    con.commit()
    return cur.lastrowid


def metricas(con, edificio_id: int | None = None) -> dict:
    filtro = " AND e.id = ?" if edificio_id else ""
    p = [edificio_id] if edificio_id else []
    base = (" FROM reservas r JOIN objetos o ON o.id = r.objeto_id JOIN vecinos v ON v.id = o.dueno_id"
            " JOIN edificios e ON e.id = v.edificio_id WHERE r.estado = 'confirmada'")
    prestamos, valor = con.execute(f"SELECT COUNT(*), COALESCE(SUM(o.valor_soles),0){base}{filtro}", p).fetchone()
    n_obj = con.execute(
        "SELECT COUNT(*) FROM objetos o JOIN vecinos v ON v.id=o.dueno_id JOIN edificios e ON e.id=v.edificio_id"
        f" WHERE 1=1{filtro}", p).fetchone()[0]
    valor_inv = con.execute(
        "SELECT COALESCE(SUM(o.valor_soles),0) FROM objetos o JOIN vecinos v ON v.id=o.dueno_id"
        f" JOIN edificios e ON e.id=v.edificio_id WHERE 1=1{filtro}", p).fetchone()[0]
    por_cat = [dict(r) for r in con.execute(
        f"SELECT o.categoria, COUNT(*) AS prestamos{base}{filtro} GROUP BY o.categoria ORDER BY prestamos DESC", p)]
    return {
        "objetos": n_obj,
        "valor_inventario": valor_inv,
        "prestamos": prestamos,
        "compras_evitadas": valor,
        "por_categoria": por_cat,
    }
