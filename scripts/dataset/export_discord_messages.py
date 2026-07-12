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

GUILD_ID = "785950838534438972"
CHANNEL_IDS = (
    "785957900869959730",
    "804280983347658804",
    "785957242863222805",
    "785958361312133130",
    "785966267407401000",
    "786351267336683530",
    "829039222383181875",
    "829038558869585980",
    "829038366674255905",
    "1084166646630985748",
    "883042598464417912",
    "913151527886147674",
    "921501000118992907",
    "793580083997573143",
    "788880695400726548",
    "785954481472143401",
    "785954423515381790",
    "785950838988210208",
    "786215601999314947",
    "785954551692918845",
    "785955802015596556",
    "785962855530627103",
    "806591910843514941",
    "785962801323180042",
)
RECIPIENT_USER_ID = "762514681209946122"
MAX_MESSAGES = None
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
        channel_ids=CHANNEL_IDS,
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
