from app.repositorio_contenidos import comprobar_base, obtener_convocatorias, obtener_resumen_convocatoria


def test_base_y_convocatorias():
    estado = comprobar_base()
    assert estado["integridad"] == "ok"
    assert estado["convocatorias"] >= 1
    assert estado["preguntas"] >= 1

    convocatorias = obtener_convocatorias()
    assert convocatorias
    for convocatoria in convocatorias:
        resumen = obtener_resumen_convocatoria(convocatoria["id"])
        assert resumen is not None
        assert resumen["codigo"] == convocatoria["codigo"]
