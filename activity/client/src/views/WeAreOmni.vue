<script setup lang="ts">
import { Bot, RadioTower, ShieldCheck } from "@lucide/vue";
import RevealOnScroll from "../components/common/RevealOnScroll.vue";
import FeatureCard from "../components/landing/FeatureCard.vue";
import HeroText from "../components/landing/HeroText.vue";

const features = [
  {
    index: "01",
    title: "AI-Powered Moderation",
    text: "Local AI moderation helps detect spam, ads, invites, bullying, violence and unsafe content while keeping server management efficient.",
  },
  {
    index: "02",
    title: "Creator & Developer Tools",
    text: "Stream alerts, video notifications, Dev Blog publishing and embed builders help creators and developers share updates beautifully.",
  },
  {
    index: "03",
    title: "Operational Control",
    text: "Role panels, welcome flows, status checks, statistics and access rules live in one focused control surface.",
  },
  {
    index: "04",
    title: "Dynamic Voice Rooms",
    text: "Temporary voice channels with owner controls for naming, user limits, lock states and ownership transfer, with cleanup when rooms go empty.",
  },
  {
    index: "05",
    title: "Server Statistics & Insights",
    text: "Track message activity, voice time, top members, channel trends and member movement in one clear dashboard.",
  },
  {
    index: "06",
    title: "Logging & Audit Trail",
    text: "Message edits, deletions, role changes and moderation actions are logged with configurable retention for transparent admin history.",
  },
];
</script>

<template>
  <main class="public-page">
    <RevealOnScroll>
      <HeroText
        kicker="OmniBot Activity"
        title="BE A PART OF SOMETHING MARVELLOUS"
        body="Omni is a modular Discord bot that combines AI moderation, automation, creator tools, analytics and elegant server management in one ecosystem."
      />
    </RevealOnScroll>

    <section class="feature-grid" aria-label="Why Omni">
      <RevealOnScroll
        v-for="feature in features"
        :key="feature.index"
        :delay="Number(feature.index) * 45"
      >
        <FeatureCard
          :index="feature.index"
          :title="feature.title"
          :text="feature.text"
        />
      </RevealOnScroll>
    </section>

    <RevealOnScroll tag="section" class="showcase-band">
      <div class="showcase-copy">
        <span class="eyebrow">Control without clutter</span>
        <h2>One Activity. Many workspaces. Zero token leaks.</h2>
        <p>
          Control without clutter. Every module, from roles and logs to moderation and
          stats, lives in one clean dashboard instead of scattered commands. Admins see
          what changed, who has access and what needs attention without digging through
          channel history.
        </p>
      </div>
      <div class="showcase-stack" aria-hidden="true">
        <div><ShieldCheck :size="20" /> Permission Matrix</div>
        <div><RadioTower :size="20" /> Creator Alerts</div>
        <div><Bot :size="20" /> AI Metrics</div>
      </div>
    </RevealOnScroll>
  </main>
</template>
