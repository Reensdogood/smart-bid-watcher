from __future__ import annotations

import threading
import hashlib
import json
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QThread, Signal, Slot

from .matching import match_notice
from .models import AppConfig, CheckResult, Notice
from .notifier import NtfyNotifier
from .providers.g2b import G2BProvider
from .providers.order_plan import OrderPlanProvider
from .providers.pre_spec import PreSpecificationProvider
from .schedule import schedule_decision
from .storage import Storage


class MonitorWorker(QObject):
    status = Signal(str)
    result = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, config: AppConfig, run_once: bool = False) -> None:
        super().__init__()
        self.config = config
        self.run_once = run_once
        self._stop_event = threading.Event()

    @Slot()
    def run(self) -> None:
        try:
            while not self._stop_event.is_set():
                if not self.run_once:
                    decision = schedule_decision(datetime.now(), self.config)
                    if not decision.active:
                        next_text = (
                            decision.next_active_at.strftime("%m-%d %H:%M")
                            if decision.next_active_at
                            else "설정을 확인하세요"
                        )
                        self.status.emit(
                            f"운영 대기 · {decision.reason} · 다음 시작 {next_text}"
                        )
                        wait_seconds = 300
                        if decision.next_active_at:
                            wait_seconds = max(
                                1,
                                min(
                                    300,
                                    int(
                                        (
                                            decision.next_active_at - datetime.now()
                                        ).total_seconds()
                                    ),
                                ),
                            )
                        if self._stop_event.wait(wait_seconds):
                            break
                        continue
                try:
                    self.result.emit(self._check_once())
                except Exception as exc:  # boundary: provider/network/storage
                    self.failed.emit(str(exc))
                if self.run_once:
                    break
                self.status.emit(f"다음 확인까지 {self.config.interval_minutes}분")
                if self._stop_event.wait(self.config.interval_minutes * 60):
                    break
        finally:
            self.finished.emit()

    def stop(self) -> None:
        self._stop_event.set()

    def _check_once(self) -> CheckResult:
        if not self.config.notice_types:
            raise RuntimeError("조회 대상을 하나 이상 선택해 주세요.")
        self.status.emit("나라장터 데이터를 확인하는 중…")
        now = datetime.now()
        storage = Storage()
        provider_types = {
            "bid_notice": G2BProvider,
            "order_plan": OrderPlanProvider,
            "pre_spec": PreSpecificationProvider,
        }
        fetched = []
        provider_errors: list[str] = []
        type_labels = {
            "bid_notice": "입찰공고",
            "order_plan": "발주계획",
            "pre_spec": "사전규격",
        }
        for notice_type in self.config.notice_types:
            provider_class = provider_types.get(notice_type)
            if not provider_class:
                continue
            api_key = self.config.api_key_for(notice_type)
            if not api_key:
                provider_errors.append(
                    f"{type_labels.get(notice_type, notice_type)}: API 인증키가 비어 있습니다."
                )
                continue
            provider = provider_class(api_key)
            try:
                fetched.extend(
                    provider.fetch(now - timedelta(hours=self.config.lookback_hours), now)
                )
                provider_errors.extend(
                    f"{type_labels[notice_type]} {error}"
                    for error in getattr(provider, "last_errors", [])
                )
            except Exception as exc:
                provider_errors.append(f"{type_labels.get(notice_type, notice_type)}: {exc}")
        if not fetched and provider_errors:
            raise RuntimeError(" / ".join(provider_errors))
        matched = [
            candidate
            for notice in fetched
            if (candidate := match_notice(
                notice,
                self.config.keywords,
                self.config.match_mode,
                self.config.exclusions,
            ))
        ]
        signature_payload = {
            "keywords": sorted(word.casefold() for word in self.config.keywords),
            "mode": self.config.match_mode.upper(),
            "exclusions": sorted(word.casefold() for word in self.config.exclusions),
            "notice_types": sorted(self.config.notice_types),
        }
        signature = hashlib.sha256(
            json.dumps(signature_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        baseline = storage.get_meta("baseline_signature") != signature
        new_notices: list[Notice] = []
        for notice in matched:
            if storage.save_notice(notice, status="baseline" if baseline else "pending"):
                if not baseline:
                    new_notices.append(notice)
        if baseline:
            storage.mark_all_pending_as_baseline()
            storage.set_meta("baseline_signature", signature)
        elif self.config.ntfy_enabled:
            notifier = NtfyNotifier(self.config.ntfy_server_url, self.config.ntfy_topic)
            for notice in storage.pending_notices():
                try:
                    notifier.send(notice)
                    storage.mark_notification(notice, "sent")
                except Exception as exc:
                    storage.mark_notification(notice, "pending", str(exc))
        return CheckResult(
            checked_at=now,
            fetched_count=len(fetched),
            matched_count=len(matched),
            new_notices=new_notices,
            errors=provider_errors,
            baseline_created=baseline,
        )


class MonitorController(QObject):
    status = Signal(str)
    result = Signal(object)
    failed = Signal(str)
    running_changed = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self.thread: QThread | None = None
        self.worker: MonitorWorker | None = None

    @property
    def is_running(self) -> bool:
        return bool(self.thread and self.thread.isRunning())

    def start(self, config: AppConfig, run_once: bool = False) -> None:
        if self.is_running:
            return
        self.thread = QThread(self)
        self.worker = MonitorWorker(config, run_once)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.status.connect(self.status)
        self.worker.result.connect(self.result)
        self.worker.failed.connect(self.failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self._on_finished)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        self.running_changed.emit(True)

    def stop(self) -> None:
        if self.worker:
            self.worker.stop()
            self.status.emit("모니터링을 중지하는 중…")

    def _on_finished(self) -> None:
        self.worker = None
        self.thread = None
        self.running_changed.emit(False)
