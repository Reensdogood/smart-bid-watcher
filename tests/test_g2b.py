import pytest

from smart_bid_watcher.providers.g2b import G2BError, G2BProvider


def test_parse_notice_uses_number_and_order_as_identity():
    item = {
        "bidNtceNo": "20260922001",
        "bidNtceOrd": "01",
        "bidNtceNm": "스마트 경로당 구축",
        "dminsttNm": "테스트시청",
        "bidNtceDt": "2026-09-22 10:00:00",
        "bidNtceDtlUrl": "https://example.test/bid",
    }
    notice = G2BProvider._parse_notice(item, "용역")
    assert notice.notice_id == "20260922001-01"
    assert notice.category == "용역"
    assert notice.organization == "테스트시청"


def test_extract_body_rejects_api_error():
    with pytest.raises(G2BError):
        G2BProvider._extract_body(
            {"response": {"header": {"resultCode": "30", "resultMsg": "SERVICE KEY IS NOT REGISTERED ERROR"}}}
        )


def test_parse_notice_rejects_item_without_notice_number():
    notice = G2BProvider._parse_notice({"bidNtceNm": "번호 없는 항목"}, "용역")
    assert notice.notice_id == ""
