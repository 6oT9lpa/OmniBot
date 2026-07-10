from __future__ import annotations

import re
from collections.abc import Mapping
from urllib.parse import urlparse

from application.dto.ai_moderation_decision import AiModerationDecision
from application.dto.ai_moderation_request import AiModerationRequest
from core.domain.ai_moderation_action import AiModerationAction
from core.domain.ai_moderation_guild_policy import AiModerationGuildPolicy
from core.domain.ai_moderation_label_policy import AiModerationLabelPolicy
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class AiModerationPolicyEnforcer:
    _ACTION_RANK = {
        AiModerationAction.IGNORE: 0,
        AiModerationAction.LOG: 1,
        AiModerationAction.REVIEW: 2,
        AiModerationAction.WARN: 3,
        AiModerationAction.DELETE: 4,
        AiModerationAction.DELETE_WARN: 5,
        AiModerationAction.TIMEOUT: 6,
        AiModerationAction.KICK: 7,
        AiModerationAction.BAN: 8,
    }

    def apply(
        self,
        request: AiModerationRequest,
        decision: AiModerationDecision,
        raw_policy: Mapping[str, object],
    ) -> AiModerationDecision:
        policy = AiModerationGuildPolicy.model_validate(raw_policy)
        configured_action = self._configured_action(policy, decision)
        blacklist_action = self._blacklist_action(policy, request.raw_text)
        domain_action = self._unapproved_domain_action(policy, request.raw_text)
        action = max(
            (candidate for candidate in (configured_action, blacklist_action, domain_action) if candidate is not None),
            key=lambda candidate: self._ACTION_RANK[candidate],
            default=AiModerationAction(decision.action),
        )
        primary_label = "BLACKLIST" if blacklist_action is not None else decision.primary_label
        labels = decision.labels if blacklist_action is None else tuple(dict.fromkeys((*decision.labels, "BLACKLIST")))
        execution_plan = self._execution_plan(action)
        if action.value == decision.action and primary_label == decision.primary_label and execution_plan == decision.execution_plan:
            return decision
        logger.info(
            "Applied guild AI moderation policy guild_id=%s message_id=%s action=%s",
            request.guild_id,
            request.message_id,
            action.value,
        )
        return decision.model_copy(
            update={
                "action": action.value,
                "primary_label": primary_label,
                "labels": labels,
                "execution_plan": execution_plan,
            }
        )

    def validate(self, raw_policy: Mapping[str, object]) -> dict[str, object]:
        return AiModerationGuildPolicy.model_validate(raw_policy).model_dump(mode="json")

    def _configured_action(self, policy: AiModerationGuildPolicy, decision: AiModerationDecision) -> AiModerationAction | None:
        configured_actions = [
            self._apply_label_rule(rule, decision)
            for label in decision.labels
            if (rule := policy.labels.get(label.upper())) is not None
        ]
        return max(configured_actions, key=lambda action: self._ACTION_RANK[action], default=None)

    def _apply_label_rule(self, rule: AiModerationLabelPolicy, decision: AiModerationDecision) -> AiModerationAction:
        if decision.risk_score < rule.risk_threshold:
            return AiModerationAction.LOG
        current_action = AiModerationAction(decision.action)
        if self._ACTION_RANK[current_action] < self._ACTION_RANK[rule.min_action]:
            return rule.min_action
        if self._ACTION_RANK[current_action] > self._ACTION_RANK[rule.max_action]:
            return rule.max_action
        return current_action

    def _blacklist_action(self, policy: AiModerationGuildPolicy, text: str) -> AiModerationAction | None:
        normalized_text = text.casefold()
        for word in policy.blacklist_words:
            if re.search(rf"(?<!\\w){re.escape(word)}(?!\\w)", normalized_text):
                return policy.blacklist_action
        return None

    def _unapproved_domain_action(self, policy: AiModerationGuildPolicy, text: str) -> AiModerationAction | None:
        if not policy.allowed_domains:
            return None
        domains = tuple(
            parsed.hostname.casefold()
            for raw_url in re.findall(r"https?://[^\s<>()]+", text, flags=re.IGNORECASE)
            if (parsed := urlparse(raw_url)).hostname
        )
        if any(not self._is_allowed_domain(domain, policy.allowed_domains) for domain in domains):
            return policy.unapproved_domain_action
        return None

    def _is_allowed_domain(self, domain: str, allowed_domains: tuple[str, ...]) -> bool:
        return any(domain == allowed or domain.endswith(f".{allowed}") for allowed in allowed_domains)

    def _execution_plan(self, action: AiModerationAction) -> tuple[str, ...]:
        if action == AiModerationAction.DELETE_WARN:
            return (AiModerationAction.DELETE.value, AiModerationAction.WARN.value)
        return (action.value,)
