from datetime import datetime

from smart_bid_watcher.models import AppConfig
from smart_bid_watcher.schedule import schedule_decision, schedule_summary


def default_config(**overrides):
    values = {
        "active_start_time": "09:00",
        "active_end_time": "19:00",
        "active_weekdays": [0, 1, 2, 3, 4],
        "skip_public_holidays": True,
    }
    values.update(overrides)
    return AppConfig(**values)


def test_weekday_inside_operating_hours_is_active():
    decision = schedule_decision(datetime(2026, 9, 29, 10, 0), default_config())
    assert decision.active


def test_end_time_is_excluded_and_next_start_is_tomorrow():
    decision = schedule_decision(datetime(2026, 9, 29, 19, 0), default_config())
    assert not decision.active
    assert decision.reason == "운영 시간 아님"
    assert decision.next_active_at == datetime(2026, 9, 30, 9, 0)


def test_weekend_waits_until_monday():
    decision = schedule_decision(datetime(2026, 10, 10, 10, 0), default_config())
    assert not decision.active
    assert decision.reason == "운영 요일 아님"
    assert decision.next_active_at == datetime(2026, 10, 12, 9, 0)


def test_korean_public_holiday_is_skipped():
    decision = schedule_decision(datetime(2026, 10, 9, 10, 0), default_config())
    assert not decision.active
    assert decision.reason == "공휴일"
    assert decision.next_active_at == datetime(2026, 10, 12, 9, 0)


def test_public_holiday_can_be_enabled_by_setting():
    config = default_config(skip_public_holidays=False)
    assert schedule_decision(datetime(2026, 10, 9, 10, 0), config).active


def test_schedule_summary_includes_days_and_holiday_rule():
    assert schedule_summary(default_config()) == "09:00–19:00 · 월·화·수·목·금 · 공휴일 제외"
