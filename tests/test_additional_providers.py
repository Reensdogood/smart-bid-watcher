from smart_bid_watcher.providers.order_plan import OrderPlanProvider
from smart_bid_watcher.providers.pre_spec import PreSpecificationProvider


def test_order_plan_mapping():
    notice = OrderPlanProvider("key").parse_notice(
        {
            "orderPlanUntyNo": "5-1-2026-1234567-000001",
            "bizNm": "스마트 경로당 구축",
            "orderInsttNm": "테스트시청",
            "nticeDt": "2026-09-23 10:00:00",
        },
        "용역",
    )
    assert notice.source == "G2B_ORDER_PLAN"
    assert notice.notice_id == "5-1-2026-1234567-000001"
    assert notice.category == "발주계획·용역"


def test_pre_spec_mapping():
    notice = PreSpecificationProvider("key").parse_notice(
        {
            "bfSpecRgstNo": "1234567",
            "prdctClsfcNoNm": "스마트 경로당 시스템",
            "rlDminsttNm": "테스트시청",
            "rgstDt": "2026-09-23 11:00:00",
        },
        "물품",
    )
    assert notice.source == "G2B_PRE_SPEC"
    assert notice.notice_id == "1234567"
    assert notice.category == "사전규격·물품"
