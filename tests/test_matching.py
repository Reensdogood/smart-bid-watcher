from smart_bid_watcher.matching import match_notice
from smart_bid_watcher.models import Notice


def notice(title: str, organization: str = "") -> Notice:
    return Notice("G2B", "1-00", title, organization)


def test_or_matches_any_keyword_and_ignores_spacing():
    result = match_notice(notice("스마트경로당 구축 용역"), ["스마트 경로당", "AI"], "OR", [])
    assert result is not None
    assert result.matched_keywords == ["스마트 경로당"]


def test_and_requires_all_keywords_across_title_and_organization():
    result = match_notice(notice("경로당 구축", "스마트복지과"), ["스마트", "경로당"], "AND", [])
    assert result is not None


def test_exclusion_wins():
    assert match_notice(notice("스마트 경로당 구축 취소"), ["경로당"], "OR", ["취소"]) is None
