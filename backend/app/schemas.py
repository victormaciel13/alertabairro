from datetime import datetime

from pydantic import BaseModel, Field


class RelatoNovo(BaseModel):
    descricao: str | None = Field(default=None, max_length=500)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class Relato(BaseModel):
    id: int
    descricao: str | None
    lat: float
    lon: float
    verificado_por_imagem: bool
    confianca: float | None
    criado_em: datetime


class Deteccao(BaseModel):
    classe: str
    confianca: float
    caixa: list[float]


class RelatoFoto(BaseModel):
    relato: Relato
    alagamento_confirmado: bool
    deteccoes: list[Deteccao]


class Saude(BaseModel):
    status: str
    banco: bool
    modelo_carregado: bool
