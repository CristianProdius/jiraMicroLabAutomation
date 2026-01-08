import { create } from "zustand";
import type { User } from "@/types/feedback";
import { authApi } from "@/lib/api/feedback-api";

interface UserState {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  fetchUser: () => Promise<void>;
  logout: () => Promise<void>;
  clearUser: () => void;
}

export const useUserStore = create<UserState>((set) => ({
  user: null,
  isLoading: false,
  error: null,

  fetchUser: async () => {
    set({ isLoading: true, error: null });
    try {
      const user = await authApi.getCurrentUser();
      set({ user, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch user",
        isLoading: false,
        user: null,
      });
    }
  },

  logout: async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignore logout errors
    }
    set({ user: null, error: null });
    window.location.href = "/auth/v1/login";
  },

  clearUser: () => {
    set({ user: null, error: null, isLoading: false });
  },
}));
