"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import type { NotificationItem } from "@/lib/api";
import { getNotifications, markAllNotificationsRead } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useNotifications() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connectSSE = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = new EventSource(`${API_URL}/notifications/stream`);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const notif: NotificationItem = JSON.parse(event.data);
        if (notif.type === "connected") return;
        setNotifications((prev) => [notif, ...prev].slice(0, 50));
        setUnreadCount((prev) => prev + 1);
      } catch {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      es.close();
      eventSourceRef.current = null;
      reconnectTimeout.current = setTimeout(connectSSE, 5000);
    };
  }, []);

  useEffect(() => {
    getNotifications(1, false)
      .then((data) => {
        setNotifications(data.notifications.slice(0, 50));
        setUnreadCount(data.notifications.filter((n) => !n.is_read).length);
      })
      .catch(() => {});

    connectSSE();

    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close();
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
    };
  }, [connectSSE]);

  const clearUnread = useCallback(() => {
    setUnreadCount(0);
    markAllNotificationsRead().catch(() => {});
    setNotifications((prev) =>
      prev.map((n) => ({ ...n, is_read: true }))
    );
  }, []);

  return { notifications, unreadCount, clearUnread };
}
