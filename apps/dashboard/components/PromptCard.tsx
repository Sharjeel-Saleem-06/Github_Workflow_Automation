"use client";

import { useState } from "react";
import { Copy, Check, ThumbsUp, ThumbsDown } from "lucide-react";
import { ratePrompt } from "@/lib/api";

interface PromptCardProps {
  prompt: string;
  issueId?: string;
}

export default function PromptCard({ prompt, issueId }: PromptCardProps) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"helpful" | "not_helpful" | null>(null);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFeedback = async (helpful: boolean) => {
    const newState = helpful ? "helpful" : "not_helpful";
    if (feedback === newState) return;
    setFeedback(newState as "helpful" | "not_helpful");
    if (issueId) {
      try {
        await ratePrompt(issueId, helpful);
      } catch {
        // silently fail — feedback is best-effort
      }
    }
  };

  return (
    <div className="group relative rounded-lg border border-white/5 bg-surface p-4">
      <div className="absolute right-3 top-3 flex items-center gap-1">
        {issueId && (
          <>
            <button
              onClick={() => handleFeedback(true)}
              className={`rounded-md p-1.5 transition ${
                feedback === "helpful"
                  ? "bg-green-500/20 text-green-400"
                  : "bg-white/5 text-gray-500 opacity-0 hover:bg-white/10 hover:text-green-400 group-hover:opacity-100"
              }`}
              title="Helpful"
            >
              <ThumbsUp className="h-3 w-3" />
            </button>
            <button
              onClick={() => handleFeedback(false)}
              className={`rounded-md p-1.5 transition ${
                feedback === "not_helpful"
                  ? "bg-red-500/20 text-red-400"
                  : "bg-white/5 text-gray-500 opacity-0 hover:bg-white/10 hover:text-red-400 group-hover:opacity-100"
              }`}
              title="Not helpful"
            >
              <ThumbsDown className="h-3 w-3" />
            </button>
          </>
        )}
        <button
          onClick={handleCopy}
          className="rounded-md bg-white/5 p-1.5 text-gray-500 opacity-0 transition hover:bg-white/10 hover:text-gray-300 group-hover:opacity-100"
          title="Copy to clipboard"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-green-400" /> : <Copy className="h-3.5 w-3.5" />}
        </button>
      </div>
      <p className="text-xs leading-relaxed text-gray-400 whitespace-pre-wrap font-mono pr-20">
        {prompt}
      </p>
    </div>
  );
}
