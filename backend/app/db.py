"""Acesso ao PostGIS. Consultas sempre parametrizadas (nada de f-string em SQL)."""

from __future__ import annotations

import logging

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

log = logging.getLogger(__name__)

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE IF NOT EXISTS relatos (
    id                    BIGSERIAL PRIMARY KEY,
    descricao             TEXT CHECK (char_length(descricao) <= 500),
    local                 GEOGRAPHY(Point, 4326) NOT NULL,
    verificado_por_imagem BOOLEAN NOT NULL DEFAULT false,
    confianca             REAL,
    criado_em             TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS relatos_local_idx ON relatos USING GIST (local);
CREATE INDEX IF NOT EXISTS relatos_criado_idx ON relatos (criado_em DESC);
"""

# Consultas fixas (sem concatenação); valores sempre passados como parâmetros (%s).
SQL_LISTAR = """
SELECT id, descricao, ST_Y(local::geometry) AS lat, ST_X(local::geometry) AS lon,
       verificado_por_imagem, confianca, criado_em
FROM relatos
ORDER BY criado_em DESC
LIMIT %s
"""

SQL_INSERIR = """
INSERT INTO relatos (descricao, local, verificado_por_imagem, confianca)
VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s, %s)
RETURNING id, descricao, ST_Y(local::geometry) AS lat, ST_X(local::geometry) AS lon,
          verificado_por_imagem, confianca, criado_em
"""


class Repositorio:
    def __init__(self, dsn: str):
        self.pool = ConnectionPool(dsn, min_size=1, max_size=5, open=False, kwargs={"row_factory": dict_row})

    def abrir(self) -> None:
        self.pool.open(wait=False)
        with self.pool.connection(timeout=30) as conn:
            conn.execute(SCHEMA)
        log.info("Banco pronto")

    def fechar(self) -> None:
        self.pool.close()

    def ping(self) -> bool:
        try:
            with self.pool.connection(timeout=2) as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:  # noqa: BLE001 - health check não pode derrubar a API
            return False

    def listar(self, limite: int) -> list[dict]:
        with self.pool.connection() as conn:
            return conn.execute(SQL_LISTAR, (limite,)).fetchall()

    def criar(self, descricao: str | None, lat: float, lon: float, verificado: bool, confianca: float | None) -> dict:
        with self.pool.connection() as conn:
            return conn.execute(SQL_INSERIR, (descricao, lon, lat, verificado, confianca)).fetchone()
