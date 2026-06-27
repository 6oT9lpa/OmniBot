<script setup lang="ts">
import RevealOnScroll from "./RevealOnScroll.vue";

const currentYear = new Date().getFullYear();
const githubDocsBase =
  "https://github.com/6oT9lpa/discord-ai-moderation-bot/blob/main/docs";

const legalLinks = [
  { label: "Privacy Policy", href: `${githubDocsBase}/PRIVACY_POLICY.md` },
  { label: "Terms of Service", href: `${githubDocsBase}/TERMS_OF_SERVICE.md` },
  { label: "Knowledge Base", href: `${githubDocsBase}/KNOWLEDGE_BASE.md` },
];

const knowledgeBaseUrl = `${githubDocsBase}/KNOWLEDGE_BASE.md`;

const productLinks = [
  { label: "Welcome", href: `${knowledgeBaseUrl}#welcome-module` },
  { label: "Role Panels", href: `${knowledgeBaseUrl}#role-panels` },
  { label: "Voice Rooms", href: `${knowledgeBaseUrl}#voice-rooms` },
  { label: "Server Stats", href: `${knowledgeBaseUrl}#server-stats` },
];
const communityLinks = [
  { label: "Creator Alerts", href: `${knowledgeBaseUrl}#creator-alerts` },
  { label: "Dev Blog", href: `${knowledgeBaseUrl}#dev-blog` },
  { label: "AI Moderation", href: `${knowledgeBaseUrl}#ai-moderation` },
  { label: "Logging", href: `${knowledgeBaseUrl}#logging` },
];
const team = ["6oT9lpa", "Arnetik", "Jimmy"];
</script>

<template>
  <RevealOnScroll tag="footer" class="public-footer">
    <div class="footer-grid">
      <section>
        <span>Product</span>
        <a v-for="link in productLinks" :key="link.label" :href="link.href" target="_blank" rel="noreferrer">
          {{ link.label }}
        </a>
      </section>
      <section>
        <span>Legal</span>
        <a v-for="link in legalLinks" :key="link.label" :href="link.href" target="_blank" rel="noreferrer">
          {{ link.label }}
        </a>
      </section>
      <section>
        <span>Community</span>
        <a v-for="link in communityLinks" :key="link.label" :href="link.href" target="_blank" rel="noreferrer">
          {{ link.label }}
        </a>
      </section>
      <section>
        <span>Team</span>
        <strong v-for="member in team" :key="member">{{ member }}</strong>
      </section>
    </div>

    <div class="footer-bottom">
      <p>&copy; 2025-{{ currentYear }} OmniBot. Built for Discord communities.</p>
      <a class="donate-button" href="https://boosty.to/REPLACE_ME" target="_blank" rel="noreferrer">
        Donate
      </a>
    </div>
  </RevealOnScroll>
</template>
