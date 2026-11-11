from datetime import date, timedelta

from repisa import db, ia


def _con(tmp_path):
    con = db.conectar(tmp_path / "t.db")
    db.inicializar(con, hoy=date(2026, 11, 11))
    return con


def test_seed(tmp_path):
    con = _con(tmp_path)
    assert len(db.objetos(con)) == len(db.OBJETOS)
    assert db.metricas(con)["prestamos"] > 0


def test_reserva_y_cruce(tmp_path):
    con = _con(tmp_path)
    d = date(2027, 1, 10)
    ok, _ = db.reservar(con, 2, 1, d, d + timedelta(days=2))
    assert ok
    ok, msg = db.reservar(con, 2, 3, d + timedelta(days=1), d + timedelta(days=3))
    assert not ok and "reservado" in msg
    ok, msg = db.reservar(con, 1, 1, d, d)  # objeto 1 es del vecino 1
    assert not ok


def test_catalogar_reglas():
    f = ia.catalogar_reglas("Tengo un taladro Bosch casi nuevo, me costó 300 soles")
    assert f["categoria"] == "Herramientas" and f["valor_estimado_soles"] == 300
    assert f["deposito_sugerido_soles"] == 45


def test_recomendar_reglas(tmp_path):
    con = _con(tmp_path)
    r = ia.recomendar_reglas("picnic el sábado con juegos", db.objetos(con))
    assert r["objetos"]
