<script setup lang="ts">
import RevealOnScroll from "./RevealOnScroll.vue";

const currentYear = new Date().getFullYear();
const githubDocsBase =
  "https://github.com/6oT9lpa/discord-ai-moderation-bot/blob/main/docs";

const legalLinks = [
  { key: "footer.privacy", href: `${githubDocsBase}/PRIVACY_POLICY.md` },
  { key: "footer.terms", href: `${githubDocsBase}/TERMS_OF_SERVICE.md` },
  { key: "footer.knowledge", href: `${githubDocsBase}/KNOWLEDGE_BASE.md` },
];

const knowledgeBaseUrl = `${githubDocsBase}/KNOWLEDGE_BASE.md`;

const productLinks = [
  { key: "footer.welcome", href: `${knowledgeBaseUrl}#5-welcome-alerts` },
  { key: "footer.role_panels", href: `${knowledgeBaseUrl}#4-roles-and-role-panels` },
  { key: "footer.voice_rooms", href: `${knowledgeBaseUrl}#11-dynamic-voice-rooms` },
  { key: "footer.server_stats", href: `${knowledgeBaseUrl}#10-statistics` },
];
const communityLinks = [
  { key: "footer.creator_alerts", href: `${knowledgeBaseUrl}#6-creator-alerts` },
  { key: "footer.dev_blog", href: `${knowledgeBaseUrl}#7-dev-blog` },
  { key: "footer.ai_moderator", href: `${knowledgeBaseUrl}#12-ai-moderation` },
  { key: "footer.logging", href: `${knowledgeBaseUrl}#9-logs-and-audit` },
];
const team = ["6oT9lpa", "Arnetik", "Jimmy"];
</script>

<template>
  <RevealOnScroll tag="footer" class="public-footer">
    <div class="footer-grid">
      <section>
        <span>{{ $t("footer.product") }}</span>
        <a v-for="link in productLinks" :key="link.key" :href="link.href" target="_blank" rel="noreferrer">
          {{ $t(link.key) }}
        </a>
      </section>
      <section>
        <span>{{ $t("footer.legal") }}</span>
        <a v-for="link in legalLinks" :key="link.key" :href="link.href" target="_blank" rel="noreferrer">
          {{ $t(link.key) }}
        </a>
      </section>
      <section>
        <span>{{ $t("footer.community") }}</span>
        <a v-for="link in communityLinks" :key="link.key" :href="link.href" target="_blank" rel="noreferrer">
          {{ $t(link.key) }}
        </a>
      </section>
      <section>
        <span>{{ $t("footer.team") }}</span>
        <strong v-for="member in team" :key="member">{{ member }}</strong>
      </section>
    </div>

    <div class="footer-bottom">
      <p>{{ $t("footer.copyright", { year: currentYear }) }}</p>
      <a class="donate-button" href="https://boosty.to/REPLACE_ME" target="_blank" rel="noreferrer">
        {{ $t("footer.donate") }}
      </a>
    </div>
  </RevealOnScroll>
</template>
