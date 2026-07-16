from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeSettings:
    pg_bin: str = os.getenv("SEDBMS_PG_BIN", r"C:\Program Files\PostgreSQL\18\bin")
    prod_host: str = os.getenv("SEDBMS_PROD_HOST", "localhost")
    prod_port: int = int(os.getenv("SEDBMS_PROD_PORT", "5542"))
    prod_db: str = os.getenv("SEDBMS_PROD_DB", "sedbms_prod")
    prod_user: str = os.getenv("SEDBMS_PROD_USER", "postgres")
    twin_host: str = os.getenv("SEDBMS_TWIN_HOST", "localhost")
    twin_port: int = int(os.getenv("SEDBMS_TWIN_PORT", "5543"))
    api_host: str = os.getenv("SEDBMS_API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("SEDBMS_API_PORT", "8080"))
    cvs_path: str = os.getenv("SEDBMS_CVS_PATH", "sedbms_cvs.sqlite")
    policy_path: str = os.getenv("SEDBMS_POLICY_PATH", "policy.yaml")

    @property
    def prod_dsn(self) -> str:
        return f"postgresql://{self.prod_user}@{self.prod_host}:{self.prod_port}/{self.prod_db}"


def get_settings() -> RuntimeSettings:
    return RuntimeSettings()
