from __future__ import annotations

from urllib.parse import urlparse

import requests

from .models import Notice


class NtfyError(RuntimeError):
    pass


class NtfyNotifier:
    def __init__(self, server_url: str, topic: str, timeout: int = 20) -> None:
        self.server_url = server_url.strip().rstrip("/")
        self.topic = topic.strip()
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.server_url and self.topic)

    def send(self, notice: Notice) -> None:
        self._validate()
        message = (
            f"{notice.title}\n\n"
            f"기관: {notice.organization or '-'}\n"
            f"구분: {notice.category or '-'}\n"
            f"번호: {notice.notice_id}\n"
            f"검색어: {', '.join(notice.matched_keywords)}"
        )
        payload = {
            "topic": self.topic,
            "title": "나라장터 신규 정보",
            "message": message,
            "priority": 4,
            "tags": ["mag", "kr"],
        }
        if notice.url:
            payload["click"] = notice.url
        try:
            response = requests.post(
                self.server_url,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            detail = ""
            if getattr(exc, "response", None) is not None:
                response = exc.response
                reason = ""
                try:
                    reason = str(response.json().get("error") or "").strip()
                except (ValueError, AttributeError):
                    reason = response.text.strip()[:300]
                detail = f" ({response.status_code})"
                if reason:
                    detail += f" {reason}"
            raise NtfyError(f"ntfy 알림 발송 실패{detail}: {exc}") from exc

    def send_test(self) -> None:
        self.send(
            Notice(
                source="TEST",
                notice_id="TEST-00",
                title="Smart Bid Watcher 테스트 알림",
                organization="연결 확인",
                category="테스트",
                matched_keywords=["테스트"],
                url="https://www.g2b.go.kr/",
            )
        )

    def _validate(self) -> None:
        parsed = urlparse(self.server_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise NtfyError("ntfy 서버 주소를 확인해 주세요.")
        if not self.topic or "/" in self.topic or len(self.topic) > 64:
            raise NtfyError("ntfy 토픽은 1~64자이며 슬래시(/)를 포함할 수 없습니다.")
