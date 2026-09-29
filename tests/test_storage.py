from smart_bid_watcher.models import Notice
from smart_bid_watcher.storage import Storage


def test_notice_is_unique_and_pending_can_be_updated(tmp_path):
    storage = Storage(tmp_path / "test.db")
    item = Notice("G2B", "2026-00", "스마트 경로당", matched_keywords=["경로당"])
    assert storage.save_notice(item)
    assert not storage.save_notice(item)
    assert storage.has_seen("G2B", "2026-00")
    assert len(storage.pending_notices()) == 1
    storage.mark_notification(item, "sent")
    assert storage.pending_notices() == []


def test_metadata_round_trip(tmp_path):
    storage = Storage(tmp_path / "test.db")
    assert storage.get_meta("baseline") == ""
    storage.set_meta("baseline", "1")
    assert storage.get_meta("baseline") == "1"


def test_pending_can_be_silenced_when_filter_baseline_changes(tmp_path):
    storage = Storage(tmp_path / "test.db")
    item = Notice("G2B", "pending-1", "기존 공고")
    storage.save_notice(item, status="pending")
    storage.mark_all_pending_as_baseline()
    assert storage.pending_notices() == []
