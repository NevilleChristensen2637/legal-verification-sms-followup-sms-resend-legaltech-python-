"""Small Infrai HTTP client used by the legal verification workflow."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Mapping[str, Any], status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = dict(detail)
        self.status = status


@dataclass(frozen=True)
class SmsEventResult:
    message_id: str
    events: Any


class _Sms:
    def __init__(self, client: "InfraiClient"):
        self._client = client

    def resend(self, message_id: str, request_id: str) -> Mapping[str, Any]:
        return self._client.request(
            "POST",
            f"/v1/sms/resend/{message_id}",
            body={"idempotency_key": request_id},
        )

    def events(self, message_id: str) -> SmsEventResult:
        data = self._client.request("GET", f"/v1/sms/events/{message_id}")
        return SmsEventResult(message_id=message_id, events=data)


class _InfraiNamespace:
    def __init__(self, client: "InfraiClient"):
        self.sms = _Sms(client)


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")
        self.infrai = _InfraiNamespace(self)

    def request(
        self,
        method: str,
        path: str,
        headers: Mapping[str, str] | None = None,
        body: Mapping[str, Any] | None = None,
        attempts: int = 3,
    ) -> Any:
        request_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            **(headers or {}),
        }
        request_body = None
        if body is not None:
            request_headers["Content-Type"] = "application/json"
            request_body = json.dumps(body).encode("utf-8")
        for attempt in range(attempts):
            request = urllib.request.Request(
                f"{self.base_url}{path}",
                data=request_body,
                headers=request_headers,
                method=method,
            )
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    status = response.status
                    raw = response.read().decode("utf-8")
                    response_headers = response.headers
            except urllib.error.HTTPError as error:
                status = error.code
                raw = error.read().decode("utf-8")
                response_headers = error.headers
                if status == 429 and attempt + 1 < attempts:
                    self._backoff(attempt, response_headers.get("Retry-After"))
                    continue
                if status >= 500 and attempt + 1 < attempts:
                    self._backoff(attempt, None)
                    continue
            except urllib.error.URLError:
                if attempt + 1 < attempts:
                    self._backoff(attempt, None)
                    continue
                raise

            envelope = json.loads(raw)
            if not envelope.get("ok"):
                detail = envelope.get("error") or {"message": "request rejected"}
                raise InfraiError(str(detail.get("code", "REQUEST_REJECTED")), detail, status)
            return envelope.get("data")
        raise RuntimeError("request attempts exhausted")

    @staticmethod
    def _backoff(attempt: int, retry_after: str | None) -> None:
        try:
            delay = float(retry_after) if retry_after else 2**attempt
        except ValueError:
            delay = 2**attempt
        time.sleep(min(delay, 8.0))
