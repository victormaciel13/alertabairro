"""Detector de alagamento: YOLO11 exportado para ONNX, rodando com onnxruntime.

Por que ONNX e não o pacote ultralytics na API?
- A imagem Docker cai de ~2 GB (PyTorch) para ~400 MB.
- Roda bem em CPU numa instância pequena (t3.small).
- Menos dependências = menos CVEs no scan do Trivy.

Exportar no Colab (uma linha):
    from ultralytics import YOLO
    YOLO("alertabairro_v1.pt").export(format="onnx", imgsz=640)
"""

from __future__ import annotations

import ast
import io
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

log = logging.getLogger(__name__)


@dataclass
class Deteccao:
    classe: str
    confianca: float
    caixa: list[float]  # x1, y1, x2, y2 em pixels da imagem original


class DetectorAlagamento:
    def __init__(self, model_path: str, conf: float = 0.5, iou: float = 0.45):
        import onnxruntime as ort

        if not Path(model_path).is_file():
            raise FileNotFoundError(model_path)
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 2
        self.session = ort.InferenceSession(model_path, opts, providers=["CPUExecutionProvider"])
        inp = self.session.get_inputs()[0]
        self.input_name = inp.name
        # shape: [1, 3, H, W]; se dinâmico, usa 640
        h, w = inp.shape[2], inp.shape[3]
        self.imgsz = (h if isinstance(h, int) else 640, w if isinstance(w, int) else 640)
        self.conf = conf
        self.iou = iou
        self.names = self._ler_nomes()
        log.info("Modelo carregado: %s, entrada %s, classes %s", model_path, self.imgsz, self.names)

    def _ler_nomes(self) -> dict[int, str]:
        meta = self.session.get_modelmeta().custom_metadata_map
        try:
            return {int(k): str(v) for k, v in ast.literal_eval(meta.get("names", "{}")).items()}
        except (ValueError, SyntaxError):
            return {}

    # ---------- pré-processamento ----------
    def _letterbox(self, img: Image.Image) -> tuple[np.ndarray, float, tuple[float, float]]:
        th, tw = self.imgsz
        w0, h0 = img.size
        r = min(tw / w0, th / h0)
        nw, nh = round(w0 * r), round(h0 * r)
        resized = img.resize((nw, nh), Image.BILINEAR)
        canvas = Image.new("RGB", (tw, th), (114, 114, 114))
        dx, dy = (tw - nw) / 2, (th - nh) / 2
        canvas.paste(resized, (int(round(dx - 0.1)), int(round(dy - 0.1))))
        arr = np.asarray(canvas, dtype=np.float32) / 255.0
        arr = arr.transpose(2, 0, 1)[None]  # HWC -> NCHW
        return np.ascontiguousarray(arr), r, (dx, dy)

    # ---------- pós-processamento ----------
    @staticmethod
    def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thr: float) -> list[int]:
        x1, y1, x2, y2 = boxes.T
        areas = (x2 - x1).clip(0) * (y2 - y1).clip(0)
        order = scores.argsort()[::-1]
        keep: list[int] = []
        while order.size:
            i = int(order[0])
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            inter = (xx2 - xx1).clip(0) * (yy2 - yy1).clip(0)
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
            order = order[1:][iou <= iou_thr]
        return keep

    def detectar(self, dados: bytes) -> list[Deteccao]:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(dados))).convert("RGB")
        w0, h0 = img.size
        x, r, (dx, dy) = self._letterbox(img)
        out = self.session.run(None, {self.input_name: x})[0]  # [1, 4+nc, N]
        pred = out[0].T  # [N, 4+nc]
        cls_scores = pred[:, 4:]
        cls_ids = cls_scores.argmax(1)
        scores = cls_scores.max(1)
        mask = scores >= self.conf
        if not mask.any():
            return []
        pred, scores, cls_ids = pred[mask], scores[mask], cls_ids[mask]
        cx, cy, bw, bh = pred[:, 0], pred[:, 1], pred[:, 2], pred[:, 3]
        boxes = np.stack([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], axis=1)
        # desfaz o letterbox
        boxes[:, [0, 2]] = ((boxes[:, [0, 2]] - dx) / r).clip(0, w0)
        boxes[:, [1, 3]] = ((boxes[:, [1, 3]] - dy) / r).clip(0, h0)
        keep = self._nms(boxes, scores, self.iou)
        return [
            Deteccao(
                classe=self.names.get(int(cls_ids[i]), str(int(cls_ids[i]))),
                confianca=round(float(scores[i]), 4),
                caixa=[round(float(v), 1) for v in boxes[i]],
            )
            for i in keep
        ]
