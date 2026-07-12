from __future__ import annotations

import json
import threading
from pathlib import Path

import httpx

from application.services.discord_message_export_service import DiscordMessageExportService
from scripts.dataset.export_discord_messages import CHANNEL_ID, GUILD_ID, execute_in_worker


def test_export_script_targets_configured_discord_channel() -> None:
    assert GUILD_ID == "1030229862310486036"
    assert CHANNEL_ID == "1030232745793818644"


def test_export_splits_jsonl_and_delivers_every_part(tmp_path: Path) -> None:
    delivered_parts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/api/v10/channels/channel-1":
            return httpx.Response(200, json={"id": "channel-1", "guild_id": "guild-1"})
        if request.method == "GET" and request.url.path == "/api/v10/channels/channel-1/messages":
            return httpx.Response(
                200,
                json=[
                    _message("3", "user-3", "третье сообщение " * 12),
                    _message("2", "bot-2", "bot", bot=True),
                    _message("1", "user-1", "привет <@123> " * 12),
                ],
            )
        if request.method == "POST" and request.url.path == "/api/v10/users/@me/channels":
            return httpx.Response(200, json={"id": "dm-1"})
        if request.method == "POST" and request.url.path == "/api/v10/channels/dm-1/messages":
            body = request.read().decode("utf-8", errors="ignore")
            delivered_parts.append(body)
            return httpx.Response(200, json={"id": str(len(delivered_parts))})
        return httpx.Response(404, json={"message": "not found"})

    service = DiscordMessageExportService(
        bot_token="token",
        guild_id="guild-1",
        channel_id="channel-1",
        recipient_user_id="recipient-1",
        output_directory=tmp_path,
        hash_salt="s" * 32,
        max_file_bytes=1_500,
        transport=httpx.MockTransport(handler),
    )

    manifest = service.run()

    parts = sorted(tmp_path.glob("*.jsonl"))
    rows = [json.loads(line) for part in parts for line in part.read_text(encoding="utf-8").splitlines()]
    assert manifest["rows"] == 2
    assert manifest["skipped_bot_messages"] == 1
    assert len(parts) == len(delivered_parts) == 2
    assert all(part.stat().st_size <= 1_500 for part in parts)
    assert rows[1]["model_text"].count("@user") == 12
    assert rows[1]["metadata"]["user_id_hash"] != "user-1"


def test_export_rejects_channel_from_another_guild(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "channel-1", "guild_id": "other-guild"})

    service = DiscordMessageExportService(
        bot_token="token",
        guild_id="guild-1",
        channel_id="channel-1",
        recipient_user_id="recipient-1",
        output_directory=tmp_path,
        hash_salt="s" * 32,
        transport=httpx.MockTransport(handler),
    )

    try:
        service.run()
    except ValueError as exc:
        assert "does not belong" in str(exc)
    else:
        raise AssertionError("Expected guild validation failure")


def test_script_executes_export_in_named_worker_thread() -> None:
    class StubService:
        def run(self) -> dict[str, object]:
            return {"thread_name": threading.current_thread().name}

    result = execute_in_worker(StubService())

    assert str(result["thread_name"]).startswith("discord-dataset-export")


def _message(message_id: str, author_id: str, content: str, *, bot: bool = False) -> dict[str, object]:
    return {
        "id": message_id,
        "content": content,
        "timestamp": "2026-07-12T18:00:00+00:00",
        "author": {"id": author_id, "bot": bot},
        "attachments": [],
        "embeds": [],
    }
