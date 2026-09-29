from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from urllib.parse import unquote

import requests

from ..models import Notice
from .base import ProcurementProvider


class DataGoKrError(RuntimeError):
    pass


class DataGoKrListProvider(ProcurementProvider):
    base_url: str
    endpoints: dict[str, str]

    def __init__(self, service_key: str, timeout: int = 25) -> None:
        self.service_key = unquote(service_key.strip())
        self.timeout = timeout
        self.last_errors: list[str] = []
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "SmartBidWatcher/1.1"})

    def fetch(self, start: datetime, end: datetime) -> list[Notice]:
        if not self.service_key:
            raise DataGoKrError("나라장터 공공데이터 API 인증키를 입력해 주세요.")
        notices: dict[str, Notice] = {}
        errors: list[str] = []
        for category, endpoint in self.endpoints.items():
            try:
                for notice in self._fetch_category(category, endpoint, start, end):
                    notices[notice.notice_id] = notice
            except DataGoKrError as exc:
                errors.append(f"{category}: {exc}")
        self.last_errors = errors
        if not notices and errors:
            raise DataGoKrError(" / ".join(errors))
        return list(notices.values())

    def _fetch_category(
        self, category: str, endpoint: str, start: datetime, end: datetime
    ) -> list[Notice]:
        page = 1
        results: list[Notice] = []
        while page <= 10:
            params = {
                "ServiceKey": self.service_key,
                "pageNo": page,
                "numOfRows": 100,
                "type": "json",
                **self.query_params(start, end),
            }
            try:
                response = self.session.get(
                    f"{self.base_url}/{endpoint}", params=params, timeout=self.timeout
                )
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as exc:
                raise DataGoKrError(f"API 연결 실패: {exc}") from exc
            body = self.extract_body(payload)
            items = body.get("items") or []
            if isinstance(items, dict):
                items = items.get("item", [])
            if isinstance(items, dict):
                items = [items]
            for item in items:
                notice = self.parse_notice(item, category)
                if notice.notice_id:
                    results.append(notice)
            total = int(body.get("totalCount") or len(items))
            if page * 100 >= total or not items:
                break
            page += 1
        return results

    @staticmethod
    def extract_body(payload: dict) -> dict:
        response = payload.get("response", payload)
        header = response.get("header", {})
        code = str(header.get("resultCode", "00"))
        if code not in {"00", "0"}:
            raise DataGoKrError(header.get("resultMsg") or f"API 오류({code})")
        return response.get("body", {})

    @abstractmethod
    def query_params(self, start: datetime, end: datetime) -> dict:
        raise NotImplementedError

    @abstractmethod
    def parse_notice(self, item: dict, category: str) -> Notice:
        raise NotImplementedError
