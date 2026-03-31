"use client";

import { useEffect, useState, useCallback } from "react";
import { Search, Filter, ChevronLeft, ChevronRight } from "lucide-react";
import { getPrompts, type PromptItem } from "@/lib/api";
import PromptCard from "@/components/PromptCard";
import { clsx } from "clsx";

const agents = ["all", "color_constants", "logic_bugs", "best_practices", "security"];
const severities = ["all", "critical", "high", "medium", "low"];

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<PromptItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [agentFilter, setAgentFilter] = useState("all");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const limit = 15;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getPrompts({
        page,
        limit,
        agent: agentFilter === "all" ? undefined : agentFilter,
        severity: severityFilter === "all" ? undefined : severityFilter,
        search: search || undefined,
      });
      setPrompts(data.prompts);
      setTotal(data.total);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [page, agentFilter, severityFilter, search]);

  useEffect(() => {
    const timer = setTimeout(load, search ? 400 : 0);
    return () => clearTimeout(timer);
  }, [load, search]);

  const totalPages = Math.ceil(total / limit);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">Fix Prompts Library</h1>
        <p className="mt-1 text-sm text-gray-500">
          {total} prompts — copy any prompt and paste into Claude to get the fix
        </p>
      </div>

      <div className="card mb-6">
        <div className="flex flex-col gap-4 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              placeholder="Search prompts, files, descriptions…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-lg border border-white/10 bg-surface py-2 pl-9 pr-4 text-sm text-gray-200 placeholder-gray-600 outline-none transition focus:border-brand-600"
            />
          </div>

          <div className="flex gap-2">
            <div className="flex items-center gap-1">
              <Filter className="h-3 w-3 text-gray-500" />
              <select
                value={agentFilter}
                onChange={(e) => {
                  setAgentFilter(e.target.value);
                  setPage(1);
                }}
                className="rounded-lg border border-white/10 bg-surface px-3 py-2 text-xs text-gray-300 outline-none"
              >
                {agents.map((a) => (
                  <option key={a} value={a}>
                    {a === "all" ? "All Agents" : a.replace("_", " ")}
                  </option>
                ))}
              </select>
            </div>

            <select
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-white/10 bg-surface px-3 py-2 text-xs text-gray-300 outline-none"
            >
              {severities.map((s) => (
                <option key={s} value={s}>
                  {s === "all" ? "All Severity" : s}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
        </div>
      ) : prompts.length === 0 ? (
        <p className="py-16 text-center text-sm text-gray-500">
          No prompts match your filters.
        </p>
      ) : (
        <div className="space-y-4">
          {prompts.map((p) => (
            <div key={p.id} className="card">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className={clsx("badge", `badge-${p.severity}`)}>
                  {p.severity}
                </span>
                <span className="badge bg-white/5 text-gray-400">
                  {p.agent_type.replace("_", " ")}
                </span>
                <span className="text-xs text-gray-600">
                  {p.repo}#{p.pr_number}
                </span>
                <span className="text-xs text-gray-600">
                  {p.file_path}
                  {p.line_number ? `:${p.line_number}` : ""}
                </span>
              </div>
              <p className="mb-3 text-sm text-gray-300">{p.description}</p>
              <PromptCard prompt={p.generated_prompt} issueId={p.id} />
            </div>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-center gap-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded-lg bg-white/5 p-2 text-gray-400 transition hover:bg-white/10 disabled:opacity-30"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-sm text-gray-500">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="rounded-lg bg-white/5 p-2 text-gray-400 transition hover:bg-white/10 disabled:opacity-30"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}
