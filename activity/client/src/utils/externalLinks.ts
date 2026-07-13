import type { DiscordSDK } from "@discord/embedded-app-sdk";

export async function openExternalLink(url: string, discordSdk: DiscordSDK | null): Promise<void> {
  try {
    if (discordSdk) {
      await discordSdk.commands.openExternalLink({ url });
      console.info(`[external-link] Opened through Discord: ${url}`);
      return;
    }

    window.open(url, "_blank", "noopener,noreferrer");
    console.info(`[external-link] Opened in browser: ${url}`);
  } catch (error) {
    console.warn(`[external-link] Discord could not open ${url}`, error);
    window.open(url, "_blank", "noopener,noreferrer");
  }
}

export function shouldHandleExternalClick(event: MouseEvent): boolean {
  return event.button === 0 && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey;
}
