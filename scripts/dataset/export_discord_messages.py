from __future__ import annotations

import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from application.services.discord_message_export_service import DiscordMessageExportService
from infrastructure.config.settings import BotConfig
from infrastructure.logging import get_logger

logger = get_logger(__name__)

GUILD_ID = "1030229862310486036"
CHANNEL_ID = "1030232745793818644"
RECIPIENT_USER_ID = "762514681209946122"
MAX_MESSAGES = 5_000
MAX_FILE_BYTES = 7_500_000


class ExportServiceProtocol(Protocol):
    def run(self) -> dict[str, object]: ...


def execute_in_worker(service: ExportServiceProtocol) -> dict[str, object]:
    logger.info("Scheduling Discord dataset export in a dedicated worker thread")
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="discord-dataset-export") as executor:
        return executor.submit(service.run).result()


def main() -> None:
    config = BotConfig()
    token = config.discord_token.get_secret_value()
    configured_salt = os.environ.get("DISCORD_EXPORT_HASH_SALT", "").strip()
    hash_salt = configured_salt or hashlib.sha256(token.encode("utf-8")).hexdigest()
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_directory = PROJECT_ROOT / "data" / "exports" / "discord_messages" / timestamp

    service = DiscordMessageExportService(
        bot_token=token,
        guild_id=GUILD_ID,
        channel_id=CHANNEL_ID,
        recipient_user_id=RECIPIENT_USER_ID,
        output_directory=output_directory,
        hash_salt=hash_salt,
        proxy_url=config.discord_proxy_url,
        max_messages=MAX_MESSAGES,
        max_file_bytes=MAX_FILE_BYTES,
    )
    manifest = execute_in_worker(service)
    logger.info("Discord dataset export script completed rows=%s parts=%s", manifest["rows"], len(manifest["parts"]))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
