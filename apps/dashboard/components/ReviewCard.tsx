import Link from "next/link";
import { clsx } from "clsx";
import type { ReviewSummary } from "@/lib/api";

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "—";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function ReviewCard({ review }: { review: ReviewSummary }) {
  const verdict = review.verdict?.toLowerCase() || review.status;
  const badgeClass =
    verdict === "approved" || verdict === "completed"
      ? "badge-approved"
      : verdict === "running"
        ? "badge-running"
        : verdict.includes("change")
          ? "badge-critical"
          : "badge-pending";

  return (
    <Link href={`/reviews/${review.id}`} className="card group block transition hover:border-white/10">
      <div className="flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">{review.repo?.full_name}</span>
            <span className="text-xs text-gray-600">#{review.pr?.number}</span>
          </div>
          <h3 className="mt-1 truncate text-sm font-semibold text-gray-200 group-hover:text-white">
            {review.pr?.title || "Untitled PR"}
          </h3>
          <p className="mt-1 text-xs text-gray-500">
            by {review.pr?.author} · {timeAgo(review.started_at)}
          </p>
        </div>
        <span className={clsx("badge ml-3 shrink-0", badgeClass)}>
          {verdict || review.status}
        </span>
      </div>

      <div className="mt-4 flex items-center gap-4 text-xs text-gray-500">
        {review.critical_count > 0 && (
          <span className="text-red-400">{review.critical_count} critical</span>
        )}
        {review.warning_count > 0 && (
          <span className="text-orange-400">{review.warning_count} warnings</span>
        )}
        {review.info_count > 0 && (
          <span className="text-green-400">{review.info_count} info</span>
        )}
        <span className="ml-auto">{review.tokens_used.toLocaleString()} tokens</span>
        <span>${review.cost_usd.toFixed(4)}</span>
      </div>
    </Link>
  );
}
