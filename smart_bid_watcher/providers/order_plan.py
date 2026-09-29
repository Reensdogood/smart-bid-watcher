from __future__ import annotations

from datetime import datetime

from ..models import Notice
from .data_go_kr import DataGoKrListProvider


class OrderPlanProvider(DataGoKrListProvider):
    source_name = "G2B_ORDER_PLAN"
    base_url = "https://apis.data.go.kr/1230000/ao/OrderPlanSttusService"
    endpoints = {
        "물품": "getOrderPlanSttusListThng",
        "공사": "getOrderPlanSttusListCnstwk",
        "용역": "getOrderPlanSttusListServc",
        "외자": "getOrderPlanSttusListFrgcpt",
    }

    def query_params(self, start: datetime, end: datetime) -> dict:
        return {
            "inqryDiv": "1",
            "orderBgnYm": start.strftime("%Y%m"),
            "orderEndYm": end.strftime("%Y%m"),
            "inqryBgnDt": start.strftime("%Y%m%d%H%M"),
            "inqryEndDt": end.strftime("%Y%m%d%H%M"),
        }

    def parse_notice(self, item: dict, category: str) -> Notice:
        notice_id = str(item.get("orderPlanUntyNo") or "").strip()
        return Notice(
            source=self.source_name,
            notice_id=notice_id,
            title=str(item.get("bizNm") or "발주계획").strip(),
            organization=str(item.get("orderInsttNm") or "").strip(),
            published_at=str(item.get("nticeDt") or item.get("chgDt") or "").strip(),
            url="https://www.g2b.go.kr/",
            category=f"발주계획·{category}",
        )
