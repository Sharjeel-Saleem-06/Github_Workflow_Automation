"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import {
  LayoutDashboard,
  GitPullRequest,
  Sparkles,
  Settings,
  Bot,
} from "lucide-react";
import NotificationBell from "./NotificationBell";

const links = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/reviews", label: "Reviews", icon: GitPullRequest },
  { href: "/prompts", label: "Fix Prompts", icon: Sparkles },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-64 flex-col border-r border-white/5 bg-surface-raised">
      <div className="flex items-center gap-3 border-b border-white/5 px-6 py-5">
        <Bot className="h-8 w-8 text-brand-500" />
        <div>
          <h1 className="text-sm font-bold tracking-tight">AI Review Bot</h1>
          <p className="text-[10px] text-gray-500">Production v1.0</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {links.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-brand-600/20 text-brand-500"
                  : "text-gray-400 hover:bg-white/5 hover:text-gray-200"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-white/5 px-4 py-4">
        <NotificationBell />
      </div>
    </aside>
  );
}
