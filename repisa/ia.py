"""La IA de Repisa: LLM con salidas estructuradas (sesión 08 del curso).

Dos usos dentro del producto:

1. ``catalogar``: el vecino describe (o fotografía) un objeto y el modelo devuelve
   una ficha estructurada (categoría, estado, valor, depósito, reglas de
   préstamo y accesorios que se pueden vender en la tienda).
2. ``recomendar``: el vecino escribe lo que necesita ("un picnic el sábado
   para 6") y el modelo elige del catálogo real del edificio qué pedir prestado.

La salida estructurada se fuerza con *tool use*: el modelo solo puede responder
llenando un esquema JSON. Si no hay API key (o la llamada falla), un motor de
reglas por palabras clave da una respuesta aproximada, para que la app nunca se
quede sin funcionar en el demo.
"""

from __future__ import annotations

import base64
import os
import re
import unicodedata

from .db import CATEGORIAS

MODELO = os.getenv("REPISA_MODELO", "claude-haiku-5-5")
ESTADOS = ["Como nuevo", "Bueno", "Usado", "Con detalles"]

ESQUEMA_FICHA = {
    "type": "object",
    "properties": {
        "nombre": {"type": "string", "description": "Nombre corto y claro del objeto, con marca si se conoce."},
        "categoria": {"type": "string", "enum": CATEGORIAS},
        "descripcion": {"type": "string", "description": "Una frase útil para quien lo pide prestado."},
        "estado": {"type": "string", "enum": ESTADOS},
        "valor_estimado_soles": {"type": "integer", "description": "Precio aproximado de comprarlo nuevo en Lima, en soles."},
        "deposito_sugerido_soles": {"type": "integer", "description": "Garantía razonable: entre 10% y 20% del valor."},
        "reglas_prestamo": {"type": "string", "description": "Plazo máximo y cuidados al devolver, en una o dos frases."},
        "accesorios_sugeridos": {
            "type": "array", "items": {"type": "string"}, "maxItems": 3,
            "description": "Consumibles o accesorios que quien lo pide podría comprar (p. ej. fundas, brocas, carbón).",
        },
        "emoji": {"type": "string", "description": "Un solo emoji que represente el objeto."},
        "riesgo": {"type": "string", "enum": ["bajo", "medio", "alto"],
                   "description": "Riesgo de daño o pérdida al prestarlo."},
    },
    "required": ["nombre", "categoria", "descripcion", "estado", "valor_estimado_soles",
                 "deposito_sugerido_soles", "reglas_prestamo", "accesorios_sugeridos", "emoji", "riesgo"],
}

ESQUEMA_RECOMENDACION = {
    "type": "object",
    "properties": {
        "objetos": {
            "type": "array",
            "maxItems": 6,
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "id del objeto en el catálogo"},
                    "por_que": {"type": "string", "description": "Por qué sirve para lo que pide, en una frase."},
                },
                "required": ["id", "por_que"],
            },
        },
        "falta": {"type": "string",
                  "description": "Qué necesitaría y no está en el catálogo (vacío si nada)."},
    },
    "required": ["objetos", "falta"],
}


def _cliente():
    clave = os.getenv("ANTHROPIC_API_KEY")
    if not clave:
        try:
            import streamlit as st
            clave = st.secrets.get("ANTHROPIC_API_KEY")  # Streamlit Community Cloud
        except Exception:
            clave = None
    if not clave:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=clave)
    except Exception:
        return None


def hay_ia() -> bool:
    return _cliente() is not None


def _llamar(sistema: str, contenido, nombre_tool: str, esquema: dict, max_tokens: int = 800) -> dict:
    cliente = _cliente()
    resp = cliente.messages.create(
        model=MODELO,
        max_tokens=max_tokens,
        system=sistema,
        tools=[{"name": nombre_tool, "description": "Devuelve la respuesta estructurada.", "input_schema": esquema}],
        tool_choice={"type": "tool", "name": nombre_tool},
        messages=[{"role": "user", "content": contenido}],
    )
    for bloque in resp.content:
        if bloque.type == "tool_use":
            return dict(bloque.input) | {"_tokens": resp.usage.input_tokens + resp.usage.output_tokens}
    raise RuntimeError("El modelo no devolvió la ficha.")


# ---------------------------------------------------------------- catalogar

