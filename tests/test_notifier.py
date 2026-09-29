import requests

from smart_bid_watcher.models import Notice
from smart_bid_watcher.notifier import NtfyError, NtfyNotifier


class FakeResponse:
    status_code = 200

    def raise_for_status(self):
        return None


def test_ntfy_send_uses_json_payload_for_korean_text(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured.update(url=url, json=json, timeout=timeout)
        return FakeResponse()

    monkeypatch.setattr("smart_bid_watcher.notifier.requests.post", fake_post)
    notifier = NtfyNotifier("https://ntfy.sh/", "private-topic")
    notifier.send(
        Notice(
            "G2B_ORDER_PLAN",
            "plan-1",
            "스마트 경로당 발주계획",
            "테스트시청",
            category="발주계획·용역",
            matched_keywords=["스마트 경로당"],
            url="https://www.g2b.go.kr/",
        )
    )

    assert captured["url"] == "https://ntfy.sh"
    assert captured["json"]["topic"] == "private-topic"
    assert captured["json"]["click"] == "https://www.g2b.go.kr/"
    assert captured["json"]["priority"] == 4
    assert captured["json"]["title"] == "나라장터 신규 정보"
    assert "발주계획" in captured["json"]["message"]


def test_ntfy_rejects_invalid_topic():
    notifier = NtfyNotifier("https://ntfy.sh", "bad/topic")
    try:
        notifier.send_test()
    except NtfyError as exc:
        assert "토픽" in str(exc)
    else:
        raise AssertionError("NtfyError was not raised")


def test_ntfy_wraps_http_errors(monkeypatch):
    def fake_post(*args, **kwargs):
        response = requests.Response()
        response.status_code = 403
        raise requests.HTTPError("forbidden", response=response)

    monkeypatch.setattr("smart_bid_watcher.notifier.requests.post", fake_post)
    try:
        NtfyNotifier("https://ntfy.sh", "private-topic").send_test()
    except NtfyError as exc:
        assert "403" in str(exc)
    else:
        raise AssertionError("NtfyError was not raised")


def test_ntfy_includes_server_error_detail(monkeypatch):
    class ErrorResponse:
        status_code = 400
        text = '{"error":"invalid request"}'

        def json(self):
            return {"error": "invalid request"}

        def raise_for_status(self):
            raise requests.HTTPError("bad request", response=self)

    monkeypatch.setattr(
        "smart_bid_watcher.notifier.requests.post",
        lambda *args, **kwargs: ErrorResponse(),
    )
    try:
        NtfyNotifier("https://ntfy.sh", "private-topic").send_test()
    except NtfyError as exc:
        assert "invalid request" in str(exc)
    else:
        raise AssertionError("NtfyError was not raised")
