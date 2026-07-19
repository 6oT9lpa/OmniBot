import { describe, expect, it } from "vitest";
import { buildModerationNotice, deriveModerationEffect, formatRiskScore } from "./moderationOutcome";

describe("deriveModerationEffect", () => {
  it("models deletion and a timeout from the classifier execution plan", () => {
    const effect = deriveModerationEffect({
      risk_score: 87.6,
      action: "DELETE_WARN",
      primary_label: "TOXIC",
      labels: ["TOXIC"],
      execution_plan: ["DELETE", "TIMEOUT"],
    });

    expect(effect).toEqual({ action: "DELETE_WARN", removesMessage: true, restriction: "timeout" });
    expect(formatRiskScore(87.6)).toBe("88%");
    expect(buildModerationNotice({
      risk_score: 87.6,
      action: "DELETE_WARN",
      primary_label: "TOXIC",
      labels: ["TOXIC"],
      execution_plan: ["DELETE", "TIMEOUT"],
    }, effect)).toContain("timed out and cannot write");
  });

  it("keeps a safe message visible and allows further chat", () => {
    const effect = deriveModerationEffect({
      risk_score: 4.2,
      action: "IGNORE",
      primary_label: "SAFE",
      labels: [],
      execution_plan: ["IGNORE"],
    });

    expect(effect).toEqual({ action: "IGNORE", removesMessage: false, restriction: null });
    expect(formatRiskScore(140)).toBe("100%");
  });
});
