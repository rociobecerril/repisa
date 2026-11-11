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

st.markdown(
    """
    <style>
    .tarjeta {border:1px solid rgba(128,128,128,.25); border-radius:14px; padding:14px 16px; margin-bottom:10px;}
    .emoji {font-size:2rem; line-height:1;}
    .chip {display:inline-block; padding:2px 10px; border-radius:999px; font-size:.78rem; margin-right:6px;}
    .libre {background:#d9f2e3; color:#145c32;}
    .ocupado {background:#fde2e1; color:#8a1c17;}
    .ia {background:#e7e3fb; color:#3d2c8d;}
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
    st.title("📦 Repisa")
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
    chip = '<span class="chip libre">Disponible hoy</span>' if o["disponible"] else '<span class="chip ocupado">Reservado hoy</span>'
    ia_chip = '<span class="chip ia">✨ catalogado con IA</span>' if o.get("catalogado_por") == "ia" else ""
    with st.container(border=True):
        c1, c2 = st.columns([1, 6])
        c1.markdown(f'<div class="emoji">{o["emoji"]}</div>', unsafe_allow_html=True)
        c2.markdown(f"**{o['nombre']}** · {o['categoria']}  \n{chip}{ia_chip}", unsafe_allow_html=True)
        if motivo:
            c2.markdown(f"💡 _{motivo}_")
        c2.caption(
            f"Dpto. {o['depto']} · {o['edificio']} · estado: {o['estado']} · "
            f"vale ~S/ {o['valor_soles']} · garantía S/ {o['deposito_soles']}"
        )
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
