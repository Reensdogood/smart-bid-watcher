from __future__ import annotations

from datetime import datetime

from ..models import Notice
from .data_go_kr import DataGoKrListProvider


class PreSpecificationProvider(DataGoKrListProvider):
    source_name = "G2B_PRE_SPEC"
    base_url = "https://apis.data.go.kr/1230000/ao/HrcspSsstndrdInfoService"
    endpoints = {
        "물품": "getPublicPrcureThngInfoThng",
        "공사": "getPublicPrcureThngInfoCnstwk",
        "용역": "getPublicPrcureThngInfoServc",
        "외자": "getPublicPrcureThngInfoFrgcpt",
    }

    def query_params(self, start: datetime, end: datetime) -> dict:
        return {
            "inqryDiv": "1",
            "inqryBgnDt": start.strftime("%Y%m%d%H%M"),
            "inqryEndDt": end.strftime("%Y%m%d%H%M"),
        }

    def parse_notice(self, item: dict, category: str) -> Notice:
        notice_id = str(item.get("bfSpecRgstNo") or item.get("refNo") or "").strip()
        product_name = str(item.get("prdctClsfcNoNm") or "").strip()
        detail = str(item.get("prdctDtlList") or "").strip()
        title = product_name or detail or f"사전규격 {notice_id}"
        if detail and detail not in title:
            title = f"{title} · {detail[:180]}"
        return Notice(
            source=self.source_name,
            notice_id=notice_id,
            title=title,
            organization=str(item.get("rlDminsttNm") or item.get("orderInsttNm") or "").strip(),
            published_at=str(item.get("rgstDt") or item.get("rcptDt") or item.get("chgDt") or "").strip(),
            url="https://www.g2b.go.kr/",
            category=f"사전규격·{category}",
        )
