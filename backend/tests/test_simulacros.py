from app.simulacros import obtener_disponibilidad


def test_disponibilidad_c1():
    filas = obtener_disponibilidad(
        1,
        ["A1", "A2", "C1", "C2"],
        ["REAL", "IA"],
    )
    assert filas
    assert all(
        fila["disponibles"] >= fila["necesarias"]
        for fila in filas
    )
