import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authAPI, User as APIUser } from '@/lib/api';

interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  wallet_address?: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  login: (user: User, token: string) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
  fetchCurrentUser: () => Promise<void>;
}

// Helper to map API user to local user format
const mapApiUser = (apiUser: APIUser): User => ({
  id: apiUser._id,
  name: apiUser.name,
  email: apiUser.email,
  wallet_address: apiUser.wallet_address,
});

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: true,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setToken: (token) => {
        if (token) {
          localStorage.setItem('token', token);
        } else {
          localStorage.removeItem('token');
        }
        set({ token });
      },
      login: (user, token) => {
        localStorage.setItem('token', token);
        set({ user, token, isAuthenticated: true, isLoading: false });
      },
      logout: () => {
        localStorage.removeItem('token');
        set({ user: null, token: null, isAuthenticated: false });
      },
      setLoading: (isLoading) => set({ isLoading }),
      fetchCurrentUser: async () => {
        const token = localStorage.getItem('token');
        if (!token) {
          set({ isLoading: false, isAuthenticated: false });
          return;
        }
        try {
          const response = await authAPI.me();
          const user = mapApiUser(response.data);
          set({ user, token, isAuthenticated: true, isLoading: false });
        } catch {
          localStorage.removeItem('token');
          set({ user: null, token: null, isAuthenticated: false, isLoading: false });
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ token: state.token, user: state.user }),
    }
  )
);
