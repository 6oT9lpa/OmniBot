<script setup lang="ts">
const currentYear = new Date().getFullYear();
const githubDocsBase =
  "https://github.com/6oT9lpa/discord-ai-moderation-bot/blob/main/docs";

const legalLinks = [
  { label: "Privacy Policy", href: `${githubDocsBase}/PRIVACY_POLICY.md` },
  { label: "Terms of Service", href: `${githubDocsBase}/TERMS_OF_SERVICE.md` },
  { label: "Knowledge Base", href: `${githubDocsBase}/KNOWLEDGE_BASE.md` },
];

const productLinks = ["Welcome", "Role Panels", "Voice Rooms", "Server Stats"];
const communityLinks = ["Creator Alerts", "Dev Blog", "AI Moderation", "Logging"];
const team = ["6oT9lpa", "Arnetik", "Jimmy"];
</script>

<template>
  <footer class="public-footer">
    <div class="footer-grid">
      <section>
        <span>Product</span>
        <a v-for="item in productLinks" :key="item" href="/about">{{ item }}</a>
      </section>
      <section>
        <span>Legal</span>
        <a v-for="link in legalLinks" :key="link.label" :href="link.href" target="_blank" rel="noreferrer">
          {{ link.label }}
        </a>
      </section>
      <section>
        <span>Community</span>
        <a v-for="item in communityLinks" :key="item" href="/about">{{ item }}</a>
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
  </footer>
</template>
