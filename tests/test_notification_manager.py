import asyncio
import json
from unittest.mock import AsyncMock

from src.notifications.manager import NotificationManager


def _critical_result():
    return {"domain": "example.com", "monitor": "ssl", "status": "critical", "message": "Expired"}


def _make_manager(tmp_path):
    manager = NotificationManager(config={}, state_file=str(tmp_path / "state.json"))
    manager.service.send_notification = AsyncMock()
    return manager


def test_new_issue_sends_alert(tmp_path):
    manager = _make_manager(tmp_path)
    asyncio.run(manager.process_and_send([_critical_result()]))
    manager.service.send_notification.assert_awaited_once()
    title, message, level = manager.service.send_notification.await_args.args
    assert "example.com" in title
    assert level == "critical"


def test_repeat_issue_snoozed_within_24h(tmp_path):
    manager = _make_manager(tmp_path)
    asyncio.run(manager.process_and_send([_critical_result()]))
    asyncio.run(manager.process_and_send([_critical_result()]))
    assert manager.service.send_notification.await_count == 1


def test_resolved_issue_removed_from_state(tmp_path):
    manager = _make_manager(tmp_path)
    asyncio.run(manager.process_and_send([_critical_result()]))
    assert manager.state
    asyncio.run(manager.process_and_send([]))
    assert manager.state == {}
    saved = json.loads((tmp_path / "state.json").read_text())
    assert saved == {}


def test_ok_results_do_not_alert(tmp_path):
    manager = _make_manager(tmp_path)
    asyncio.run(manager.process_and_send([{"domain": "example.com", "monitor": "dns", "status": "ok"}]))
    manager.service.send_notification.assert_not_awaited()
