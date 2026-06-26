# Omnibot Discord Activity

This folder contains the real Discord Activity for Omnibot.

Discord Activities are web apps hosted in an iframe and connected to Discord with the Embedded App SDK. The Python bot can keep handling Discord events, while this Activity provides the admin application UI.

## Structure

- `client/` - Vue 3 + Vite + TypeScript frontend loaded inside Discord.
- `server/` - FastAPI backend for OAuth token exchange, admin checks, and welcome configuration API.

## Developer Portal Setup

1. Open the Discord Developer Portal for the Omnibot application.
2. Enable Activities for the app.
3. Add OAuth2 redirect URI: `https://127.0.0.1`.
4. Add an Activity URL Mapping to the public tunnel URL that points to the frontend/backend host.
5. Use the default Activity entry point command, or rename it in the portal.

## Local Run

Create `activity/client/.env` from `.env.example` and set:

```env
VITE_DISCORD_CLIENT_ID=your_discord_application_client_id
VITE_API_BASE_URL=
```

Start the backend:

```bash
python -m uvicorn activity.server.main:app --host 0.0.0.0 --port 8008 --reload
```

Start the frontend:

```bash
cd activity/client
npm install
npm run dev
```

For local UI work, opening `http://localhost:5173` uses a safe preview session and does not contact Discord.
For Discord to load the Activity, expose the frontend/backend host with your production server or tunnel and configure that URL in Activity URL Mappings.

## Required Server Env

The backend reads the existing `.env` from the project root and also needs:

```env
DISCORD_CLIENT_ID=your_discord_application_client_id
DISCORD_CLIENT_SECRET=your_discord_oauth_client_secret
```

Admin access currently uses the Discord `ADMINISTRATOR` permission from the OAuth `guilds` scope. A custom admin-role check can be added after the Activity shell is confirmed.
