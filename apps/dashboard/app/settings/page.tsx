"use client";

import { Bot, ExternalLink } from "lucide-react";

export default function SettingsPage() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-gray-500">
          Configuration for your AI Code Review Bot
        </p>
      </div>

      <div className="space-y-6">
        <div className="card">
          <h2 className="mb-4 text-lg font-semibold">GitHub App Setup</h2>
          <div className="space-y-4 text-sm text-gray-400">
            <div>
              <h3 className="font-medium text-gray-300">1. Create a GitHub App</h3>
              <p className="mt-1">
                Go to{" "}
                <a
                  href="https://github.com/settings/apps/new"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-brand-500 hover:underline"
                >
                  GitHub Settings → Developer Settings → New GitHub App
                  <ExternalLink className="h-3 w-3" />
                </a>
              </p>
            </div>
            <div>
              <h3 className="font-medium text-gray-300">2. Required Permissions</h3>
              <ul className="mt-1 list-inside list-disc space-y-1">
                <li>Pull requests: Read &amp; Write</li>
                <li>Contents: Read</li>
                <li>Issues: Read &amp; Write</li>
                <li>Metadata: Read</li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium text-gray-300">3. Subscribe to Events</h3>
              <ul className="mt-1 list-inside list-disc space-y-1">
                <li>Pull request</li>
                <li>Pull request review</li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium text-gray-300">4. Webhook URL</h3>
              <code className="mt-1 block rounded bg-surface px-3 py-2 text-xs text-gray-300">
                https://your-api-domain.com/webhooks/github
              </code>
            </div>
            <div>
              <h3 className="font-medium text-gray-300">5. Generate Private Key</h3>
              <p className="mt-1">
                Download the PEM file, base64-encode it, and set as{" "}
                <code className="rounded bg-surface px-1.5 py-0.5 text-xs">GITHUB_APP_PRIVATE_KEY</code>{" "}
                env var.
              </p>
              <code className="mt-2 block rounded bg-surface px-3 py-2 text-xs text-gray-300">
                cat your-app.pem | base64 | tr -d &apos;\n&apos;
              </code>
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="mb-4 text-lg font-semibold">Agent Configuration</h2>
          <div className="space-y-3">
            {[
              { name: "Color & Constants", desc: "Detects hardcoded colors, magic numbers, missing design tokens" },
              { name: "Logic & Bugs", desc: "Finds null checks, off-by-one errors, race conditions" },
              { name: "Best Practices", desc: "SRP, DRY, deep nesting, missing error handling" },
              { name: "Security", desc: "OWASP Top 10, hardcoded secrets, injection vulnerabilities" },
            ].map((agent) => (
              <div
                key={agent.name}
                className="flex items-center justify-between rounded-lg border border-white/5 bg-surface px-4 py-3"
              >
                <div>
                  <p className="text-sm font-medium text-gray-200">{agent.name}</p>
                  <p className="text-xs text-gray-500">{agent.desc}</p>
                </div>
                <span className="badge badge-approved">Active</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2 className="mb-4 text-lg font-semibold">About</h2>
          <div className="flex items-center gap-3">
            <Bot className="h-10 w-10 text-brand-500" />
            <div>
              <p className="text-sm font-semibold">AI Code Review Bot v1.0</p>
              <p className="text-xs text-gray-500">
                Autonomous PR review powered by Claude · 4 specialized agents ·
                Real-time notifications · Fix prompts library
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
