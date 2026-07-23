# Discord Bot Architecture

## Runtime layers

- `presentation/` contains Discord event listeners, slash commands and embeds.
- `application/` contains use cases and policy orchestration.
- `core/` contains domain models and repository/service interfaces.
- `infrastructure/` implements Discord, HTTP, persistence and configuration.
- `activity/` is the Discord Activity server and Vue client.

## AI moderation flow

1. `AiModerationCog` accepts a Discord create/edit event.
2. It builds an `AiModerationRequest` with bounded reply and author-history
   context, then queues it through `AiModerationQueue`.
3. `AiModeratorApiClient` requests classification from the AI moderator.
4. `AiModerationPolicyEnforcer` applies the guild policy. It preserves the
   model proposal separately from the executable action.
5. The cog executes only the resulting plan, records the result and writes an
   audit event. Shadow mode therefore cannot punish members.

## Enforcement modes

- **SHADOW** — records a proposed action and emits `REVIEW` only.
- **LIMITED** — permits WARN and high-confidence, hard-rule DELETE paths.
- **ELEVATED** — requires beta acknowledgement plus explicit switches for
  timeout, kick and ban.

## Activity access

Normal AI settings use Activity RBAC. Private quality metrics additionally
require DM approval with `/labeling ai-metrics`; this is stored separately from
regular Activity access.
