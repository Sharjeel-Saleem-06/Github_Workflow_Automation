"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Clock, Cpu, DollarSign, MessageSquare } from "lucide-react";
import { getReview, type ReviewDetail } from "@/lib/api";
import IssuesList from "@/components/IssuesList";
import PromptCard from "@/components/PromptCard";

function renderMarkdownSafe(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/^### (.+)$/gm, '<h3 class="text-base font-semibold mt-4 mb-1">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-lg font-bold mt-5 mb-2">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="text-xl font-bold mt-6 mb-2">$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, '<code class="rounded bg-white/10 px-1 py-0.5 text-xs">$1</code>')
    .replace(/^- (.+)$/gm, '<li class="ml-4 list-disc">$1</li>')
    .replace(/\n{2,}/g, '<br/><br/>')
    .replace(/\n/g, "<br/>");
}

export default function ReviewDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [review, setReview] = useState<ReviewDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"issues" | "summary" | "senior">("issues");

  useEffect(() => {
    getReview(id)
      .then(setReview)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  if (!review) {
    return <p className="py-16 text-center text-gray-500">Review not found.</p>;
  }

  return (
    <div>
      <Link
        href="/reviews"
        className="mb-4 inline-flex items-center gap-1 text-sm text-gray-500 transition hover:text-gray-300"
      >
        <ArrowLeft className="h-3 w-3" /> Back to reviews
      </Link>

      <div className="card mb-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs text-gray-500">{review.repo?.full_name}</p>
            <h1 className="mt-1 text-xl font-bold">
              #{review.pr?.number} — {review.pr?.title}
            </h1>
            <p className="mt-1 text-sm text-gray-500">by {review.pr?.author}</p>
          </div>
          <span
            className={`badge text-sm ${
              review.verdict?.includes("APPROVED") ? "badge-approved" : "badge-critical"
            }`}
          >
            {review.verdict || review.status}
          </span>
        </div>

        <div className="mt-4 flex flex-wrap gap-6 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {review.completed_at
              ? `Completed ${new Date(review.completed_at).toLocaleString()}`
              : `Started ${review.started_at ? new Date(review.started_at).toLocaleString() : "—"}`}
          </span>
          <span className="flex items-center gap-1">
            <Cpu className="h-3 w-3" />
            {review.tokens_used.toLocaleString()} tokens
          </span>
          <span className="flex items-center gap-1">
            <DollarSign className="h-3 w-3" />
            ${review.cost_usd.toFixed(4)}
          </span>
          <span className="flex items-center gap-1">
            <MessageSquare className="h-3 w-3" />
            {review.issues.length} issues
          </span>
        </div>
      </div>

      <div className="mb-6 flex gap-2 border-b border-white/5 pb-2">
        {(["issues", "summary", "senior"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-t-lg px-4 py-2 text-sm font-medium transition ${
              tab === t
                ? "bg-surface-raised text-white"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {t === "issues"
              ? `Issues (${review.issues.length})`
              : t === "summary"
                ? "Summary"
                : `Senior Feedback (${review.senior_comments.length})`}
          </button>
        ))}
      </div>

      {tab === "issues" && <IssuesList issues={review.issues} />}

      {tab === "summary" && (
        <div className="card prose prose-invert max-w-none">
          {review.final_summary ? (
            <div
              dangerouslySetInnerHTML={{
                __html: renderMarkdownSafe(review.final_summary),
              }}
            />
          ) : (
            <p className="text-gray-500">No summary available.</p>
          )}
        </div>
      )}

      {tab === "senior" && (
        <div className="space-y-4">
          {review.senior_comments.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-500">
              No senior feedback processed for this PR yet.
            </p>
          ) : (
            review.senior_comments.map((sc) => (
              <div key={sc.id} className="card">
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <span className="font-medium text-gray-300">@{sc.reviewer_login}</span>
                  {sc.file_path && <span>· {sc.file_path}</span>}
                </div>
                <blockquote className="mt-2 border-l-2 border-brand-600 pl-3 text-sm text-gray-400 italic">
                  {sc.body}
                </blockquote>
                {sc.guidance && (
                  <div className="mt-3">
                    <p className="text-xs font-medium text-gray-400">Guidance:</p>
                    <p className="mt-1 text-sm text-gray-300">{sc.guidance}</p>
                  </div>
                )}
                {sc.generated_prompt && (
                  <div className="mt-3">
                    <p className="mb-2 text-xs font-medium text-gray-400">Fix Prompt:</p>
                    <PromptCard prompt={sc.generated_prompt} />
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
