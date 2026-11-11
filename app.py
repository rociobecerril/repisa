"""Repisa · la biblioteca de cosas de tu edificio.

Ejecutar:  streamlit run app.py
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from repisa import db, ia

st.set_page_config(page_title="Repisa · biblioteca de cosas", page_icon="📦", layout="wide")

COLOR_CAT = {
    "Juegos de mesa": "#F6E3C6", "Herramientas": "#E4E9DD", "Camping y aire libre": "#DCE8E2",
    "Cocina y fiestas": "#F7DCD0", "Bebés y niños": "#F3E1EA", "Deporte": "#E2E4F2",
    "Tecnología": "#DFE7EF", "Hogar y limpieza": "#EDE6D8", "Otros": "#ECE8E1",
}

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=DM+Sans:wght@400;500;700&display=swap');
    :root { --tinta:#2B2118; --suave:#7A6A5B; --acento:#C2562F; --madera:#8B5E3C; --papel:#FBF7F0; --linea:#E8DFD2; }
    html, body, [class*="css"], .stMarkdown, p, label, input, textarea, button { font-family:'DM Sans', sans-serif !important; }
    h1, h2, h3, .serif { font-family:'Fraunces', Georgia, serif !important; letter-spacing:-.01em; color:var(--tinta); }
    header[data-testid="stHeader"] { background:transparent; }
    [data-testid="stToolbar"], [data-testid="stDecoration"], footer, #MainMenu { display:none !important; }
    .block-container { padding-top:1.6rem; max-width:1180px; }
    [data-testid="stSidebar"] { background:#F3ECE1; border-right:1px solid var(--linea); }

    /* portada */
    .hero { background:linear-gradient(135deg,#F7EBDD 0%,#FBF7F0 60%); border:1px solid var(--linea);
            border-radius:22px; padding:28px 32px 22px; margin-bottom:18px; position:relative; overflow:hidden; }
    .hero:after { content:""; position:absolute; left:32px; right:32px; bottom:16px; height:7px;
                  background:var(--madera); border-radius:4px; opacity:.85; box-shadow:0 6px 0 -2px #6d482d; }
    .hero h1 { font-size:2.5rem; margin:0 0 4px; line-height:1.1; }
    .hero h1 em { color:var(--acento); font-style:italic; }
    .hero p { color:var(--suave); margin:0 0 18px; font-size:1.05rem; }
    .estante { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:22px; }
    .stat { background:white; border:1px solid var(--linea); border-radius:14px; padding:10px 16px; min-width:150px; }
    .stat b { display:block; font-family:'Fraunces',serif; font-size:1.55rem; color:var(--tinta); line-height:1.1; }
    .stat span { color:var(--suave); font-size:.82rem; }

    /* pestañas tipo píldora */
    .stTabs [data-baseweb="tab-list"] { gap:6px; border-bottom:none; flex-wrap:wrap; }
    .stTabs [data-baseweb="tab"] { background:white; border:1px solid var(--linea); border-radius:999px;
                                   padding:6px 16px; height:auto; }
    .stTabs [aria-selected="true"] { background:var(--tinta) !important; border-color:var(--tinta) !important; }
    .stTabs [aria-selected="true"] p { color:white !important; }
    .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none; }

    /* tarjetas */
    [data-testid="stVerticalBlockBorderWrapper"] { background:white; border-radius:18px !important;
        border-color:var(--linea) !important; transition:box-shadow .2s, transform .2s; }
    [data-testid="stVerticalBlockBorderWrapper"]:hover { box-shadow:0 8px 24px rgba(43,33,24,.08); }
    .ficha { display:flex; gap:14px; align-items:flex-start; }
    .icono { width:64px; height:64px; min-width:64px; border-radius:16px; display:flex; align-items:center;
             justify-content:center; font-size:2rem; }
    .ficha h4 { font-family:'Fraunces',serif; font-size:1.12rem; margin:0 0 4px; color:var(--tinta); padding:0; }
    .meta { color:var(--suave); font-size:.84rem; margin-top:6px; }
    .motivo { background:#FFF4EC; border-left:3px solid var(--acento); padding:6px 10px; border-radius:6px;
              font-size:.9rem; margin-top:8px; color:var(--tinta); }
    .emoji { font-size:2rem; line-height:1; }
    .chip { display:inline-block; padding:2px 10px; border-radius:999px; font-size:.75rem; margin-right:6px; font-weight:500; }
    .libre { background:#DFF0E3; color:#1F5C33; }
    .ocupado { background:#F9E0DA; color:#8A2C17; }
    .ia { background:#EDE7FB; color:#4B3A9C; }
    .cat { background:#F3ECE1; color:var(--madera); }

    .stButton button[kind="primary"], .stFormSubmitButton button { border-radius:999px; font-weight:700; }
    .stTextInput input, .stTextArea textarea { border-radius:12px; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def conexion():
    con = db.conectar()
    db.inicializar(con)
    return con


con = conexion()
hoy = date.today()

# ------------------------------------------------------------------ barra lateral
edificios = [dict(r) for r in con.execute("SELECT * FROM edificios ORDER BY id")]
nombres_ed = {e["id"]: f"{e['nombre']} ({e['distrito']})" for e in edificios}

with st.sidebar:
    st.markdown("<h2 class='serif' style='margin-bottom:0'>📦 Repisa</h2>", unsafe_allow_html=True)
    st.caption("La biblioteca de cosas de tu edificio")
    ed_id = st.selectbox("Mi edificio", list(nombres_ed), format_func=nombres_ed.get)
    vecinos_ed = [dict(r) for r in con.execute("SELECT * FROM vecinos WHERE edificio_id=? ORDER BY depto", (ed_id,))]
    yo = st.selectbox("Soy el vecino del dpto.", vecinos_ed, format_func=lambda v: f"Dpto. {v['depto']}")
    ver_barrio = st.toggle("Ver también otros edificios del barrio", value=False)
    st.divider()
    if ia.hay_ia():
        st.success(f"IA activa · {ia.MODELO}", icon="✨")
    else:
        st.info("Modo sin IA: catalogo por reglas. Agrega ANTHROPIC_API_KEY para activar la IA.", icon="ℹ️")
    st.caption("Demo con datos sintéticos: vecinos identificados solo por departamento.")

if "carrito" not in st.session_state:
    st.session_state.carrito = []

catalogo = db.objetos(con, None if ver_barrio else ed_id)
for o in catalogo:
    o["disponible"] = db.disponible_hoy(con, o["id"], hoy)
por_id = {o["id"]: o for o in catalogo}


def tarjeta_objeto(o: dict, clave: str, motivo: str | None = None):
    chip = '<span class="chip libre">● Disponible hoy</span>' if o["disponible"] else '<span class="chip ocupado">● Reservado hoy</span>'
    ia_chip = '<span class="chip ia">✨ catalogado con IA</span>' if o.get("catalogado_por") == "ia" else ""
    fondo = COLOR_CAT.get(o["categoria"], "#ECE8E1")
    motivo_html = f'<div class="motivo">💡 {motivo}</div>' if motivo else ""
    with st.container(border=True):
        st.markdown(
            f'''<div class="ficha"><div class="icono" style="background:{fondo}">{o["emoji"]}</div>
            <div><h4>{o["nombre"]}</h4>{chip}<span class="chip cat">{o["categoria"]}</span>{ia_chip}
            <div class="meta">Dpto. {o["depto"]} · {o["edificio"]}<br>{o["estado"]} · vale ~S/ {o["valor_soles"]}
            · garantía S/ {o["deposito_soles"]}</div>{motivo_html}</div></div>''',
            unsafe_allow_html=True,
        )
        c2 = st
        with c2.expander("Reservar"):
            if o.get("reglas"):
                st.caption(f"📜 {o['reglas']}")
            ocupadas = db.reservas_de_objeto(con, o["id"])
            if ocupadas:
                st.caption("Ocupado: " + ", ".join(f"{r['desde'][5:]}→{r['hasta'][5:]}" for r in ocupadas))
            d = st.date_input("Recojo y devolución", (hoy, hoy + timedelta(days=2)), min_value=hoy, key=f"f{clave}")
            if st.button("Confirmar reserva", key=f"b{clave}", type="primary"):
                if isinstance(d, (list, tuple)) and len(d) == 2:
                    ok, msg = db.reservar(con, o["id"], yo["id"], d[0], d[1])
                    (st.success if ok else st.error)(msg)
                    if ok:
                        acc = json.loads(o.get("accesorios") or "[]")
                        if acc:
                            st.info("¿Te falta algo? En la Tienda tienes: " + ", ".join(acc), icon="🛍️")
                else:
                    st.warning("Elige las dos fechas.")


met_ed = db.metricas(con, ed_id)
libres_hoy = sum(o["disponible"] for o in catalogo)
st.markdown(
    f"""<div class="hero"><h1>Lo que tu edificio <em>ya tiene</em>.</h1>
    <p>Pide prestado en lugar de comprar. Presta lo que guardas. Reglas claras, garantía y reservas.</p>
    <div class="estante">
      <div class="stat"><b>{len(catalogo)}</b><span>cosas en la repisa</span></div>
      <div class="stat"><b>{libres_hoy}</b><span>disponibles hoy</span></div>
      <div class="stat"><b>{met_ed['prestamos']}</b><span>préstamos registrados</span></div>
      <div class="stat"><b>S/ {met_ed['compras_evitadas']:,}</b><span>en compras evitadas</span></div>
    </div></div>""",
    unsafe_allow_html=True,
)

tab_pedir, tab_prestar, tab_mapa, tab_tienda, tab_panel = st.tabs(
    ["🔎 Pedir prestado", "➕ Prestar algo", "🗺️ Mapa del barrio", "🛍️ Tienda", "📊 Panel de la junta"]
)

# ------------------------------------------------------------------ pedir prestado
with tab_pedir:
    st.subheader("¿Qué vas a hacer?")
    st.caption("Cuéntalo como se lo dirías a un vecino. La IA busca en lo que ya hay en el edificio.")
    c1, c2 = st.columns([5, 1])
    necesidad = c1.text_input(
        "Necesidad", placeholder="Ej.: el sábado hacemos un picnic con 6 amigos y queremos jugar algo",
        label_visibility="collapsed",
    )
    buscar = c2.button("Buscar ✨", use_container_width=True, type="primary")
    if buscar and necesidad.strip():
        with st.spinner("Revisando las repisas del edificio…"):
            reco, origen = ia.recomendar(necesidad, catalogo)
        st.session_state.reco = (necesidad, reco, origen)

    if "reco" in st.session_state:
        nec, reco, origen = st.session_state.reco
        st.markdown(f"**Para:** _{nec}_ · {'✨ IA' if origen == 'ia' else '⚙️ reglas'}")
        if not reco["objetos"]:
            st.warning("No encontré nada en el edificio para eso.")
        for x in reco["objetos"]:
            tarjeta_objeto(por_id[x["id"]], f"r{x['id']}", x.get("por_que"))
        if reco.get("falta"):
            st.info(f"🧩 No hay en el edificio: {reco['falta']}")
        st.divider()

    st.subheader("Todo lo que hay")
    f1, f2 = st.columns([2, 3])
    cat = f1.selectbox("Categoría", ["Todas"] + db.CATEGORIAS)
    txt = f2.text_input("Buscar por nombre", "")
    lista = [o for o in catalogo if (cat == "Todas" or o["categoria"] == cat)
             and (not txt or txt.lower() in o["nombre"].lower())]
    st.caption(f"{len(lista)} objetos · {sum(o['disponible'] for o in lista)} disponibles hoy")
    cols = st.columns(2)
    for i, o in enumerate(lista):
        with cols[i % 2]:
            tarjeta_objeto(o, f"c{o['id']}")

# ------------------------------------------------------------------ prestar algo
with tab_prestar:
    st.subheader("Pon algo en la repisa")
    st.caption("Descríbelo con tus palabras o súbele una foto. La IA arma la ficha; tú la revisas antes de publicar.")
    desc = st.text_area(
        "¿Qué quieres prestar?",
        placeholder="Ej.: tengo un Monopoly de los 90, le falta una casita verde, lo uso solo en Navidad",
        height=90,
    )
    foto = st.file_uploader("Foto (opcional)", type=["jpg", "jpeg", "png", "webp"])
    if st.button("Catalogar con IA ✨", type="primary"):
        if not (desc.strip() or foto):
            st.warning("Escribe una descripción o sube una foto.")
        else:
            with st.spinner("Armando la ficha…"):
                ficha, origen = ia.catalogar(desc, foto.getvalue() if foto else None, foto.type if foto else "image/jpeg")
            st.session_state.ficha_ia = (ficha, origen)

    if "ficha_ia" in st.session_state:
        ficha, origen = st.session_state.ficha_ia
        if origen == "reglas" and ficha.get("_error"):
            st.warning("La IA no respondió; usé el catalogador de reglas.")
        st.markdown(f"**Ficha propuesta** {'✨ por IA' if origen == 'ia' else '⚙️ por reglas'}"
                    + (f" · {ficha['_tokens']} tokens" if ficha.get("_tokens") else ""))
        with st.form("ficha"):
            c1, c2 = st.columns([1, 5])
            emoji = c1.text_input("Ícono", ficha.get("emoji", "📦"))
            nombre = c2.text_input("Nombre", ficha["nombre"])
            c3, c4 = st.columns(2)
            categoria = c3.selectbox("Categoría", db.CATEGORIAS, index=db.CATEGORIAS.index(ficha["categoria"]))
            estado = c4.selectbox("Estado", ia.ESTADOS, index=ia.ESTADOS.index(ficha["estado"]))
            c5, c6, c7 = st.columns(3)
            valor = c5.number_input("Valor (S/)", 0, 20000, int(ficha["valor_estimado_soles"]))
            deposito = c6.number_input("Garantía (S/)", 0, 20000, int(ficha["deposito_sugerido_soles"]))
            c7.metric("Riesgo", ficha.get("riesgo", "—").capitalize())
            descripcion = st.text_input("Descripción", ficha.get("descripcion", ""))
            reglas = st.text_input("Reglas de préstamo", ficha.get("reglas_prestamo", ""))
            acc = st.text_input("Accesorios para la tienda", ", ".join(ficha.get("accesorios_sugeridos", [])))
            if st.form_submit_button("Publicar en la repisa 📦", type="primary"):
                nueva = {
                    "nombre": nombre, "categoria": categoria, "descripcion": descripcion, "estado": estado,
                    "valor_estimado_soles": valor, "deposito_sugerido_soles": deposito,
                    "reglas_prestamo": reglas, "emoji": emoji,
                    "accesorios_sugeridos": [a.strip() for a in acc.split(",") if a.strip()],
                }
                db.agregar_objeto(con, nueva, yo["id"], origen)
                del st.session_state.ficha_ia
                st.success(f"¡Listo! {nombre} ya está en la repisa del dpto. {yo['depto']}.")
                st.balloons()

    mios = [o for o in db.objetos(con) if o["dueno_id"] == yo["id"]]
    if mios:
        st.divider()
        st.markdown(f"**Mis cosas en la repisa ({len(mios)})**")
        for o in mios:
            st.write(f"{o['emoji']} {o['nombre']} · {o['estado']} · garantía S/ {o['deposito_soles']}")

# ------------------------------------------------------------------ mapa
with tab_mapa:
    st.subheader("Lo que hay en el barrio")
    st.caption("Cada edificio es una repisa. El tamaño del círculo es cuántas cosas comparte.")
    todos = db.objetos(con)
    cat_m = st.selectbox("Mostrar", ["Todo"] + db.CATEGORIAS, key="cat_mapa")
    m = folium.Map(location=[-12.081, -77.058], zoom_start=13, tiles="OpenStreetMap")
    for e in edificios:
        objs = [o for o in todos if o["edificio_id"] == e["id"] and (cat_m == "Todo" or o["categoria"] == cat_m)]
        libres = sum(db.disponible_hoy(con, o["id"], hoy) for o in objs)
        html = f"<b>{e['nombre']}</b><br>{e['direccion']}, {e['distrito']}<br>{len(objs)} cosas · {libres} libres hoy<br>"
        html += "<br>".join(f"{o['emoji']} {o['nombre']}" for o in objs[:8])
        folium.CircleMarker(
            [e["lat"], e["lon"]], radius=8 + 2 * len(objs),
            color="#3d2c8d" if e["id"] == ed_id else "#2a9d8f", fill=True, fill_opacity=.55,
            popup=folium.Popup(html, max_width=260), tooltip=f"{e['nombre']}: {len(objs)} cosas",
        ).add_to(m)
    st_folium(m, height=430, use_container_width=True, returned_objects=[])

# ------------------------------------------------------------------ tienda
with tab_tienda:
    st.subheader("Tienda: lo que se gasta, se compra")
    st.caption("Lo durable se presta; los consumibles y accesorios se compran. Sugeridos según lo que reservas.")
    sugeridos = set()
    for r in con.execute(
        "SELECT o.accesorios FROM reservas r JOIN objetos o ON o.id=r.objeto_id WHERE r.vecino_id=?", (yo["id"],)
    ):
        sugeridos |= set(json.loads(r[0] or "[]"))
    productos = [dict(r) for r in con.execute("SELECT * FROM productos ORDER BY categoria")]
    productos.sort(key=lambda p: (not any(s.lower()[:12] in p["nombre"].lower() for s in sugeridos), p["categoria"]))
    cols = st.columns(3)
    for i, p in enumerate(productos):
        with cols[i % 3].container(border=True):
            es_sug = any(s.lower()[:12] in p["nombre"].lower() for s in sugeridos)
            st.markdown(f"<div class='emoji'>{p['emoji']}</div>**{p['nombre']}**" + (" · ⭐ para ti" if es_sug else ""),
                        unsafe_allow_html=True)
            st.caption(f"{p['categoria']} · S/ {p['precio_soles']:.2f}")
            if st.button("Agregar", key=f"p{p['id']}"):
                st.session_state.carrito.append(p)
    if st.session_state.carrito:
        total = sum(p["precio_soles"] for p in st.session_state.carrito)
        st.success(f"🛒 {len(st.session_state.carrito)} productos · S/ {total:.2f} · se entrega en conserjería")

# ------------------------------------------------------------------ panel
with tab_panel:
    st.subheader("Panel para la junta de propietarios y la municipalidad")
    alcance = st.radio("Ver", ["Mi edificio", "Todo el barrio"], horizontal=True)
    met = db.metricas(con, ed_id if alcance == "Mi edificio" else None)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Cosas compartidas", met["objetos"])
    k2.metric("Valor en la repisa", f"S/ {met['valor_inventario']:,}")
    k3.metric("Préstamos", met["prestamos"])
    k4.metric("Compras evitadas", f"S/ {met['compras_evitadas']:,}",
              help="Suma del valor de los objetos prestados: lo que cada vecino no tuvo que comprar.")
    if met["por_categoria"]:
        df = pd.DataFrame(met["por_categoria"]).set_index("categoria")
        st.bar_chart(df, horizontal=True, height=280)
    st.caption(
        "Cada préstamo es una compra que no se hizo: menos gasto para las familias y menos residuos para la "
        "municipalidad. Es un bien común con reglas claras (plazo, garantía y reputación)."
    )
