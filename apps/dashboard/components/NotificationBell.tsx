"use client";

import { useState } from "react";
import { Bell } from "lucide-react";
import { clsx } from "clsx";
import { useNotifications } from "@/hooks/useNotifications";

export default function NotificationBell() {
  const { notifications, unreadCount, clearUnread } = useNotifications();
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => {
          setOpen(!open);
          if (!open) clearUnread();
        }}
        className="relative flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-400 transition hover:bg-white/5 hover:text-gray-200"
      >
        <Bell className="h-4 w-4" />
        Notifications
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute bottom-full left-0 mb-2 w-80 rounded-xl border border-white/10 bg-surface-overlay shadow-2xl">
          <div className="border-b border-white/5 px-4 py-3">
            <h3 className="text-sm font-semibold">Recent Notifications</h3>
          </div>
          <div className="max-h-72 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="px-4 py-6 text-center text-xs text-gray-500">
                No notifications yet. They&apos;ll appear here in real-time when PRs are reviewed.
              </p>
            ) : (
              notifications.slice(0, 10).map((n) => (
                <div
                  key={n.id}
                  className={clsx(
                    "border-b border-white/5 px-4 py-3 transition hover:bg-white/5",
                    !n.is_read && "bg-brand-600/5"
                  )}
                >
                  <p className="text-xs font-medium text-gray-200">{n.title}</p>
                  <p className="mt-0.5 text-[11px] text-gray-500">{n.body}</p>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
