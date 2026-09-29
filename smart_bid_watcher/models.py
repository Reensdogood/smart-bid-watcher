from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from secrets import token_hex


@dataclass(slots=True)
class Notice:
    source: str
    notice_id: str
    title: str
    organization: str = ""
    published_at: str = ""
    url: str = "https://www.g2b.go.kr/"
    category: str = ""
    matched_keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class AppConfig:
    config_version: int = 5
    keywords: list[str] = field(default_factory=lambda: ["스마트 경로당"])
    notice_types: list[str] = field(
        default_factory=lambda: ["bid_notice", "order_plan", "pre_spec"]
    )
    match_mode: str = "OR"
    exclusions: list[str] = field(default_factory=lambda: ["취소"])
    interval_minutes: int = 20
    active_start_time: str = "09:00"
    active_end_time: str = "19:00"
    active_weekdays: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    skip_public_holidays: bool = True
    # A wider first/recovery window prevents a recently posted notice from being
    # missed when the app has not been running for a few days.
    lookback_hours: int = 168
    g2b_api_key: str = ""
    # Retained for one-way migration from the short-lived v1.2 three-key layout.
    bid_notice_api_key: str = ""
    order_plan_api_key: str = ""
    pre_spec_api_key: str = ""
    ntfy_server_url: str = "https://ntfy.sh"
    ntfy_topic: str = field(default_factory=lambda: f"smart-bid-{token_hex(8)}")
    ntfy_enabled: bool = True
    run_at_startup: bool = False
    minimize_to_tray: bool = True

    @classmethod
    def from_dict(cls, values: dict) -> "AppConfig":
        values = dict(values)
        version = int(values.get("config_version") or 0)
        if version < 2:
            values["lookback_hours"] = max(
                int(values.get("lookback_hours") or 0), 168
            )
        if version < 3:
            legacy_key = str(values.get("g2b_api_key") or "").strip()
            for field_name in (
                "bid_notice_api_key",
                "order_plan_api_key",
                "pre_spec_api_key",
            ):
                values.setdefault(field_name, legacy_key)
        if version < 4 and not str(values.get("g2b_api_key") or "").strip():
            values["g2b_api_key"] = next(
                (
                    str(values.get(field_name) or "").strip()
                    for field_name in (
                        "bid_notice_api_key",
                        "order_plan_api_key",
                        "pre_spec_api_key",
                    )
                    if str(values.get(field_name) or "").strip()
                ),
                "",
            )
        values["config_version"] = 5
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: value for key, value in values.items() if key in allowed})

    def to_dict(self) -> dict:
        return asdict(self)

    def api_key_for(self, notice_type: str) -> str:
        return self.g2b_api_key.strip()

    def missing_api_key_types(self) -> list[str]:
        return [kind for kind in self.notice_types if not self.api_key_for(kind)]


@dataclass(slots=True)
class CheckResult:
    checked_at: datetime
    fetched_count: int
    matched_count: int
    new_notices: list[Notice]
    errors: list[str] = field(default_factory=list)
    baseline_created: bool = False
