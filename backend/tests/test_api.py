from app.detector import DetectorAlagamento

from .conftest import jpeg, modelo_onnx_falso


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "banco": True, "modelo_carregado": True}


def test_criar_e_listar_relato(client):
    r = client.post("/relatos", json={"descricao": "Rua cheia", "lat": -23.55, "lon": -46.63})
    assert r.status_code == 201
    assert r.json()["verificado_por_imagem"] is False
    lista = client.get("/relatos").json()
    assert len(lista) == 1 and lista[0]["descricao"] == "Rua cheia"


def test_relato_coordenada_invalida(client):
    r = client.post("/relatos", json={"lat": 123, "lon": -46.63})
    assert r.status_code == 422


def test_foto_confirma_alagamento(client):
    r = client.post(
        "/relatos/foto",
        files={"foto": ("rua.jpg", jpeg(), "image/jpeg")},
        data={"lat": "-23.55", "lon": "-46.63", "descricao": "Av. alagada"},
    )
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["alagamento_confirmado"] is True
    assert corpo["relato"]["verificado_por_imagem"] is True
    assert len(corpo["deteccoes"]) == 1  # NMS removeu a caixa duplicada
    assert corpo["deteccoes"][0]["classe"] == "alagamento"


def test_foto_tipo_errado(client):
    r = client.post(
        "/relatos/foto",
        files={"foto": ("x.txt", b"ola", "text/plain")},
        data={"lat": "-23.55", "lon": "-46.63"},
    )
    assert r.status_code == 415


def test_foto_corrompida(client):
    r = client.post(
        "/relatos/foto",
        files={"foto": ("x.jpg", b"nao sou imagem", "image/jpeg")},
        data={"lat": "-23.55", "lon": "-46.63"},
    )
    assert r.status_code == 422


def test_foto_sem_modelo(client):
    client.app.state.detector = None
    r = client.post(
        "/relatos/foto",
        files={"foto": ("rua.jpg", jpeg(), "image/jpeg")},
        data={"lat": "-23.55", "lon": "-46.63"},
    )
    assert r.status_code == 503


def test_metrics_exige_token(client):
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"Authorization": "Bearer errado"}).status_code == 401
    client.get("/relatos")
    r = client.get("/metrics", headers={"Authorization": "Bearer token-de-teste"})
    assert r.status_code == 200
    assert "http_requests_total" in r.text
    assert "http_requests_inprogress" in r.text


def test_rota_de_erro_desligada_por_padrao(client):
    assert client.get("/debug/erro").status_code == 404


def test_letterbox_volta_para_coordenadas_originais(tmp_path):
    det = DetectorAlagamento(modelo_onnx_falso(str(tmp_path / "m.onnx")))
    # 1280x640 -> escala 0,5 e faixa de 160 px em cima e embaixo
    (d,) = det.detectar(jpeg(1280, 640))
    assert d.caixa == [540.0, 220.0, 740.0, 420.0]


def test_abaixo_do_limiar_nao_confirma(tmp_path):
    det = DetectorAlagamento(modelo_onnx_falso(str(tmp_path / "m.onnx"), score=0.3), conf=0.5)
    assert det.detectar(jpeg()) == []
