import json
import logging

from prayer_sync.observability import JsonFormatter


def test_json_logs_include_only_allowlisted_fields() -> None:
    record = logging.makeLogRecord(
        {
            "name": "prayer_sync.service",
            "levelno": logging.INFO,
            "levelname": "INFO",
            "msg": "provider.fetch.completed",
            "event": "provider.fetch.completed",
            "provider": "mawaqit",
            "outcome": "success",
            "app_specific_password": "must-not-appear",
            "refresh_token": "must-not-appear-either",
        }
    )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "provider.fetch.completed"
    assert payload["provider"] == "mawaqit"
    assert "app_specific_password" not in payload
    assert "refresh_token" not in payload
