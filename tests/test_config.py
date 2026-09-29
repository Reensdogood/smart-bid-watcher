from smart_bid_watcher.config import ConfigStore
from smart_bid_watcher.models import AppConfig


def test_config_round_trip(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    expected = AppConfig(keywords=["스마트", "경로당"], match_mode="AND", interval_minutes=5)
    store.save(expected)
    actual = store.load()
    assert actual.keywords == expected.keywords
    assert actual.match_mode == "AND"
    assert actual.interval_minutes == 5


def test_old_config_is_migrated_to_seven_day_lookup(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"keywords":["스마트 경로당"],"lookback_hours":72}', encoding="utf-8")
    actual = ConfigStore(path).load()
    assert actual.lookback_hours == 168
    assert actual.config_version == 5


def test_legacy_single_api_key_remains_the_common_key(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        '{"config_version":2,"g2b_api_key":"legacy-key"}', encoding="utf-8"
    )
    actual = ConfigStore(path).load()
    assert actual.g2b_api_key == "legacy-key"
    assert actual.api_key_for("bid_notice") == "legacy-key"
    assert actual.api_key_for("order_plan") == "legacy-key"
    assert actual.api_key_for("pre_spec") == "legacy-key"


def test_three_key_layout_is_migrated_to_one_common_key(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        '{"config_version":3,"bid_notice_api_key":"shared-key",'
        '"order_plan_api_key":"shared-key","pre_spec_api_key":"shared-key"}',
        encoding="utf-8",
    )
    actual = ConfigStore(path).load()
    assert actual.g2b_api_key == "shared-key"
    assert actual.config_version == 5


def test_missing_common_key_includes_all_selected_services():
    config = AppConfig(
        notice_types=["bid_notice", "pre_spec"],
        g2b_api_key="",
    )
    assert config.missing_api_key_types() == ["bid_notice", "pre_spec"]
