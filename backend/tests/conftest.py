import io
from datetime import datetime, timezone

import numpy as np
import onnx
import pytest
from onnx import TensorProto, helper, numpy_helper
from PIL import Image


class RepoFalso:
    """Substitui o PostGIS nos testes."""

    def __init__(self):
        self.relatos = []

    def ping(self):
        return True

    def listar(self, limite):
        return self.relatos[:limite]

    def criar(self, descricao, lat, lon, verificado, confianca):
        r = dict(
            id=len(self.relatos) + 1, descricao=descricao, lat=lat, lon=lon,
            verificado_por_imagem=verificado, confianca=confianca,
            criado_em=datetime.now(timezone.utc),
        )
        self.relatos.insert(0, r)
        return r


def modelo_onnx_falso(path, score=0.9):
    """ONNX com a mesma saída do YOLO11 ([1, 4+nc, 8400]) e 1 caixa fixa em (320,320) 100x100."""
    saida = np.zeros((1, 5, 8400), dtype=np.float32)
    saida[0, :, 0] = [320, 320, 100, 100, score]
    saida[0, :, 1] = [322, 321, 100, 100, score - 0.05]  # sobreposta: deve sumir no NMS
    const = numpy_helper.from_array(saida, "const")
    zero = numpy_helper.from_array(np.array(0, dtype=np.float32), "zero")
    nodes = [
        helper.make_node("ReduceSum", ["images"], ["s"], keepdims=0),
        helper.make_node("Mul", ["s", "zero"], ["s0"]),
        helper.make_node("Add", ["const", "s0"], ["output0"]),
    ]
    graph = helper.make_graph(
        nodes, "yolo_falso",
        [helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 640, 640])],
        [helper.make_tensor_value_info("output0", TensorProto.FLOAT, [1, 5, 8400])],
        initializer=[const, zero],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 9
    helper.set_model_props(model, {"names": "{0: 'alagamento'}"})
    onnx.save(model, path)
    return path


def jpeg(w=1280, h=640):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (90, 120, 160)).save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture
def modelo(tmp_path):
    return modelo_onnx_falso(str(tmp_path / "modelo.onnx"))


@pytest.fixture
def client(modelo, monkeypatch):
    monkeypatch.setenv("METRICS_TOKEN", "token-de-teste")
    from app.config import get_settings

    get_settings.cache_clear()
    from fastapi.testclient import TestClient

    from app.detector import DetectorAlagamento
    from app.main import app

    app.state.repo = RepoFalso()
    app.state.detector = DetectorAlagamento(modelo)
    with TestClient(app) as c:
        yield c
    app.state.repo = None
    app.state.detector = None
    get_settings.cache_clear()
