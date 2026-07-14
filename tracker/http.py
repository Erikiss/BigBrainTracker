"""Small HTTP helper with retries and a shared session."""

from __future__ import annotations

import time

import requests

USER_AGENT = "BigBrainTracker/1.0 (+https://github.com/Erikiss/BigBrainTracker)"

_RETRY_STATUS = {429, 500, 502, 503, 504}

_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT


class HttpError(RuntimeError):
    """Request failed after all retries (or with a non-retryable status)."""


def get(url: str, params: dict | None = None, *,
        timeout: float = 30.0, retries: int = 3, backoff: float = 2.0) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = _session.get(url, params=params, timeout=timeout)
            if response.status_code in _RETRY_STATUS:
                last_error = HttpError(f"HTTP {response.status_code} für {response.url}")
            else:
                response.raise_for_status()
                return response
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = exc
        except requests.HTTPError as exc:
            # 4xx (außer 429): nicht sinnvoll wiederholbar
            raise HttpError(str(exc)) from exc
        if attempt < retries:
            time.sleep(backoff * (2 ** attempt))
    raise HttpError(str(last_error))
