from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração lida de variáveis de ambiente (nunca de valores fixos no código)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Banco (PostGIS). A senha vem do .env local ou do Azure Key Vault em produção.
    database_url: str = "postgresql://alertabairro@db:5432/alertabairro"

    # Modelo de visão (YOLO exportado para ONNX)
    model_path: str = "models/alertabairro_v1.onnx"
    conf_alagamento: float = 0.5  # detecção acima disso = "alagamento confirmado"
    iou_nms: float = 0.45
    max_foto_mb: int = 5

    # Token que o Prometheus usa para ler /metrics. Vazio = /metrics desligado.
    metrics_token: str = ""

    # Prefixo quando a API está atrás do proxy (Caddy serve a API em /api)
    root_path: str = ""

    # Liga a rota /debug/erro, usada só para disparar o alerta no teste de carga.
    chaos_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
