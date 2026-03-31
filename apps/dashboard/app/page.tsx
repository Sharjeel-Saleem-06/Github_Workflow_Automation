"use client";

import { useEffect, useState } from "react";
import {
  GitPullRequest,
  AlertTriangle,
  DollarSign,
  Zap,
  TrendingUp,
  Shield,
  AlertCircle,
} from "lucide-react";
import { getStats, type DashboardStats, type ReviewSummary } from "@/lib/api";
import ReviewCard from "@/components/ReviewCard";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Overview of your autonomous AI code reviews
        </p>
      </div>

      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={<GitPullRequest className="h-5 w-5" />}
          label="Total Reviews"
          value={stats ? String(stats.total_reviews) : "—"}
          color="text-brand-500"
        />
        <StatCard
          icon={<AlertTriangle className="h-5 w-5" />}
          label="Critical Issues"
          value={stats ? String(stats.issues_by_severity.critical) : "—"}
          color="text-red-400"
        />
        <StatCard
          icon={<Shield className="h-5 w-5" />}
          label="Warnings"
          value={stats ? String(stats.issues_by_severity.warning) : "—"}
          color="text-yellow-400"
        />
        <StatCard
          icon={<DollarSign className="h-5 w-5" />}
          label="Total Cost"
          value={stats ? `$${stats.total_cost_usd.toFixed(4)}` : "—"}
          color="text-emerald-400"
        />
      </div>

      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard
          icon={<Zap className="h-5 w-5" />}
          label="Total Tokens Used"
          value={stats ? stats.total_tokens.toLocaleString() : "—"}
          color="text-purple-400"
        />
        <StatCard
          icon={<GitPullRequest className="h-5 w-5" />}
          label="Repos Connected"
          value={stats ? String(stats.total_repos) : "—"}
          color="text-blue-400"
        />
        <StatCard
          icon={<AlertCircle className="h-5 w-5" />}
          label="Total Issues Found"
          value={stats ? String(stats.total_issues) : "—"}
          color="text-orange-400"
        />
      </div>

      <div className="flex items-center gap-2 mb-4">
        <TrendingUp className="h-4 w-4 text-gray-500" />
        <h2 className="text-lg font-semibold">Recent Reviews</h2>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
        </div>
      ) : !stats || stats.recent_reviews.length === 0 ? (
        <div className="card py-16 text-center">
          <GitPullRequest className="mx-auto h-12 w-12 text-gray-600" />
          <h3 className="mt-4 text-sm font-semibold text-gray-400">No reviews yet</h3>
          <p className="mt-1 text-xs text-gray-500">
            Install the GitHub App on a repo and open a PR to trigger the first review.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {stats.recent_reviews.map((r) => (
            <ReviewCard key={r.id} review={r} />
          ))}
        </div>
      )}
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="card flex items-center gap-4">
      <div className={`rounded-lg bg-white/5 p-2.5 ${color}`}>{icon}</div>
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-xl font-bold tracking-tight">{value}</p>
      </div>
    </div>
  );
}
