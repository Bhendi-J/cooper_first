import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// =====================
// TYPE DEFINITIONS
// =====================

export interface User {
  _id: string;
  name: string;
  email: string;
  wallet_address?: string;
}

export interface Event {
  _id: string;
  name: string;
  description?: string;
  creator_id: string;
  start_date?: string;
  end_date?: string;
  status: 'active' | 'completed' | 'cancelled';
  invite_code?: string;
  invite_enabled?: boolean;
  total_pool: number;
  total_spent: number;
  participants?: Participant[];
  rules?: {
    spending_limit?: number;
    approval_required?: boolean;
    auto_approve_under?: number;
  };
  created_at?: string;
}

export interface Participant {
  _id: string;
  user_id: string;
  user_name: string;
  deposit_amount: number;
  total_spent: number;
  balance: number;
  status: string;
}

export interface Expense {
  _id: string;
  event_id: string;
  payer_id: string;
  amount: number;
  description: string;
  category_id?: string;
  split_type: 'equal' | 'custom';
  splits: Array<{
    user_id: string;
    amount: number;
    status: 'paid' | 'pending';
  }>;
  status: 'pending' | 'verified';
  merkle_proof?: string[];
  created_at: string;
}

export interface Category {
  _id: string;
  name: string;
  icon?: string;
}

// =====================
// AUTH API
// =====================
export const authAPI = {
  register: (data: { name: string; email: string; password: string }) =>
    api.post<{ access_token: string; user: User }>('/auth/register', data),
  login: (data: { email: string; password: string }) =>
    api.post<{ access_token: string; user: User }>('/auth/login', data),
  me: () => api.get<User>('/auth/me'),
};

// =====================
// EVENTS API
// =====================
export interface CreateEventData {
  name: string;
  description?: string;
  start_date?: string;
  end_date?: string;
  rules?: {
    spending_limit?: number;
    approval_required?: boolean;
    auto_approve_under?: number;
  };
}

export const eventsAPI = {
  // Create a new event
  create: (data: CreateEventData) =>
    api.post<{ event: Event }>('/events/', data),
  
  // List all events for the current user
  list: () => api.get<{ events: Event[] }>('/events/'),
  
  // Get a single event by ID
  get: (id: string) => api.get<{ event: Event }>(`/events/${id}`),
  
  // Join an event by event ID (deprecated, use joinByCode instead)
  join: (id: string) => api.post<{ message: string }>(`/events/${id}/join`),
  
  // Get event preview by invite code (public)
  getByInviteCode: (code: string) =>
    api.get<{ event: Partial<Event> & { creator_name: string; participant_count: number } }>(
      `/events/join/${code}`
    ),
  
  // Join an event using invite code
  joinByCode: (code: string) =>
    api.post<{ message: string; event_id: string; event_name: string }>(
      `/events/join/${code}`
    ),
  
  // Deposit money to an event
  deposit: (id: string, amount: number) =>
    api.post<{ message: string; amount: number }>(`/events/${id}/deposit`, { amount }),
  
  // Get invite link info
  getInviteLink: (id: string) =>
    api.get<{
      invite_code: string;
      invite_url: string;
      frontend_join_url: string;
      invite_enabled: boolean;
      qr_data: string;
    }>(`/events/${id}/invite-link`),
  
  // Toggle or regenerate invite link
  updateInviteLink: (id: string, data: { enabled?: boolean; regenerate?: boolean }) =>
    api.put<{ invite_code: string; invite_enabled: boolean; invite_url: string }>(
      `/events/${id}/invite-link`,
      data
    ),
};

// =====================
// EXPENSES API
// =====================
export interface CreateExpenseData {
  event_id: string;
  amount: number;
  description?: string;
  category_id?: string;
}

export const expensesAPI = {
  // Add a new expense
  add: (data: CreateExpenseData) =>
    api.post<{ expense: Expense; merkle_root: string; payment_intents: Array<{ user_id: string; intent: any }> }>(
      '/expenses/',
      data
    ),
  
  // Get all expenses for an event
  getByEvent: (eventId: string) =>
    api.get<{ expenses: Expense[]; merkle_root: string }>(`/expenses/event/${eventId}`),
  
  // Verify an expense
  verify: (id: string, proof?: string[]) =>
    api.post<{ valid: boolean; expense_hash?: string; error?: string }>(
      `/expenses/${id}/verify`,
      proof ? { proof } : {}
    ),
  
  // Get expense categories
  getCategories: () => api.get<{ categories: Category[] }>('/expenses/categories'),
};

// =====================
// USERS API
// =====================
export const usersAPI = {
  // Get current user's profile
  getProfile: () => api.get<User>('/users/profile'),
  
  // Get user's summary stats
  getSummary: () => api.get<{ events: number; expenses: number }>('/users/summary'),
};

// =====================
// WALLETS API
// =====================
export const walletsAPI = {
  // Get wallet balance for a user
  getBalance: (userId: string) =>
    api.get<{ user_id: string; balance: number }>(`/wallets/balance/${userId}`),
  
  // Deposit to wallet
  deposit: (data: { amount: number; user_id?: string }) =>
    api.post<{ status: string; data: any }>('/wallets/deposit', data),
};

// =====================
// DASHBOARDS API
// =====================
export const dashboardsAPI = {
  // Get dashboard summary for a user
  getSummary: (userId: string) =>
    api.get<{ user_id: string; summary: any }>(`/dashboards/summary/${userId}`),
};

// =====================
// SETTLEMENTS API
// =====================
export const settlementsAPI = {
  // Finalize settlements for an event
  finalize: (eventId: string) =>
    api.post<{ event_id: string; status: string }>(`/settlements/finalize/${eventId}`),
};

// =====================
// PAYMENTS API
// =====================
export const paymentsAPI = {
  // Create a payment intent
  createIntent: (data: { amount: number; description?: string }) =>
    api.post<{ status: string; data: any }>('/payments/intent', data),
  
  // Get payment intent by ID
  getIntent: (intentId: string) =>
    api.get<{ id: string; status: string }>(`/payments/intent/${intentId}`),
};
