"use client";

import { useState } from "react";
import { clsx } from "clsx";
import type { IssueItem } from "@/lib/api";
import PromptCard from "./PromptCard";

const severityOrder: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

export default function IssuesList({ issues }: { issues: IssueItem[] }) {
  const [filter, setFilter] = useState<string>("all");

  const sorted = [...issues].sort(
    (a, b) => (severityOrder[a.severity] ?? 4) - (severityOrder[b.severity] ?? 4)
  );

  const filtered =
    filter === "all" ? sorted : sorted.filter((i) => i.severity === filter);

  const counts = issues.reduce(
    (acc, i) => {
      acc[i.severity] = (acc[i.severity] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-2">
        {["all", "critical", "high", "medium", "low"].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={clsx(
              "rounded-lg px-3 py-1.5 text-xs font-medium transition",
              filter === s
                ? "bg-brand-600 text-white"
                : "bg-white/5 text-gray-400 hover:bg-white/10"
            )}
          >
            {s === "all" ? `All (${issues.length})` : `${s} (${counts[s] || 0})`}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {filtered.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-500">
            {issues.length === 0
              ? "No issues found — LGTM! ✅"
              : "No issues match this filter."}
          </p>
        ) : (
          filtered.map((issue) => (
            <div key={issue.id} className="card">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={clsx(
                        "badge",
                        `badge-${issue.severity}`
                      )}
                    >
                      {issue.severity}
                    </span>
                    <span className="badge bg-white/5 text-gray-400">
                      {issue.agent_type}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-gray-200">{issue.description}</p>
                  <p className="mt-1 text-xs text-gray-500">
                    {issue.file_path}
                    {issue.line_number ? `:${issue.line_number}` : ""}
                  </p>
                </div>
              </div>

              {issue.generated_prompt && (
                <div className="mt-3">
                  <PromptCard prompt={issue.generated_prompt} issueId={issue.id} />
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
