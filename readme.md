# OmniBot

<div align="center">

**A Discord bot with a Discord Activity control panel and self-hosted AI moderation through Ollama. Includes role-based Activity access, autoroles, interactive role panels, welcome alerts, dynamic voice rooms, server statistics, SQLite logging, admin tools, and Dev Blog publishing. Built with Python 3.12 + disnake, FastAPI, Vue 3, and a clean architecture with dependency injection.**

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![disnake](https://img.shields.io/badge/disnake-2.9.2-green.svg)](https://github.com/DisnakeDev/disnake)
[![Ollama](https://img.shields.io/badge/Ollama-AI-orange.svg)](https://ollama.ai)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue.svg)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-red.svg)](LICENSE)

</div>

---

## About

OmniBot is designed to automate Discord server management. Its key feature is **self-hosted AI moderation** through Ollama, which allows message classification without sending message content to commercial external AI APIs.

## Key Features

| Module | Description |
| --- | --- |
| **AI Moderation** | Local LLM moderation for spam, ads, invites, bullying, violence, and NSFW detection |
| **Streams** | Twitch, YouTube, and Kick stream announcements |
| **Roles** | Autoroles and interactive role panels with buttons or reactions |
| **Discord Activity** | In-Discord control panel with role-based module access |
| **Voice Rooms** | Dynamic voice rooms with owner controls |
| **Statistics** | Server activity, leaderboards, voice time, and counters |
| **Admin Tools** | Warnings, mutes, kicks, bans, chat cleanup, and slowmode |
| **Logging** | Message, moderation, server event, and Activity audit logs in SQLite |
| **Dev Blog** | Build up to 10 embeds, save drafts, and publish to the configured Dev Blog channel |

---

## Quick Start

### Requirements

| Component | Minimum | Recommended |
| --- | --- | --- |
| Python | 3.12 | 3.12+ |
| RAM without AI | 2 GB | 4 GB |
| RAM with Mistral | 8 GB | 16 GB |
| Disk | 10 GB | 20 GB |
| OS | Linux | Ubuntu 22.04+ |

### Installation

```bash
git clone https://github.com/6oT9lpa/discord-ai-moderation-bot.git
cd discord-ai-moderation-bot

python3.12 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
nano .env

python main.py
```

### Ollama Setup

```bash
curl -fsSL https://ollama.com/install.sh | sh

ollama pull mistral
# or
ollama pull llama3
# or
ollama pull phi3:mini

ollama list

curl http://localhost:11434/api/generate \
  -d '{"model":"mistral","prompt":"Hello"}'
```

### Docker

```bash
docker-compose up -d
```

---

## Modules

### AI Moderation

Example commands:

```text
/ai-stats
/ai-whitelist add #chat
/ai-threshold set 0.85
```

Supported categories:

- `SPAM`
- `ADVERTISEMENT`
- `INVITE`
- `VIOLENCE`
- `BULLYING`
- `NSFW`
- `SAFE`

AI moderation is intended as an assistive tool. Moderators should review disputed detections manually.

### Roles and Autoroles

```text
/role-panel setup #roles
/role-panel add @Gamer
/role-autoassign set @Member
/roles-list
```

Features:

- automatic base role assignment on member join;
- interactive role panels with buttons;
- reaction/emoji role support;
- safe role hierarchy checks.

### Discord Activity Control Panel

OmniBot includes a Discord Activity frontend served by the FastAPI backend. The panel is designed to run inside Discord only; direct browser access is rejected for the protected workspace.

Activity access is controlled by synchronized Discord server roles and separate Activity access roles:

- built-in Activity roles: `user`, `creator`, `developer`, `moderator`, `administrator`;
- Discord administrators can bootstrap role sync with `/sync_roles` or the Activity sync action;
- if roles are not synchronized, non-admin users receive `403`;
- module tabs are hidden when the user's Activity role has no permission for that tab;
- `administrator` Activity role permissions are immutable.

Default visible modules include:

- Dashboard;
- Integrations;
- Health Status;
- Server Stats;
- Voice Rooms.

Administrative modules include:

- Access Control;
- Welcome Alerts;
- Role Panels;
- Dev Blog;
- Logs;
- Bot Settings.

The Activity backend uses aggregated endpoints for heavy panels such as Access Control, Role Panels, and Bot Settings so the UI can wait for complete data before rendering module controls.

### Streams and Publications

```text
/streamer add twitch https://twitch.tv/nick
/stream-template set
/subscribe youtube UCxxxxx
```

Supported platforms:

- Twitch;
- YouTube;
- Kick;
- TikTok/RSS when configured.

### Dynamic Voice Rooms

```text
/room name "My Room"
/room limit 5
/room lock
/room unlock
/room transfer @user
```

Features:

- temporary room creation from a trigger channel;
- owner controls;
- user limit;
- lock/unlock;
- ownership transfer;
- automatic cleanup of empty temporary rooms.

### Statistics

```text
/stats server
/stats user @user
/stats channels
/leaderboard
```

Tracked metrics may include:

- message count;
- active users;
- active channels;
- voice minutes;
- top users;
- top channels;
- member joins and leaves.

### Administration and Moderation

```text
/warn @user reason
/mute @user 10m reason
/unmute @user
/kick @user reason
/ban @user reason
/unban user_id
/purge 50
/slowmode #chat 5
```

Moderation actions are stored in SQLite and can be reviewed through history commands.

### Logging

The Bot can store and publish logs for:

- messages;
- deleted messages;
- edited messages;
- member joins and leaves;
- punishments;
- role changes;
- voice events;
- channel and role updates.

Database: PostgreSQL. SQLite is still supported as a local fallback and as the source format for migration.

Default retention:

- message logs: 30 days;
- expired punishment history: 365 days;
- retention cleanup interval: 6 hours.

### Dev Blog

```text
Activity -> Dev Blog -> Publish
Activity -> Dev Blog -> Save Draft
```

Features:

- multi-embed builder with up to 10 embeds;
- first embed cannot be removed;
- image URLs and per-embed colors;
- up to 10 saved drafts stored in SQLite;
- publish to the Dev Blog channel configured through Bot Settings or `/list_channels`/channel-purpose setup.

---

## Configuration

### `.env`

```env
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=123456789012345678
DISCORD_OWNER_ID=987654321098765432

DATABASE_URL=postgresql://omnibot:change_me@localhost:5432/omnibot

AUTO_ROLE_ID=123456789012345678
LOG_CHANNEL_ID=123456789012345678
WELCOME_CHANNEL_ID=123456789012345678

LOG_LEVEL=INFO
DISCORD_PROXY_URL=http://127.0.0.1:10809
MESSAGE_LOG_RETENTION_DAYS=30
PUNISHMENT_RETENTION_DAYS=365
RETENTION_CLEANUP_INTERVAL_HOURS=6

DISCORD_CLIENT_ID=your_discord_application_client_id
DISCORD_CLIENT_SECRET=your_discord_oauth_client_secret

OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral

TWITCH_CLIENT_ID=your_twitch_id
TWITCH_CLIENT_SECRET=your_twitch_secret
YOUTUBE_API_KEY=your_youtube_key
```

### Discord Configuration

Useful commands may include:

```text
/bot config view
/bot config set KEY value
/bot reload cog
/bot status
/bot uptime
/bot ping
```

### Activity Frontend Configuration

`activity/client/.env` is used at build time:

```env
VITE_DISCORD_CLIENT_ID=your_discord_application_client_id
VITE_API_BASE_URL=
```

For production builds, leave `VITE_API_BASE_URL` empty so the Activity frontend calls the FastAPI backend on the same origin with `/api/...`. Do not compile `127.0.0.1` or `localhost` as the production API base URL.

The Discord application should not be configured as a Public Client for this deployment. The Activity frontend receives an OAuth code through the Embedded App SDK, and the FastAPI backend exchanges it using `DISCORD_CLIENT_SECRET`.

Recommended OAuth scopes:

- bot invite URL: `bot`, `applications.commands`;
- Activity SDK authorization: `identify`, `guilds`, `applications.commands`.

---

## Docker Compose Example

```yaml
version: "3.8"

services:
  bot:
    build: .
    container_name: discord-bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    restart: unless-stopped
    volumes:
      - ./ollama_models:/root/.ollama
    ports:
      - "11434:11434"
```

---

## VPS Deployment

### systemd Service

```ini
[Unit]
Description=OmniBot Bot
After=network.target ollama.service xray-client.service
Wants=xray-client.service

[Service]
Type=simple
User=discord
WorkingDirectory=/opt/omnibot
EnvironmentFile=/opt/omnibot/.env
Environment=DISCORD_PROXY_URL=http://127.0.0.1:10809
ExecStart=/opt/omnibot/venv/bin/python main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Service Management

```bash
sudo systemctl enable omnibot-bot omnibot-activity
sudo systemctl start omnibot-bot omnibot-activity
sudo systemctl status omnibot-bot omnibot-activity
```

### Daily SQLite Backups

```cron
0 3 * * * pg_dump "$DATABASE_URL" > "/opt/discord-bot/backups/omnibot_$(date +\%Y\%m\%d).sql"
```

---

## Project Structure

```text
discord-ai-moderation-bot/
├── core/
├── application/
├── infrastructure/
├── presentation/
├── di/
├── tests/
├── main.py
└── requirements.txt
```

Architecture patterns:

- Clean Architecture;
- Dependency Injection;
- Repository Pattern;
- Service Layer;
- SQLite persistence.

---

## Monitoring

| Command | Purpose |
| --- | --- |
| `/bot uptime` | Bot uptime |
| `/bot ping` | Discord API latency |
| `/ai-stats` | AI moderation statistics |
| `journalctl -u omnibot-bot -f` | Live bot systemd logs |
| `journalctl -u omnibot-activity -f` | Live Activity API logs |

---

## FAQ

### The Bot Cannot See Messages

Enable these intents in the Discord Developer Portal:

- `MESSAGE CONTENT INTENT`;
- `SERVER MEMBERS INTENT`.

Also make sure the Bot has channel permissions:

- View Channels;
- Read Message History;
- Send Messages.

### AI Moderation Does Not Work

Check Ollama:

```bash
systemctl status ollama
ollama pull mistral

curl http://localhost:11434/api/generate \
  -d '{"model":"mistral","prompt":"Hi"}'
```

### The Bot Does Not Assign Roles

The Bot's highest role must be above the roles it assigns. The Bot also needs the `Manage Roles` permission.

### Activity Shows `Session failed` or Empty Panels

Check that:

- the Activity is opened from inside Discord, not a standalone browser tab;
- `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, and `VITE_DISCORD_CLIENT_ID` match the Discord application;
- production frontend was built with empty `VITE_API_BASE_URL`;
- `/sync_roles` has synchronized Discord roles into Activity RBAC;
- `omnibot-activity` can reach Discord through `DISCORD_PROXY_URL` when direct Discord access is blocked;
- Discord snowflake IDs are handled as strings on the frontend.

### `database is locked`

Try enabling WAL mode:

```sql
PRAGMA journal_mode=WAL;
```

Also check that only one Bot instance is writing to the same SQLite database.

---

## Documentation

- [Privacy Policy](https://github.com/6oT9lpa/discord-ai-moderation-bot/blob/main/docs/PRIVACY_POLICY.md)
- [Terms of Service](https://github.com/6oT9lpa/discord-ai-moderation-bot/blob/main/docs/TERMS_OF_SERVICE.md)
- [Knowledge Base](https://github.com/6oT9lpa/discord-ai-moderation-bot/blob/main/docs/KNOWLEDGE_BASE.md)

---

## Testing

```bash
pytest tests -v
pytest --cov=. --cov-report=html
pytest tests/unit/test_ai_moderation.py -v
```

---

## License

MIT License

Copyright (c) 2025-2026 6oT9lpa

---

## Support

- GitHub Issues
- Pull Requests
- Discussions

Author: **6oT9lpa**

<div align="center">

If this project is useful, consider starring the repository.

Built for Discord communities.

</div>
