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

st.set_page_config(page_title="Repisa · biblioteca de cosas", page_icon="📦", layout="wide",
                   initial_sidebar_state="expanded")

COLOR_CAT = {
    "Juegos de mesa": "#F7C6D3", "Herramientas": "#BFE3EC", "Camping y aire libre": "#CFE6A8",
    "Cocina y fiestas": "#FBE7A1", "Bebés y niños": "#F7C6D3", "Deporte": "#BFE3EC",
    "Tecnología": "#D9CFF3", "Hogar y limpieza": "#CFE6A8", "Otros": "#FBE7A1",
}

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght,SOFT@9..144,400..900,0..100&family=DM+Sans:wght@400;500;700&family=DM+Mono:wght@400;500&display=swap');
    :root { --tinta:#1D1D1B; --suave:#5F5A52; --rosa:#F7B8C9; --rosa2:#F7C6D3; --celeste:#BFE3EC;
            --verde:#CFE6A8; --amarillo:#FBE7A1; --papel:#FFFDF6; }
    html, body, p, label, input, textarea, button, .stMarkdown { font-family:'DM Sans', sans-serif !important; }
    h1, h2, h3, .serif { font-family:'Fraunces', Georgia, serif !important; font-variation-settings:"SOFT" 100;
                         font-weight:800 !important; letter-spacing:-.02em; color:var(--tinta); }
    .stApp { background-color:var(--papel);
             background-image:linear-gradient(rgba(29,29,27,.055) 1px, transparent 1px),
                              linear-gradient(90deg, rgba(29,29,27,.055) 1px, transparent 1px);
             background-size:22px 22px; }
    header[data-testid="stHeader"] { background:transparent; }
    [data-testid="stToolbarActions"], [data-testid="stMainMenu"], .stAppDeployButton, [data-testid="stDecoration"], footer, #MainMenu { display:none !important; }
    [data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] { display:flex !important; visibility:visible !important;
        background:white; border:1.5px solid var(--tinta); border-radius:999px; }
    .block-container { padding-top:1.4rem; max-width:1180px; }
    [data-testid="stSidebar"] { background:#FFF6F8; border-right:1.5px solid var(--tinta); }

    .mono { font-family:'DM Mono', monospace !important; text-transform:uppercase; letter-spacing:.06em; font-size:.72rem; }
    .etiqueta { display:inline-block; background:var(--celeste); padding:3px 8px; font-family:'DM Mono',monospace;
                text-transform:uppercase; letter-spacing:.05em; font-size:.68rem; color:var(--tinta); line-height:1.35; }

    /* portada */
    .hero { text-align:center; padding:26px 10px 8px; position:relative; }
    .hero h1 { font-size:clamp(2.6rem,6vw,4.6rem); line-height:.95; margin:10px 0 6px; text-transform:lowercase; }
    .hero h1 .resalta { background:linear-gradient(transparent 18%, var(--rosa) 18%, var(--rosa) 88%, transparent 88%);
                        padding:0 .12em; }
    .hero .sub { color:var(--suave); max-width:560px; margin:10px auto 16px; font-size:1.02rem; }
    .sticker { position:absolute; font-size:2.1rem; filter:drop-shadow(2px 2px 0 rgba(29,29,27,.15)); }
    .pill { display:inline-flex; align-items:center; gap:8px; border:1.5px solid var(--tinta); border-radius:999px;
            background:white; padding:6px 16px; font-size:.86rem; font-weight:500; color:var(--tinta); }
    .pill:before { content:""; width:9px; height:9px; border-radius:50%; background:#E8578A; }
    .cinta { overflow:hidden; white-space:nowrap; border-top:1.5px solid var(--tinta); border-bottom:1.5px solid var(--tinta);
             background:var(--verde); margin:18px -4rem 20px; padding:7px 0; }
    .cinta span { display:inline-block; padding-left:100%; animation:corre 28s linear infinite;
                  font-family:'DM Mono',monospace; text-transform:uppercase; letter-spacing:.08em; font-size:.74rem; }
    @keyframes corre { to { transform:translateX(-100%); } }
    .stats { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:0 0 22px; }
    .stat { border:1.5px solid var(--tinta); border-radius:14px; padding:12px 14px; }
    .stat b { display:block; font-family:'Fraunces',serif; font-weight:800; font-size:1.8rem; line-height:1; color:var(--tinta); }
    .stat span { font-family:'DM Mono',monospace; text-transform:uppercase; font-size:.66rem; letter-spacing:.05em; }
    @media (max-width:700px) { .stats { grid-template-columns:repeat(2,1fr); } .sticker { display:none; } }

    /* pestañas */
    .stTabs [data-baseweb="tab-list"] { gap:8px; border-bottom:none; flex-wrap:wrap; }
    [data-testid="stTab"] { background:white !important; border:1.5px solid var(--tinta) !important; border-radius:999px !important;
        padding:5px 14px !important; margin-right:8px; height:auto !important; }
    [data-testid="stTab"] p { font-family:'DM Mono',monospace !important; text-transform:uppercase; font-size:.74rem !important; letter-spacing:.04em; color:var(--tinta) !important; }
    [data-testid="stTab"][aria-selected="true"] { background:var(--rosa) !important; }
    [data-testid="stTabs"] [role="tablist"] { border-bottom:none !important; gap:8px; flex-wrap:wrap; }
    [data-testid="stTabs"] [role="tablist"] > div:not([data-testid="stTab"]) { display:none; }
    [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .ficha),
    [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .emoji) {
        background:white; border:1.5px solid var(--tinta) !important; border-radius:16px !important; box-shadow:4px 4px 0 var(--tinta); }
    .stTabs [data-baseweb="tab"] { background:white; border:1.5px solid var(--tinta); border-radius:999px; padding:5px 14px; height:auto; }
    .stTabs [data-baseweb="tab"] p { font-family:'DM Mono',monospace !important; text-transform:uppercase; font-size:.74rem; letter-spacing:.04em; }
    .stTabs [aria-selected="true"] { background:var(--rosa) !important; }
    .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none; }

    /* tarjetas */
    [data-testid="stVerticalBlockBorderWrapper"] { background:white; border:1.5px solid var(--tinta) !important;
        border-radius:16px !important; box-shadow:4px 4px 0 var(--tinta); }
    .ficha { display:flex; gap:14px; align-items:flex-start; }
    .icono { width:64px; height:64px; min-width:64px; border-radius:14px; border:1.5px solid var(--tinta);
             display:flex; align-items:center; justify-content:center; font-size:2rem; }
    .ficha h4 { font-family:'Fraunces',serif; font-weight:800; font-size:1.18rem; margin:0 0 5px; color:var(--tinta); padding:0; }
    .meta { color:var(--suave); font-size:.84rem; margin-top:6px; }
    .motivo { background:var(--amarillo); border:1.5px solid var(--tinta); padding:6px 10px; border-radius:10px;
              font-size:.88rem; margin-top:8px; color:var(--tinta); display:inline-block; }
    .emoji { font-size:2rem; line-height:1; }
    .chip { display:inline-block; padding:2px 9px; border-radius:999px; font-family:'DM Mono',monospace; text-transform:uppercase;
            font-size:.64rem; letter-spacing:.04em; margin:0 6px 3px 0; border:1.2px solid var(--tinta); }
    .libre { background:var(--verde); } .ocupado { background:var(--rosa); } .ia { background:#D9CFF3; } .cat { background:white; }

    .stButton button, .stFormSubmitButton button { border-radius:999px !important; border:1.5px solid var(--tinta) !important;
        font-weight:600; color:var(--tinta) !important; background:white !important; }
    .stButton button[kind="primary"], .stFormSubmitButton button { background:var(--rosa) !important; }
    .stButton button:hover { box-shadow:2px 2px 0 var(--tinta); }
    .stTextInput input, .stTextArea textarea { border-radius:12px; }
    [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div { border:1.5px solid var(--tinta) !important; border-radius:12px !important; background:white !important; }
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
        st.success(f"IA activa · {ia.nombre_modelo()}", icon="✨")
    else:
        st.info("Modo sin IA: catálogo por reglas. Agrega GEMINI_API_KEY (o ANTHROPIC_API_KEY) en Secrets para activar la IA.", icon="ℹ️")
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
    f"""<div class="hero">
    <span class="sticker" style="left:6%;top:30px">🎲</span><span class="sticker" style="right:8%;top:22px">⛺</span>
    <span class="sticker" style="left:12%;bottom:40px">🔩</span><span class="sticker" style="right:5%;bottom:60px">🧺</span>
    <span class="etiqueta" style="transform:rotate(-2deg)">donde los vecinos se prestan las cosas</span>
    <h1>lo que tu edificio<br><span class="resalta">ya tiene</span></h1>
    <p class="sub">Pide prestado en lugar de comprar. Presta lo que guardas. Con reservas, garantía y reglas claras.</p>
    <span class="pill">{nombres_ed[ed_id]} · Dpto. {yo['depto']}</span>
    </div>
    <div class="cinta"><span>{"pide prestado &nbsp;·&nbsp; presta lo que guardas &nbsp;·&nbsp; menos compras &nbsp;·&nbsp; más vecindad &nbsp;·&nbsp; " * 4}</span></div>
    <div class="stats">
      <div class="stat" style="background:var(--rosa2)"><b>{len(catalogo)}</b><span>cosas en la repisa</span></div>
      <div class="stat" style="background:var(--celeste)"><b>{libres_hoy}</b><span>disponibles hoy</span></div>
      <div class="stat" style="background:var(--verde)"><b>{met_ed['prestamos']}</b><span>préstamos</span></div>
      <div class="stat" style="background:var(--amarillo)"><b>S/ {met_ed['compras_evitadas']:,}</b><span>compras evitadas</span></div>
    </div>""",
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
        for x in [x for x in reco["objetos"] if por_id[x["id"]]["dueno_id"] != yo["id"]]:
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
            st.caption(f"Detalle: {ficha['_error']}")
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
            st.markdown(f"<div class='emoji'>{p['emoji']}</div><b>{p['nombre']}</b>" + (" <span class='chip ia'>⭐ para ti</span>" if es_sug else ""),
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
        st.bar_chart(df, horizontal=True, height=280, color="#E8578A")
    st.caption(
        "Cada préstamo es una compra que no se hizo: menos gasto para las familias y menos residuos para la "
        "municipalidad. Es un bien común con reglas claras (plazo, garantía y reputación)."
    )