SISTEMA_FICHA = (
    "Eres el catalogador de Repisa, la biblioteca de cosas de un edificio en Lima. "
    "Un vecino quiere prestar un objeto. Llena la ficha con criterio práctico y precios realistas "
    "del mercado peruano (soles). Si el vecino menciona daños o piezas faltantes, refléjalo en el estado. "
    "No inventes marcas que el vecino no dijo ni se ven en la foto."
)


def catalogar(texto: str, imagen: bytes | None = None, media_type: str = "image/jpeg") -> tuple[dict, str]:
    """Devuelve (ficha, origen) donde origen es 'ia' o 'reglas'."""
    if _cliente() is not None:
        contenido: list = []
        if imagen:
            contenido.append({"type": "image", "source": {
                "type": "base64", "media_type": media_type, "data": base64.b64encode(imagen).decode()}})
        contenido.append({"type": "text", "text": texto or "Cataloga el objeto de la foto."})
        try:
            ficha = _llamar(SISTEMA_FICHA, contenido, "ficha_objeto", ESQUEMA_FICHA)
            return _sanear(ficha), "ia"
        except Exception as e:  # sin internet, sin saldo, etc.
            ficha = catalogar_reglas(texto)
            ficha["_error"] = str(e)[:200]
            return ficha, "reglas"
    return catalogar_reglas(texto), "reglas"


def _sanear(f: dict) -> dict:
    if f.get("categoria") not in CATEGORIAS:
        f["categoria"] = "Otros"
    if f.get("estado") not in ESTADOS:
        f["estado"] = "Bueno"
    f["valor_estimado_soles"] = max(10, int(f.get("valor_estimado_soles") or 100))
    dep = int(f.get("deposito_sugerido_soles") or 0)
    f["deposito_sugerido_soles"] = min(max(dep, 0), f["valor_estimado_soles"])
    return f


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


# palabra clave -> (categoría, valor típico, emoji, accesorios)
_DICCIONARIO = {
    "catan": ("Juegos de mesa", 180, "🎲", ["Fundas para cartas"]),
    "juego": ("Juegos de mesa", 120, "🎲", ["Fundas para cartas"]),
    "monopoly": ("Juegos de mesa", 130, "🎲", []),
    "ajedrez": ("Juegos de mesa", 80, "♟️", []),
    "rompecabezas": ("Juegos de mesa", 60, "🧩", []),
    "taladro": ("Herramientas", 280, "🔩", ["Brocas para concreto", "Tarugos y tornillos"]),
    "escalera": ("Herramientas", 260, "🪜", []),
    "martillo": ("Herramientas", 40, "🔨", []),
    "sierra": ("Herramientas", 300, "🪚", []),
    "herramienta": ("Herramientas", 150, "🧰", []),
    "carpa": ("Camping y aire libre", 380, "⛺", ["Linterna frontal"]),
    "cooler": ("Camping y aire libre", 190, "🧊", ["Gel refrigerante"]),
    "bolsa de dormir": ("Camping y aire libre", 150, "🛌", []),
    "parrilla": ("Cocina y fiestas", 350, "🔥", ["Carbón 5 kg"]),
    "silla": ("Cocina y fiestas", 60, "🪑", []),
    "mesa": ("Cocina y fiestas", 230, "🍽️", []),
    "olla": ("Cocina y fiestas", 150, "🍲", []),
    "licuadora": ("Cocina y fiestas", 250, "🥤", []),
    "coche": ("Bebés y niños", 650, "👶", []),
    "cuna": ("Bebés y niños", 500, "🛏️", []),
    "bicicleta": ("Deporte", 600, "🚲", ["Casco infantil"]),
    "pesa": ("Deporte", 200, "🏋️", []),
    "mancuerna": ("Deporte", 200, "🏋️", []),
    "proyector": ("Tecnología", 900, "📽️", ["Parlante bluetooth"]),
    "parlante": ("Tecnología", 380, "🔊", []),
    "consola": ("Tecnología", 1500, "🎮", []),
    "aspiradora": ("Hogar y limpieza", 340, "🌀", []),
    "hidrolavadora": ("Hogar y limpieza", 450, "💦", ["Detergente para hidrolavadora"]),
    "maquina de coser": ("Hogar y limpieza", 480, "🧵", ["Hilos de colores"]),
}


