from __future__ import annotations

import httpx


def create_local_runtime_client(*, base_url: str, timeout: float) -> httpx.Client:
    return httpx.Client(
        base_url=base_url,
        timeout=timeout,
        trust_env=False,
    )
