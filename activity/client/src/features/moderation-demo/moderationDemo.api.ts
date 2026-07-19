import { apiRequest } from "../../api/client";
import type { ModerationDemoDecision } from "./types";

export function classifyDemoMessage(message: string): Promise<ModerationDemoDecision> {
  return apiRequest<ModerationDemoDecision>("/api/public/moderation-demo/classify", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}
