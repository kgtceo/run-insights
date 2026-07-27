"""Runtime configuration (RI_ prefix)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
        return
    except ImportError:
        pass
    cwd = Path.cwd()
    for directory in (cwd, *cwd.parents):
        env_file = directory / ".env"
        if env_file.is_file():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
            return


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    model: str = os.getenv("RI_MODEL", "claude-sonnet-4-6")
    judge_model: str = os.getenv("RI_JUDGE_MODEL", "claude-opus-4-8")
    max_tokens: int = int(os.getenv("RI_MAX_TOKENS", "2048"))
    max_schema_retries: int = int(os.getenv("RI_MAX_SCHEMA_RETRIES", "2"))

    @classmethod
    def from_env(cls) -> "Settings":
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")
        return cls(anthropic_api_key=key)
