import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    s3_endpoint: str
    catalog_uri: str
    access_key: str
    secret_key: str
    trino_host: str
    trino_port: int

    @classmethod
    def load(cls):
        load_dotenv()
        return cls(
            os.getenv("S3_ENDPOINT", "http://localhost:19000"),
            os.getenv("CATALOG_URI", "http://localhost:18181"),
            os.getenv("MINIO_ROOT_USER", "archtrace"),
            os.getenv("MINIO_ROOT_PASSWORD", "archtrace-local-password"),
            os.getenv("TRINO_HOST", "localhost"),
            int(os.getenv("TRINO_PORT", "18080")),
        )


def region_codes(path: Path) -> set[str]:
    codes = {row["code"] for row in yaml.safe_load(path.read_text())["regions"]}
    if not codes or any(
        not isinstance(code, str) or len(code) != 5 or not code.isascii() or not code.isdigit()
        for code in codes
    ):
        raise ValueError("Region codes must be five-digit strings")
    return codes
