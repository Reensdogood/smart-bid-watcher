from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from functools import lru_cache

from holidays.countries.south_korea import SouthKorea

from .models import AppConfig


@dataclass(frozen=True, slots=True)
class ScheduleDecision:
    active: bool
    reason: str = ""
    next_active_at: datetime | None = None


def parse_time(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()


@lru_cache(maxsize=8)
def korean_holidays(year: int) -> SouthKorea:
    return SouthKorea(years=[year], language="ko")


def is_public_holiday(moment: datetime) -> bool:
    return moment.date() in korean_holidays(moment.year)


def is_operating_moment(moment: datetime, config: AppConfig) -> bool:
    if moment.weekday() not in config.active_weekdays:
        return False
    if config.skip_public_holidays and is_public_holiday(moment):
        return False
    start = parse_time(config.active_start_time)
    end = parse_time(config.active_end_time)
    current = moment.time().replace(second=0, microsecond=0)
    if start < end:
        return start <= current < end
    return current >= start or current < end


def schedule_decision(moment: datetime, config: AppConfig) -> ScheduleDecision:
    if is_operating_moment(moment, config):
        return ScheduleDecision(active=True)

    if moment.weekday() not in config.active_weekdays:
        reason = "운영 요일 아님"
    elif config.skip_public_holidays and is_public_holiday(moment):
        reason = "공휴일"
    else:
        reason = "운영 시간 아님"

    next_active = _next_active_at(moment, config)
    return ScheduleDecision(False, reason, next_active)


def _next_active_at(moment: datetime, config: AppConfig) -> datetime | None:
    start = parse_time(config.active_start_time)
    cursor = moment.replace(second=0, microsecond=0)
    for offset in range(0, 15):
        day = (cursor + timedelta(days=offset)).date()
        candidate = datetime.combine(day, start)
        if candidate <= moment:
            continue
        if candidate.weekday() not in config.active_weekdays:
            continue
        if config.skip_public_holidays and is_public_holiday(candidate):
            continue
        return candidate
    return None


def schedule_summary(config: AppConfig) -> str:
    labels = ["월", "화", "수", "목", "금", "토", "일"]
    days = "·".join(labels[index] for index in config.active_weekdays)
    holiday = " · 공휴일 제외" if config.skip_public_holidays else ""
    return (
        f"{config.active_start_time}–{config.active_end_time} · "
        f"{days or '운영 요일 없음'}{holiday}"
    )
