from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTime, QUrl, Signal
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSystemTrayIcon,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
    QMenu,
)

from ..config import ConfigStore
from ..models import AppConfig, CheckResult
from ..monitor import MonitorController
from ..notifier import NtfyNotifier
from ..schedule import schedule_summary
from ..startup import set_run_at_startup
from ..storage import Storage


def _app_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(Qt.white)
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 16, 16)
    painter.setBrush(Qt.GlobalColor.darkGreen)
    painter.drawRoundedRect(13, 13, 38, 38, 10, 10)
    painter.setBrush(Qt.white)
    painter.drawEllipse(26, 20, 12, 12)
    painter.drawRoundedRect(24, 34, 16, 5, 2, 2)
    painter.end()
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    quitting = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.config_store = ConfigStore()
        self.config = self.config_store.load()
        self.storage = Storage()
        self.monitor = MonitorController()
        self._allow_close = False

        self.setWindowTitle("Smart Bid Watcher")
        self.setWindowIcon(_app_icon())
        self.resize(760, 780)
        self.setMinimumSize(680, 680)
        self._build_ui()
        self._build_tray()
        self._load_config_into_ui()
        self._load_recent_notices()
        self._wire_events()

    def show_initial(self) -> None:
        # Every launch starts with the settings window visible. Monitoring only
        # begins after the user explicitly presses the Start button.
        self.show()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(22, 20, 22, 18)
        root_layout.setSpacing(14)

        header = QFrame()
        header.setObjectName("Header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        titles = QVBoxLayout()
        app_title = QLabel("Smart Bid Watcher")
        app_title.setObjectName("AppTitle")
        subtitle = QLabel("나라장터 입찰공고·발주계획·사전규격을 확인합니다")
        subtitle.setObjectName("AppSubtitle")
        titles.addWidget(app_title)
        titles.addWidget(subtitle)
        header_layout.addLayout(titles)
        header_layout.addStretch()
        self.status_pill = QLabel("●  대기 중")
        self.status_pill.setObjectName("StatusPill")
        header_layout.addWidget(self.status_pill)
        root_layout.addWidget(header)

        tabs = QTabWidget()
        tabs.addTab(self._build_monitor_tab(), "모니터링")
        tabs.addTab(self._build_connection_tab(), "연결 설정")
        root_layout.addWidget(tabs, 1)

        footer = QHBoxLayout()
        self.last_check_label = QLabel("아직 확인하지 않았습니다")
        self.last_check_label.setObjectName("Muted")
        footer.addWidget(self.last_check_label)
        footer.addStretch()
        self.check_button = QPushButton("지금 확인")
        self.stop_button = QPushButton("중지")
        self.stop_button.setObjectName("Danger")
        self.start_button = QPushButton("모니터링 시작")
        self.start_button.setObjectName("Primary")
        footer.addWidget(self.check_button)
        footer.addWidget(self.stop_button)
        footer.addWidget(self.start_button)
        root_layout.addLayout(footer)
        self.setCentralWidget(root)

    def _build_monitor_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 14, 4, 4)
        layout.setSpacing(12)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 16)
        title = QLabel("검색 조건")
        title.setObjectName("SectionTitle")
        card_layout.addWidget(title)
        form = QFormLayout()
        form.setVerticalSpacing(10)
        self.keywords_edit = QPlainTextEdit()
        self.keywords_edit.setPlaceholderText("한 줄에 하나씩 입력\n예: 스마트 경로당")
        self.keywords_edit.setFixedHeight(92)
        self.match_mode_combo = QComboBox()
        self.match_mode_combo.addItems(["OR — 하나라도 포함", "AND — 모두 포함"])
        notice_types = QWidget()
        notice_types_layout = QHBoxLayout(notice_types)
        notice_types_layout.setContentsMargins(0, 0, 0, 0)
        self.bid_notice_check = QCheckBox("입찰공고")
        self.order_plan_check = QCheckBox("발주계획")
        self.pre_spec_check = QCheckBox("사전규격")
        notice_types_layout.addWidget(self.bid_notice_check)
        notice_types_layout.addWidget(self.order_plan_check)
        notice_types_layout.addWidget(self.pre_spec_check)
        notice_types_layout.addStretch()
        self.exclusions_edit = QLineEdit()
        self.exclusions_edit.setPlaceholderText("쉼표로 구분: 취소, 정정")
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["5분", "10분", "20분", "30분"])
        operating_hours = QWidget()
        operating_hours_layout = QHBoxLayout(operating_hours)
        operating_hours_layout.setContentsMargins(0, 0, 0, 0)
        self.active_start_edit = QTimeEdit()
        self.active_start_edit.setDisplayFormat("HH:mm")
        self.active_end_edit = QTimeEdit()
        self.active_end_edit.setDisplayFormat("HH:mm")
        operating_hours_layout.addWidget(self.active_start_edit)
        operating_hours_layout.addWidget(QLabel("부터"))
        operating_hours_layout.addWidget(self.active_end_edit)
        operating_hours_layout.addWidget(QLabel("까지"))
        operating_hours_layout.addStretch()
        operating_days = QWidget()
        operating_days_layout = QHBoxLayout(operating_days)
        operating_days_layout.setContentsMargins(0, 0, 0, 0)
        self.weekday_checks = []
        for label in ("월", "화", "수", "목", "금", "토", "일"):
            checkbox = QCheckBox(label)
            self.weekday_checks.append(checkbox)
            operating_days_layout.addWidget(checkbox)
        operating_days_layout.addStretch()
        self.skip_holidays_check = QCheckBox("대한민국 공휴일에는 실행하지 않음")
        form.addRow("검색어", self.keywords_edit)
        form.addRow("조회 대상", notice_types)
        form.addRow("검색 방식", self.match_mode_combo)
        form.addRow("제외 단어", self.exclusions_edit)
        form.addRow("확인 주기", self.interval_combo)
        form.addRow("운영 시간", operating_hours)
        form.addRow("운영 요일", operating_days)
        form.addRow("", self.skip_holidays_check)
        card_layout.addLayout(form)
        layout.addWidget(card)

        recent_header = QHBoxLayout()
        recent_title = QLabel("최근 발견 공고")
        recent_title.setObjectName("SectionTitle")
        self.notice_count_label = QLabel("0건")
        self.notice_count_label.setObjectName("Muted")
        recent_header.addWidget(recent_title)
        recent_header.addStretch()
        recent_header.addWidget(self.notice_count_label)
        layout.addLayout(recent_header)
        self.notice_list = QListWidget()
        self.notice_list.setAlternatingRowColors(False)
        self.notice_list.itemActivated.connect(self._open_notice)
        layout.addWidget(self.notice_list, 1)
        return page

    def _build_connection_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 14, 4, 4)
        layout.setSpacing(12)

        g2b_card = QFrame()
        g2b_card.setObjectName("Card")
        g2b_layout = QVBoxLayout(g2b_card)
        g2b_layout.setContentsMargins(16, 14, 16, 16)
        g2b_title = QLabel("나라장터 OpenAPI 인증키")
        g2b_title.setObjectName("SectionTitle")
        g2b_layout.addWidget(g2b_title)
        g2b_help = QLabel(
            "공공데이터포털 일반 인증키 하나를 입력하면 선택한 모든 나라장터 서비스에 사용합니다."
        )
        g2b_help.setWordWrap(True)
        g2b_help.setObjectName("Muted")
        g2b_layout.addWidget(g2b_help)
        self.g2b_key_edit = QLineEdit()
        self.g2b_key_edit.setEchoMode(QLineEdit.Password)
        self.g2b_key_edit.setPlaceholderText("공공데이터포털 일반 인증키")
        key_row = QHBoxLayout()
        key_row.addWidget(self.g2b_key_edit, 1)
        self.g2b_key_toggle = QPushButton("표시")
        self.g2b_key_toggle.setCheckable(True)
        key_row.addWidget(self.g2b_key_toggle)
        g2b_layout.addLayout(key_row)
        self.g2b_key_state = QLabel("저장된 인증키 없음")
        self.g2b_key_state.setObjectName("Muted")
        g2b_layout.addWidget(self.g2b_key_state)
        layout.addWidget(g2b_card)

        ntfy_card = QFrame()
        ntfy_card.setObjectName("Card")
        ntfy_layout = QVBoxLayout(ntfy_card)
        ntfy_layout.setContentsMargins(16, 14, 16, 16)
        row = QHBoxLayout()
        ntfy_title = QLabel("ntfy 푸시 알림")
        ntfy_title.setObjectName("SectionTitle")
        self.ntfy_state = QLabel("토픽 준비됨")
        self.ntfy_state.setObjectName("Muted")
        row.addWidget(ntfy_title)
        row.addStretch()
        row.addWidget(self.ntfy_state)
        ntfy_layout.addLayout(row)
        ntfy_help = QLabel("휴대폰 ntfy 앱에서 아래 토픽을 구독하면 새 항목을 바로 받을 수 있습니다.")
        ntfy_help.setWordWrap(True)
        ntfy_help.setObjectName("Muted")
        ntfy_layout.addWidget(ntfy_help)
        form = QFormLayout()
        self.ntfy_server_edit = QLineEdit()
        self.ntfy_server_edit.setPlaceholderText("https://ntfy.sh")
        self.ntfy_topic_edit = QLineEdit()
        self.ntfy_topic_edit.setPlaceholderText("추측하기 어려운 비공개 토픽 이름")
        form.addRow("서버 주소", self.ntfy_server_edit)
        form.addRow("구독 토픽", self.ntfy_topic_edit)
        ntfy_layout.addLayout(form)
        ntfy_actions = QHBoxLayout()
        self.ntfy_enabled_check = QCheckBox("새 항목을 ntfy로 알림")
        self.ntfy_test_button = QPushButton("테스트 발송")
        ntfy_actions.addWidget(self.ntfy_enabled_check)
        ntfy_actions.addStretch()
        ntfy_actions.addWidget(self.ntfy_test_button)
        ntfy_layout.addLayout(ntfy_actions)
        layout.addWidget(ntfy_card)

        behavior_card = QFrame()
        behavior_card.setObjectName("Card")
        behavior_layout = QVBoxLayout(behavior_card)
        behavior_layout.setContentsMargins(16, 14, 16, 16)
        behavior_title = QLabel("앱 동작")
        behavior_title.setObjectName("SectionTitle")
        behavior_layout.addWidget(behavior_title)
        self.startup_check = QCheckBox("Windows 시작 시 설정 창 열기")
        self.tray_check = QCheckBox("닫을 때 시스템 트레이로 최소화")
        behavior_layout.addWidget(self.startup_check)
        behavior_layout.addWidget(self.tray_check)
        layout.addWidget(behavior_card)
        layout.addStretch()
        return page

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(_app_icon(), self)
        self.tray.setToolTip("Smart Bid Watcher")
        menu = QMenu()
        show_action = QAction("Smart Bid Watcher 열기", self)
        start_action = QAction("모니터링 시작", self)
        stop_action = QAction("모니터링 중지", self)
        quit_action = QAction("종료", self)
        show_action.triggered.connect(self._show_window)
        start_action.triggered.connect(self._start)
        stop_action.triggered.connect(self.monitor.stop)
        quit_action.triggered.connect(self._quit)
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(start_action)
        menu.addAction(stop_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self._show_window()
            if reason == QSystemTrayIcon.DoubleClick
            else None
        )
        self.tray.show()

    def _wire_events(self) -> None:
        self.start_button.clicked.connect(self._start)
        self.stop_button.clicked.connect(self.monitor.stop)
        self.check_button.clicked.connect(self._check_now)
        self.ntfy_test_button.clicked.connect(self._test_ntfy)
        self.g2b_key_toggle.toggled.connect(self._toggle_api_key_visibility)
        self.g2b_key_edit.textChanged.connect(self._update_api_key_state)
        self.monitor.status.connect(self._on_monitor_status)
        self.monitor.result.connect(self._on_result)
        self.monitor.failed.connect(self._on_error)
        self.monitor.running_changed.connect(self._on_running_changed)

    def _load_config_into_ui(self) -> None:
        self.keywords_edit.setPlainText("\n".join(self.config.keywords))
        self.bid_notice_check.setChecked("bid_notice" in self.config.notice_types)
        self.order_plan_check.setChecked("order_plan" in self.config.notice_types)
        self.pre_spec_check.setChecked("pre_spec" in self.config.notice_types)
        self.match_mode_combo.setCurrentIndex(1 if self.config.match_mode == "AND" else 0)
        self.exclusions_edit.setText(", ".join(self.config.exclusions))
        self.interval_combo.setCurrentText(f"{self.config.interval_minutes}분")
        self.active_start_edit.setTime(
            QTime.fromString(self.config.active_start_time, "HH:mm")
        )
        self.active_end_edit.setTime(
            QTime.fromString(self.config.active_end_time, "HH:mm")
        )
        for index, checkbox in enumerate(self.weekday_checks):
            checkbox.setChecked(index in self.config.active_weekdays)
        self.skip_holidays_check.setChecked(self.config.skip_public_holidays)
        self.g2b_key_edit.setText(self.config.g2b_api_key)
        self._update_api_key_state(saved=True)
        self.ntfy_server_edit.setText(self.config.ntfy_server_url)
        self.ntfy_topic_edit.setText(self.config.ntfy_topic)
        self.ntfy_enabled_check.setChecked(self.config.ntfy_enabled)
        self.startup_check.setChecked(self.config.run_at_startup)
        self.tray_check.setChecked(self.config.minimize_to_tray)

    def _collect_config(self) -> AppConfig:
        keywords = [line.strip() for line in self.keywords_edit.toPlainText().splitlines() if line.strip()]
        exclusions = [word.strip() for word in self.exclusions_edit.text().split(",") if word.strip()]
        notice_types = []
        if self.bid_notice_check.isChecked():
            notice_types.append("bid_notice")
        if self.order_plan_check.isChecked():
            notice_types.append("order_plan")
        if self.pre_spec_check.isChecked():
            notice_types.append("pre_spec")
        return AppConfig(
            keywords=keywords,
            notice_types=notice_types,
            match_mode="AND" if self.match_mode_combo.currentIndex() == 1 else "OR",
            exclusions=exclusions,
            interval_minutes=int(self.interval_combo.currentText().replace("분", "")),
            active_start_time=self.active_start_edit.time().toString("HH:mm"),
            active_end_time=self.active_end_edit.time().toString("HH:mm"),
            active_weekdays=[
                index
                for index, checkbox in enumerate(self.weekday_checks)
                if checkbox.isChecked()
            ],
            skip_public_holidays=self.skip_holidays_check.isChecked(),
            g2b_api_key=self.g2b_key_edit.text().strip(),
            ntfy_server_url=self.ntfy_server_edit.text().strip(),
            ntfy_topic=self.ntfy_topic_edit.text().strip(),
            ntfy_enabled=self.ntfy_enabled_check.isChecked(),
            run_at_startup=self.startup_check.isChecked(),
            minimize_to_tray=self.tray_check.isChecked(),
        )

    def _save(self, require_api_key: bool = False) -> bool:
        config = self._collect_config()
        if not config.keywords:
            QMessageBox.warning(self, "검색어 필요", "검색어를 하나 이상 입력해 주세요.")
            return False
        if not config.notice_types:
            QMessageBox.warning(self, "조회 대상 필요", "조회 대상을 하나 이상 선택해 주세요.")
            return False
        if not config.active_weekdays:
            QMessageBox.warning(self, "운영 요일 필요", "운영 요일을 하나 이상 선택해 주세요.")
            return False
        if config.active_start_time == config.active_end_time:
            QMessageBox.warning(
                self,
                "운영 시간 확인",
                "운영 시작 시간과 종료 시간을 다르게 설정해 주세요.",
            )
            return False
        if require_api_key and not self._validate_selected_api_keys(config):
            return False
        try:
            self.config_store.save(config)
            saved = self.config_store.load()
            if saved.g2b_api_key != config.g2b_api_key:
                raise OSError("저장 후 인증키 검증에 실패했습니다.")
        except OSError as exc:
            QMessageBox.critical(self, "설정 저장 실패", str(exc))
            return False
        self.config = config
        try:
            # Synchronize every time so stale registry entries from an older
            # version are also removed or updated.
            set_run_at_startup(config.run_at_startup)
        except OSError as exc:
            QMessageBox.warning(self, "시작프로그램 설정", str(exc))
        self._update_api_key_state(saved=True)
        return True

    def _start(self) -> None:
        if not self._save(require_api_key=True):
            return
        self.monitor.start(self.config)
        self._set_status(f"모니터링 중 · {self.config.interval_minutes}분 간격")
        self.tray.setToolTip(
            f"Smart Bid Watcher · 모니터링 중 · {self.config.interval_minutes}분 간격"
        )
        self.tray.showMessage(
            "Smart Bid Watcher",
            "모니터링을 시작했습니다.\n"
            f"{schedule_summary(self.config)}\n"
            f"운영 시간에는 {self.config.interval_minutes}분마다 확인합니다.",
            QSystemTrayIcon.Information,
            5000,
        )
        self.hide()

    def _check_now(self) -> None:
        if self.monitor.is_running:
            QMessageBox.information(self, "확인 중", "이미 모니터링이 실행 중입니다.")
            return
        if self._save(require_api_key=True):
            self.monitor.start(self.config, run_once=True)

    def _validate_selected_api_keys(self, config: AppConfig | None = None) -> bool:
        config = config or self.config
        labels = {
            "bid_notice": "입찰공고",
            "order_plan": "발주계획",
            "pre_spec": "사전규격",
        }
        key = config.g2b_api_key.strip()
        if key and all(character in "*•●·" for character in key):
            QMessageBox.warning(
                self,
                "실제 API 키 필요",
                "별표나 점 문자가 아니라 공공데이터포털의 실제 일반 인증키를 입력해 주세요.",
            )
            return False
        missing = config.missing_api_key_types()
        if not missing:
            return True
        names = ", ".join(labels.get(kind, kind) for kind in missing)
        QMessageBox.warning(
            self,
            "API 키 필요",
            f"선택한 조회 대상의 인증키를 입력해 주세요: {names}",
        )
        return False

    def _toggle_api_key_visibility(self, visible: bool) -> None:
        self.g2b_key_edit.setEchoMode(
            QLineEdit.Normal if visible else QLineEdit.Password
        )
        self.g2b_key_toggle.setText("숨김" if visible else "표시")

    def _update_api_key_state(self, _text: str = "", *, saved: bool = False) -> None:
        length = len(self.g2b_key_edit.text().strip())
        if length:
            prefix = "저장된 인증키 있음" if saved else "저장 전 인증키 입력됨"
            self.g2b_key_state.setText(f"{prefix} · {length}자")
        else:
            self.g2b_key_state.setText(
                "저장된 인증키 없음" if saved else "인증키 없음"
            )

    def _test_ntfy(self) -> None:
        if not self._save():
            return
        notifier = NtfyNotifier(self.config.ntfy_server_url, self.config.ntfy_topic)
        try:
            notifier.send_test()
        except Exception as exc:
            QMessageBox.warning(self, "테스트 실패", str(exc))
            return
        QMessageBox.information(self, "발송 완료", "ntfy 앱에서 구독 토픽을 확인해 주세요.")

    def _on_result(self, result: CheckResult) -> None:
        self.last_check_label.setText(result.checked_at.strftime("마지막 확인  %Y-%m-%d %H:%M:%S"))
        self.tray.setToolTip(
            result.checked_at.strftime(
                f"Smart Bid Watcher · 모니터링 중 · 마지막 확인 %H:%M:%S"
            )
        )
        if result.baseline_created:
            message = (
                f"기준선 저장 완료 · 전체 {result.fetched_count}건 · "
                f"검색어 일치 {result.matched_count}건"
            )
        elif result.new_notices:
            message = f"새 공고 {len(result.new_notices)}건 발견"
            self.tray.showMessage("Smart Bid Watcher", message, QSystemTrayIcon.Information, 5000)
        else:
            message = (
                f"새 항목 없음 · 전체 {result.fetched_count}건 · "
                f"검색어 일치 {result.matched_count}건"
            )
        if result.errors:
            message += f" · 일부 조회 실패 {len(result.errors)}건"
            self.tray.showMessage(
                "Smart Bid Watcher 일부 조회 실패",
                "\n".join(result.errors[:3]),
                QSystemTrayIcon.Warning,
                7000,
            )
        self._set_status(message)
        self._load_recent_notices()

    def _on_error(self, message: str) -> None:
        self._set_status("확인 실패")
        self.tray.setToolTip("Smart Bid Watcher · 모니터링 중 · 최근 확인 실패")
        self.tray.showMessage("Smart Bid Watcher", message, QSystemTrayIcon.Warning, 6000)
        if self.isVisible():
            QMessageBox.warning(self, "확인 실패", message)

    def _on_running_changed(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.check_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        if not running and self.status_pill.text() == "●  모니터링을 중지하는 중…":
            self._set_status("중지됨")
        if not running:
            self.tray.setToolTip("Smart Bid Watcher · 중지됨")

    def _on_monitor_status(self, text: str) -> None:
        self._set_status(text)
        self.tray.setToolTip(f"Smart Bid Watcher · {text}")

    def _set_status(self, text: str) -> None:
        self.status_pill.setText(f"●  {text}")

    def _load_recent_notices(self) -> None:
        rows = self.storage.recent_notices()
        self.notice_list.clear()
        for row in rows:
            published = row["published_at"] or row["first_seen_at"]
            item = QListWidgetItem(f"{row['title']}\n{row['organization']}  ·  {published}")
            item.setData(Qt.UserRole, row["url"])
            item.setToolTip("더블클릭하면 공고 페이지를 엽니다.")
            self.notice_list.addItem(item)
        if not rows:
            item = QListWidgetItem("아직 발견한 공고가 없습니다.\n모니터링을 시작하면 여기에 표시됩니다.")
            item.setFlags(Qt.NoItemFlags)
            self.notice_list.addItem(item)
        self.notice_count_label.setText(f"{len(rows)}건")

    def _open_notice(self, item: QListWidgetItem) -> None:
        url = item.data(Qt.UserRole)
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _show_window(self) -> None:
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save()
        if self._allow_close or not self.config.minimize_to_tray:
            self.monitor.stop()
            event.accept()
        else:
            event.ignore()
            self.hide()
            self.tray.showMessage(
                "Smart Bid Watcher",
                "트레이에서 계속 실행 중입니다.",
                QSystemTrayIcon.Information,
                3000,
            )

    def _quit(self) -> None:
        self._allow_close = True
        self.monitor.stop()
        self.tray.hide()
        QApplication.quit()
