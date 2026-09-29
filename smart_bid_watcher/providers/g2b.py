from __future__ import annotations

from datetime import datetime
from urllib.parse import unquote

import requests

from ..models import Notice
from .base import ProcurementProvider


class G2BError(RuntimeError):
    pass


class G2BProvider(ProcurementProvider):
    source_name = "G2B"
    BASE_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"
    ENDPOINTS = {
        "공사": "getBidPblancListInfoCnstwk",
        "용역": "getBidPblancListInfoServc",
        "물품": "getBidPblancListInfoThng",
        "외자": "getBidPblancListInfoFrgcpt",
    }

    def __init__(self, service_key: str, timeout: int = 25) -> None:
        self.service_key = unquote(service_key.strip())
        self.timeout = timeout
        self.last_errors: list[str] = []
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "SmartBidWatcher/1.0"})

    def fetch(self, start: datetime, end: datetime) -> list[Notice]:
        if not self.service_key:
            raise G2BError("나라장터 공공데이터 API 인증키를 입력해 주세요.")
        notices: dict[str, Notice] = {}
        errors: list[str] = []
        for category, endpoint in self.ENDPOINTS.items():
            try:
                for notice in self._fetch_category(category, endpoint, start, end):
                    notices[notice.notice_id] = notice
            except G2BError as exc:
                errors.append(f"{category}: {exc}")
        self.last_errors = errors
        if not notices and errors:
            raise G2BError(" / ".join(errors))
        return list(notices.values())

    def _fetch_category(
        self, category: str, endpoint: str, start: datetime, end: datetime
    ) -> list[Notice]:
        page = 1
        results: list[Notice] = []
        while page <= 10:
            params = {
                "serviceKey": self.service_key,
                "pageNo": page,
                "numOfRows": 100,
                "inqryDiv": "1",
                "inqryBgnDt": start.strftime("%Y%m%d%H%M"),
                "inqryEndDt": end.strftime("%Y%m%d%H%M"),
                "type": "json",
            }
            try:
                response = self.session.get(
                    f"{self.BASE_URL}/{endpoint}", params=params, timeout=self.timeout
                )
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as exc:
                raise G2BError(f"API 연결 실패: {exc}") from exc

            body = self._extract_body(payload)
            items = body.get("items") or []
            if isinstance(items, dict):
                items = items.get("item", [])
            if isinstance(items, dict):
                items = [items]
            for item in items:
                notice = self._parse_notice(item, category)
                if notice.notice_id:
                    results.append(notice)

            total = int(body.get("totalCount") or len(items))
            if page * 100 >= total or not items:
                break
            page += 1
        return results

    @staticmethod
    def _extract_body(payload: dict) -> dict:
        response = payload.get("response", payload)
        header = response.get("header", {})
        code = str(header.get("resultCode", "00"))
        if code not in {"00", "0"}:
            raise G2BError(header.get("resultMsg") or f"API 오류({code})")
        return response.get("body", {})

    @staticmethod
    def _parse_notice(item: dict, category: str) -> Notice:
        number = str(item.get("bidNtceNo") or item.get("bidPbancNo") or "").strip()
        order = str(item.get("bidNtceOrd") or item.get("bidPbancOrd") or "00").strip()
        notice_id = f"{number}-{order}" if number else ""
        detail_url = str(item.get("bidNtceDtlUrl") or "").strip()
        if not detail_url:
            detail_url = "https://www.g2b.go.kr/"
        return Notice(
            source="G2B",
            notice_id=notice_id,
            title=str(item.get("bidNtceNm") or "제목 없음").strip(),
            organization=str(
                item.get("dminsttNm") or item.get("ntceInsttNm") or item.get("crdtrNm") or ""
            ).strip(),
            published_at=str(item.get("bidNtceDt") or "").strip(),
            url=detail_url,
            category=category,
        )
