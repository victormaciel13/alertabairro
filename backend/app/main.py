"""API do AlertaBairro."""

from __future__ import annotations

import io
import logging
import secrets
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, Counter, Histogram, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator

from .config import Settings, get_settings
from .schemas import Deteccao, Relato, RelatoFoto, RelatoNovo, Saude

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("alertabairro")

Image.MAX_IMAGE_PIXELS = 40_000_000  # bloqueia "decompression bomb"
TIPOS_ACEITOS = {"image/jpeg", "image/png", "image/webp"}

RELATOS_CRIADOS = Counter(
    "alertabairro_relatos_total", "Relatos criados", ["verificado_por_imagem"]
)
TEMPO_INFERENCIA = Histogram(
    "alertabairro_inferencia_segundos",
    "Tempo de inferência do YOLO",
    buckets=(0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1, 1.5, 2, 3, 5),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    if getattr(app.state, "repo", None) is None:  # testes injetam um repositório falso
        from .db import Repositorio

        app.state.repo = Repositorio(s.database_url)
        app.state.repo.abrir()
    if getattr(app.state, "detector", None) is None:
        try:
            from .detector import DetectorAlagamento

            app.state.detector = DetectorAlagamento(s.model_path, s.conf_alagamento, s.iou_nms)
        except FileNotFoundError:
            log.warning("Modelo não encontrado em %s: /relatos/foto responderá 503", s.model_path)
            app.state.detector = None
    yield
    fechar = getattr(app.state.repo, "fechar", None)
    if fechar:
        fechar()


app = FastAPI(
    title="AlertaBairro API",
    version="1.0.0",
    description="Relatos colaborativos de alagamento em São Paulo, com validação por imagem (YOLO).",
    lifespan=lifespan,
    root_path=get_settings().root_path,
)

Instrumentator(
    should_group_status_codes=True,  # status vira 2xx, 4xx, 5xx
    should_instrument_requests_inprogress=True,  # saturação: requisições em andamento
    inprogress_labels=True,
    excluded_handlers=["/metrics", "/health"],
).instrument(app)


def repo(request: Request):
    return request.app.state.repo


# ---------------------------------------------------------------- rotas
@app.get("/health", response_model=Saude, tags=["infra"])
def health(request: Request):
    return Saude(
        status="ok",
        banco=request.app.state.repo.ping(),
        modelo_carregado=request.app.state.detector is not None,
    )


@app.get("/metrics", include_in_schema=False)
def metrics(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
):
    esperado = f"Bearer {settings.metrics_token}"
    if not settings.metrics_token or not secrets.compare_digest(authorization or "", esperado):
        raise HTTPException(status_code=401, detail="não autorizado")
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


@app.get("/relatos", response_model=list[Relato], tags=["relatos"])
def listar_relatos(r=Depends(repo), limite: Annotated[int, Query(ge=1, le=500)] = 100):
    return r.listar(limite)


@app.post("/relatos", response_model=Relato, status_code=201, tags=["relatos"])
def criar_relato(novo: RelatoNovo, r=Depends(repo)):
    RELATOS_CRIADOS.labels("false").inc()
    return r.criar(novo.descricao, novo.lat, novo.lon, False, None)


@app.post("/relatos/foto", response_model=RelatoFoto, status_code=201, tags=["relatos"])
def criar_relato_com_foto(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    foto: Annotated[UploadFile, File(description="Foto JPEG, PNG ou WebP do local")],
    lat: Annotated[float, Form(ge=-90, le=90)],
    lon: Annotated[float, Form(ge=-180, le=180)],
    descricao: Annotated[str | None, Form(max_length=500)] = None,
    r=Depends(repo),
):
    detector = request.app.state.detector
    if detector is None:
        raise HTTPException(status_code=503, detail="modelo de visão indisponível")
    if foto.content_type not in TIPOS_ACEITOS:
        raise HTTPException(status_code=415, detail="envie JPEG, PNG ou WebP")

    limite = settings.max_foto_mb * 1024 * 1024
    dados = foto.file.read(limite + 1)
    if len(dados) > limite:
        raise HTTPException(status_code=413, detail=f"foto maior que {settings.max_foto_mb} MB")
    try:
        Image.open(io.BytesIO(dados)).verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(status_code=422, detail="arquivo não é uma imagem válida") from None

    inicio = time.perf_counter()
    deteccoes = detector.detectar(dados)
    TEMPO_INFERENCIA.observe(time.perf_counter() - inicio)

    confirmado = len(deteccoes) > 0
    confianca = max((d.confianca for d in deteccoes), default=None)
    RELATOS_CRIADOS.labels(str(confirmado).lower()).inc()
    # LGPD (minimização): a foto NÃO é armazenada; só o resultado da análise.
    relato = r.criar(descricao, lat, lon, confirmado, confianca)
    return RelatoFoto(
        relato=relato,
        alagamento_confirmado=confirmado,
        deteccoes=[Deteccao(**d.__dict__) for d in deteccoes],
    )


@app.get("/debug/erro", include_in_schema=False)
def erro_proposital(settings: Annotated[Settings, Depends(get_settings)]):
    """Gera 500 de propósito para disparar o alerta de taxa de erro (só se CHAOS_ENABLED=true)."""
    if not settings.chaos_enabled:
        raise HTTPException(status_code=404)
    raise HTTPException(status_code=500, detail="erro proposital para teste de alerta")
