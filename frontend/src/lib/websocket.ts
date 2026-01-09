/**
 * WebSocket connection manager with auto-reconnect.
 * Uses cookie-based authentication via a token endpoint.
 */

import type { WebSocketEvent } from "@/types/feedback";

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

type EventHandler = (event: WebSocketEvent) => void;

// Fetch a WebSocket token from the backend (authenticated via cookies)
async function fetchWsToken(): Promise<string | null> {
  try {
    const response = await fetch("/api/v1/auth/ws-token", {
      credentials: "include",
    });
    if (!response.ok) {
      console.warn("WebSocket: Failed to get WS token", response.status);
      return null;
    }
    const data = await response.json();
    return data.token;
  } catch (error) {
    console.error("WebSocket: Error fetching WS token", error);
    return null;
  }
}

class WebSocketManager {
  private socket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private handlers: Set<EventHandler> = new Set();
  private pingInterval: NodeJS.Timeout | null = null;
  private endpoint: string = "";
  private isConnecting = false;

  connect(endpoint: "/ws/live" | `/ws/analysis/${string}`): void {
    if (this.socket?.readyState === WebSocket.OPEN && this.endpoint === endpoint) {
      return; // Already connected to this endpoint
    }

    // Close existing connection if different endpoint
    if (this.socket) {
      this.disconnect();
    }

    this.endpoint = endpoint;
    this.establishConnection();
  }

  private async establishConnection(): Promise<void> {
    if (this.isConnecting) return;
    this.isConnecting = true;

    const token = await fetchWsToken();
    if (!token) {
      console.warn("WebSocket: No access token available");
      this.isConnecting = false;
      return;
    }

    const url = `${WS_BASE_URL}/api/v1${this.endpoint}?token=${token}`;

    try {
      this.socket = new WebSocket(url);

      this.socket.onopen = () => {
        console.log("WebSocket connected");
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.startPing();
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketEvent;
          this.handlers.forEach((handler) => handler(data));
        } catch (error) {
          console.error("WebSocket: Failed to parse message", error);
        }
      };

      this.socket.onclose = (event) => {
        console.log("WebSocket closed", event.code, event.reason);
        this.isConnecting = false;
        this.stopPing();

        // Reconnect unless it was a clean close or auth error
        if (event.code !== 1000 && event.code !== 4001) {
          this.scheduleReconnect();
        }
      };

      this.socket.onerror = (error) => {
        console.error("WebSocket error", error);
        this.isConnecting = false;
      };
    } catch (error) {
      console.error("WebSocket: Failed to create connection", error);
      this.isConnecting = false;
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn("WebSocket: Max reconnect attempts reached");
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`WebSocket: Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

    setTimeout(() => {
      if (this.endpoint) {
        this.establishConnection();
      }
    }, delay);
  }

  private startPing(): void {
    this.pingInterval = setInterval(() => {
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.socket.send("ping");
      }
    }, 30000); // Ping every 30 seconds
  }

  private stopPing(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  disconnect(): void {
    this.stopPing();
    if (this.socket) {
      this.socket.close(1000, "Client disconnect");
      this.socket = null;
    }
    this.endpoint = "";
    this.reconnectAttempts = 0;
  }

  subscribe(handler: EventHandler): () => void {
    this.handlers.add(handler);
    return () => {
      this.handlers.delete(handler);
    };
  }

  isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  getState(): "connecting" | "open" | "closing" | "closed" {
    if (!this.socket) return "closed";
    switch (this.socket.readyState) {
      case WebSocket.CONNECTING:
        return "connecting";
      case WebSocket.OPEN:
        return "open";
      case WebSocket.CLOSING:
        return "closing";
      default:
        return "closed";
    }
  }
}

// Singleton instance
export const wsManager = new WebSocketManager();

// React hook for WebSocket events
import { useEffect, useState, useCallback } from "react";

export function useWebSocket(
  endpoint: "/ws/live" | `/ws/analysis/${string}` | null,
  onEvent?: EventHandler
) {
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<WebSocketEvent[]>([]);

  const handleEvent = useCallback(
    (event: WebSocketEvent) => {
      setEvents((prev) => [...prev.slice(-99), event]); // Keep last 100 events
      onEvent?.(event);
    },
    [onEvent]
  );

  useEffect(() => {
    if (!endpoint) {
      wsManager.disconnect();
      setIsConnected(false);
      return;
    }

    wsManager.connect(endpoint);

    const unsubscribe = wsManager.subscribe(handleEvent);

    // Check connection status periodically
    const checkInterval = setInterval(() => {
      setIsConnected(wsManager.isConnected());
    }, 1000);

    return () => {
      unsubscribe();
      clearInterval(checkInterval);
    };
  }, [endpoint, handleEvent]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  return {
    isConnected,
    events,
    clearEvents,
    state: wsManager.getState(),
  };
}
