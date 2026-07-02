# Privacy Policy for OmniBot

**Effective Date:** June 18, 2026  
**Last Updated:** July 2, 2026

This Privacy Policy explains what data OmniBot processes, why it is processed, how it is stored, and how deletion or access requests can be made.

OmniBot operates inside Discord servers and uses the Discord API. Use of OmniBot also remains subject to the [Discord Terms of Service](https://discord.com/terms), [Discord Privacy Policy](https://discord.com/privacy), Discord Developer Terms, and Discord Developer Policy.

## 1. Controller and Contact

Bot operator: **6oT9lpa / OmniBot project team**.  
Contact: **Discord Support Server: https://discord.gg/wUb3Js2wzt**.

Server administrators are also responsible for how OmniBot is configured on their server: which modules are enabled, which channels receive logs, which roles can access Activity tabs, and who can view moderation or audit information.

## 2. Data Processed By Current Modules

OmniBot processes only data needed for configured features.

### 2.1 Server and Configuration Data

OmniBot may store:

- Discord server ID;
- configured channel IDs for welcome, logs, stream announcements, Dev Blog, and other purposes;
- configured role IDs for Activity access, stream ping, Dev Blog ping, autorole, and role panels;
- role names, colors, positions, and metadata used for Activity RBAC;
- bot runtime settings such as prefix, status, retention, and log level;
- welcome message configuration;
- role panel configuration;
- voice room trigger/channel configuration.

### 2.2 User and Member Data

OmniBot may store or process:

- Discord user ID;
- username, display name, avatar URL, and role IDs where needed for embeds, audit logs, and permissions;
- Activity OAuth user profile and guild membership data while opening the Activity panel;
- moderation target and moderator IDs;
- voice room owner/admin/member IDs;
- statistics counters such as messages, voice time, warnings, joins, and leaves.

### 2.3 Message and Log Data

When logging or moderation modules are enabled, OmniBot may process:

- message ID;
- author ID;
- channel ID;
- message content for logged message events;
- edited or deleted message content when available;
- timestamps;
- event type;
- moderation actions, punishment reasons, and durations.

Message logs are used for server administration, moderation review, audit, and statistics. OmniBot does not intentionally read private direct messages unless a user directly interacts with the bot in DMs or Discord sends an interaction event to the bot.

### 2.4 Creator Alerts and External Platform Data

For Creator Alerts, OmniBot may store:

- creator Discord user ID;
- platform: Twitch, YouTube, or Kick;
- channel URL;
- optional external channel ID;
- channel name;
- alert kind;
- embed title and description templates;
- button label;
- color;
- ping role ID;
- active/paused state;
- last announced event ID and last checked time.

OmniBot may contact Twitch, YouTube, or Kick APIs/public endpoints only for configured monitoring and publication features. Those services have their own policies.

### 2.5 Dev Blog Data

For Dev Blog, OmniBot may store:

- post title;
- content;
- embed descriptions, colors, and image URLs;
- draft/published status;
- channel ID and Discord message ID;
- author ID;
- payload used for publication.

### 2.6 Activity Panel Data

When a user opens the Discord Activity panel, OmniBot processes:

- Discord OAuth code;
- backend-exchanged Discord access token for the current Activity session;
- Discord user profile;
- current guild ID;
- role/membership information needed for Activity access;
- Activity audit events created by admin actions.

The Discord client secret is handled only by the backend. It must not be placed in frontend code.

### 2.7 Technical Logs

OmniBot writes technical logs to diagnose errors and keep services stable. Logs may contain:

- timestamp;
- module name;
- log level;
- error details;
- Discord IDs involved in the event;
- request path and status for Activity API requests.

## 3. Planned AI Moderation

AI moderation is planned as a future module. It is not described here as a currently enabled production feature.

When released, it is expected to use local/self-hosted checks by default. The Privacy Policy should be updated again before or when AI moderation is enabled in production.

## 4. Data We Do Not Intentionally Collect

OmniBot does not intentionally collect:

- Discord passwords;
- user tokens;
- payment details;
- precise geolocation;
- biometric data;
- voice channel audio recordings;
- browser fingerprints for tracking;
- Discord client secrets in frontend code.

## 5. How Data Is Used

Data is used to:

- execute slash commands, buttons, menus, and modals;
- authorize Activity panel access;
- determine which Activity tabs a user may access;
- synchronize roles and manage role panels;
- send welcome messages;
- log server and moderation events;
- show statistics;
- operate voice rooms;
- publish Creator Alerts and Dev Blog posts;
- prevent duplicate stream announcements;
- maintain audit trails;
- diagnose errors and improve service stability.

## 6. Data Sharing and Third Parties

We do not sell or rent user data.

Data may be processed by or visible to:

- Discord, because OmniBot operates through Discord APIs;
- the hosting provider or VPS where OmniBot runs;
- PostgreSQL or SQLite storage configured by the operator;
- Twitch, YouTube, and Kick when Creator Alerts are configured;
- proxy infrastructure such as VLESS/Xray when Discord traffic is routed through it;
- server administrators and moderators with access to logs or Activity panels;
- authorities when legally required.

## 7. Storage and Retention

Production deployments may use PostgreSQL. Local deployments may use SQLite.

Default retention:

- message logs: 30 days unless changed by configuration;
- expired punishment history: 365 days unless changed by configuration;
- cleanup interval: approximately every 6 hours unless changed by configuration;
- server settings, Activity RBAC, role panels, welcome settings, Creator Alerts, and Dev Blog drafts: kept while the server uses the bot or until changed/deleted;
- technical logs: kept until log rotation or manual cleanup.

Some data may be retained longer where needed for security, abuse investigation, backups, legal compliance, or recovery.

## 8. Access, Correction, and Deletion

Users and server administrators may request:

- access to data associated with a user ID or server ID;
- correction of incorrect settings;
- deletion of user data;
- deletion of server data after bot removal;
- disabling modules that collect additional data.

To request this, contact the project support channel and include:

- Discord user ID;
- server ID;
- the requested action: export, correct, delete, or disable.

We may verify that the requester is the relevant user or a server administrator. Requests are usually reviewed within 30 days.

## 9. Security

Security measures include:

- keeping tokens and API keys in server `.env`;
- backend-only OAuth code exchange;
- Discord permission checks;
- Activity RBAC checks;
- database access restricted to the deployment environment;
- log rotation;
- avoiding frontend storage of secrets;
- optional proxy configuration via server environment.

No system is perfectly secure. Report suspected leaks or vulnerabilities through the contact channel.

## 10. Children and Minimum Age

OmniBot is not intended for users below the minimum age required by Discord and local law.

## 11. Changes

This policy may be updated when features, infrastructure, laws, or Discord requirements change. Material updates will be reflected by the Last Updated date.

## 12. Contact

Privacy, deletion, and security questions: **https://discord.gg/wUb3Js2wzt**.

Include the server ID and user ID where relevant.