def catalogar_reglas(texto: str) -> dict:
    t = _norm(texto or "")
    cat, valor, emoji, acc = "Otros", 100, "📦", []
    nombre = None
    for clave, datos in _DICCIONARIO.items():
        if clave in t:
            cat, valor, emoji, acc = datos
            # nombre = palabra clave + la palabra siguiente si parece marca (empieza en mayúscula)
            palabras = (texto or "").split()
            nombre = clave.capitalize()
            for i, w in enumerate(palabras):
                if _norm(w).startswith(clave.split()[0]):
                    nombre = w.strip(",.").capitalize()
                    sig = palabras[i + 1].strip(",.") if i + 1 < len(palabras) else ""
                    if sig[:1].isupper():
                        nombre += " " + sig
                    break
            break
    m = re.search(r"(\d{2,5})\s*(soles|s/)|s/\.?\s*(\d{2,5})", t)
    if m:
        valor = int(m.group(1) or m.group(3))
    estado = "Bueno"
    if any(w in t for w in ["nuevo", "sin usar", "en caja"]):
        estado = "Como nuevo"
    if any(w in t for w in ["roto", "falta", "rayado", "detalle", "no funciona"]):
        estado = "Con detalles"
    if not nombre:
        nombre = (texto or "Objeto").strip().split(".")[0].split(",")[0][:50].capitalize()
    return {
        "nombre": nombre,
        "categoria": cat,
        "descripcion": (texto or "").strip()[:160],
        "estado": estado,
        "valor_estimado_soles": valor,
        "deposito_sugerido_soles": round(valor * 0.15),
        "reglas_prestamo": "Máximo 1 semana. Devolver limpio y completo.",
        "accesorios_sugeridos": acc,
        "emoji": emoji,
        "riesgo": "alto" if valor > 600 else "medio" if valor > 250 else "bajo",
    }


# ---------------------------------------------------------------- recomendar

SISTEMA_RECO = (
    "Eres el asistente de Repisa, la biblioteca de cosas de un edificio en Lima. "
    "El vecino cuenta qué quiere hacer. Elige SOLO objetos del catálogo que te paso (por su id) "
    "que de verdad le sirvan, priorizando los disponibles. Si algo clave no está, dilo en 'falta'."
)


def recomendar(necesidad: str, catalogo: list[dict]) -> tuple[dict, str]:
    if _cliente() is not None:
        lineas = "\n".join(
            f"id={o['id']} | {o['nombre']} | {o['categoria']} | "
            f"{'disponible' if o.get('disponible', True) else 'reservado hoy'}"
            for o in catalogo
        )
        texto = f"Catálogo del edificio:\n{lineas}\n\nLo que necesita el vecino: {necesidad}"
        try:
            r = _llamar(SISTEMA_RECO, texto, "recomendacion", ESQUEMA_RECOMENDACION, 600)
            ids = {o["id"] for o in catalogo}
            r["objetos"] = [x for x in r.get("objetos", []) if x.get("id") in ids]
            return r, "ia"
        except Exception as e:
            r = recomendar_reglas(necesidad, catalogo)
            r["_error"] = str(e)[:200]
            return r, "reglas"
    return recomendar_reglas(necesidad, catalogo), "reglas"


_TEMAS = {
    "picnic": ["Cocina y fiestas", "Camping y aire libre", "Juegos de mesa"],
    "playa": ["Camping y aire libre", "Tecnología"],
    "camping": ["Camping y aire libre"],
    "fiesta": ["Cocina y fiestas", "Tecnología"],
    "cumple": ["Cocina y fiestas", "Tecnología", "Juegos de mesa"],
    "parrilla": ["Cocina y fiestas"],
    "noche de juegos": ["Juegos de mesa"],
    "juego": ["Juegos de mesa"],
    "pelicula": ["Tecnología"],
    "cine": ["Tecnología"],
    "mudanza": ["Herramientas", "Hogar y limpieza"],
    "cuadro": ["Herramientas"],
    "colgar": ["Herramientas"],
    "limpieza": ["Hogar y limpieza"],
    "bebe": ["Bebés y niños"],
    "visita": ["Bebés y niños", "Cocina y fiestas"],
    "ejercicio": ["Deporte"],
}


def recomendar_reglas(necesidad: str, catalogo: list[dict]) -> dict:
    t = _norm(necesidad)
    cats: list[str] = []
    for clave, cs in _TEMAS.items():
        if clave in t:
            cats += [c for c in cs if c not in cats]
    elegidos = []
    for o in catalogo:
        if o["categoria"] in cats or any(p in _norm(o["nombre"]) for p in t.split() if len(p) > 3):
            elegidos.append({"id": o["id"], "por_que": f"Es de {o['categoria'].lower()}."})
    return {"objetos": elegidos[:6], "falta": "" if elegidos else "No encontré nada parecido en el edificio."}
