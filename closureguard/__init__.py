"""ClosureGuard: Detecting Epistemic Closure Violations in LLM Agent Reasoning Traces."""

import os
from pathlib import Path

__version__ = "0.1.0"


def _load_dotenv() -> None:
    """Load .env file from project root if it exists. No external dependency needed."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if not os.environ.get(key):
                os.environ[key] = value


_load_dotenv()
