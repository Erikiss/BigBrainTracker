"""Small HTTP helper with retries and a shared session."""

from __future__ import annotations

import datetime as dt
from email.utils import parsedate_to_datetime
import time

import requests

USER_AGENT = "BigBrainTracker/1.0 (+https://github.com/Erikiss/BigBrainTracker)"

_RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_RETRY_AFTER_SECONDS = 60

_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT


class HttpError(RuntimeError):
    """Request failed after all retries (or with a non-retryable status)."""


class RateLimitError(HttpError):
    """Request was rate-limited beyond the retry budget."""


def _retry_delay(response: requests.Response, attempt: int, backoff: float) -> float:
    delay = backoff * (2 ** attempt)
    retry_after = response.headers.get("Retry-After", "").strip()
    if not retry_after:
        return delay
    try:
        return max(delay, float(retry_after))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(retry_after)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=dt.timezone.utc)
            return max(delay, (retry_at - dt.datetime.now(dt.timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return delay


def get(url: str, params: dict | None = None, *,
        timeout: float = 30.0, retries: int = 3, backoff: float = 2.0) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        response = None
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
            delay = _retry_delay(response, attempt, backoff) if response is not None else \
                backoff * (2 ** attempt)
            if response is not None and response.status_code == 429 \
                    and delay > MAX_RETRY_AFTER_SECONDS:
                raise RateLimitError(
                    f"HTTP 429 mit Retry-After {delay:.0f}s für {response.url}"
                )
            time.sleep(delay)
    if response is not None and response.status_code == 429:
        raise RateLimitError(str(last_error))
    raise HttpError(str(last_error))
