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

  // Deposit money to an event (direct mode)
  deposit: (id: string, amount: number) =>
    api.post<{ message: string; amount: number }>(`/events/${id}/deposit`, { amount }),

  // Deposit money via Finternet (returns payment URL)
  depositWithFinternet: (id: string, amount: number, currency = 'USDC') =>
    api.post<{
      message: string;
      payment_url: string;
      intent_id: string;
      finternet_id: string;
      amount: number;
    }>(`/events/${id}/deposit`, { amount, currency, use_finternet: true }),

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

  // Alias for get (some components use getById)
  getById: (id: string) => api.get<Event>(`/events/${id}`),
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

  // Scan receipt using Gemini AI
  scanReceipt: (file: File) => {
    const formData = new FormData();
    formData.append('receipt', file);
    return api.post<{
      amount?: number;
      description?: string;
      date?: string;
      currency?: string;
      items?: any[];
      error?: string;
    }>('/expenses/scan-receipt', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
};

// =====================
// USERS API
// =====================
export interface UserSummary {
  events: number;
  expense_count: number;
  total_expense_amount: number;
}

export const usersAPI = {
  // Get current user's profile
  getProfile: () => api.get<User>('/users/profile'),

  // Get user's summary stats
  getSummary: () => api.get<UserSummary>('/users/summary'),
};

// =====================
// DASHBOARDS API
// =====================
export interface RecentActivity {
  _id: string;
  type: 'expense' | 'deposit';
  description: string;
  amount: number;
  event_id: string;
  event_name: string;
  payer_id: string;
  payer_name: string;
  created_at: string;
}

export const dashboardsAPI = {
  // Get dashboard summary for a user
  getSummary: (userId: string) =>
    api.get<{ user_id: string; summary: any }>(`/dashboards/summary/${userId}`),

  // Get recent activity for current user
  getRecentActivity: (limit = 5) =>
    api.get<{ activities: RecentActivity[] }>(`/dashboards/recent-activity?limit=${limit}`),
};

// =====================
// ANALYTICS API
// =====================
export interface CategoryTotal {
  category_id: string;
  category_name: string;
  total: number;
  count: number;
}

export interface DailyExpense {
  date: string;
  total: number;
  count: number;
}

export interface AnalyticsOverview {
  category_totals: CategoryTotal[];
  daily_expenses: DailyExpense[];
}

export const analyticsAPI = {
  // Get analytics overview for current user
  getOverview: () => api.get<AnalyticsOverview>('/analytics/overview'),
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
// SETTLEMENTS API
// =====================
export interface Balance {
  user_id: string;
  username: string;
  email: string;
  balance: number;
  total_spent: number;
}

export interface Debt {
  from_user: string;
  from_username: string;
  to_user: string;
  to_username: string;
  amount: number;
}

export interface Settlement {
  _id: string;
  event_id: string;
  from_user_id: string;
  from_username: string;
  to_user_id: string;
  to_username: string;
  amount: number;
  payment_method: string;
  status: string;
  created_at: string;
}

export interface SettlementParticipant {
  user_id: string;
  user_name: string;
  deposited: number;
  spent: number;
  balance: number;
  status: string;
  refund_pending?: boolean;
  is_you?: boolean;
}

export interface SettlementSummary {
  event_id: string;
  event_name: string;
  event_status: string;
  total_pool: number;
  total_spent: number;
  settlements: SettlementParticipant[];
}

export interface Refund {
  _id: string;
  event_id: string;
  event_name: string;
  amount: number;
  status: 'pending' | 'processing' | 'completed';
  payment_url?: string;
  created_at: string;
  completed_at?: string;
}

export const settlementsAPI = {
  // Get balances for all participants in an event
  getBalances: (eventId: string) =>
    api.get<{ balances: Balance[] }>(`/settlements/balances/${eventId}`),

  // Get calculated debts (who owes whom)
  getDebts: (eventId: string) =>
    api.get<{ debts: Debt[]; total_owed: number }>(`/settlements/debts/${eventId}`),

  // Record a settlement payment
  settle: (data: { event_id: string; from_user_id: string; to_user_id: string; amount: number; payment_method?: string }) =>
    api.post<{ settlement: Settlement }>('/settlements/settle', data),

  // Get settlement history for an event
  getHistory: (eventId: string) =>
    api.get<{ settlements: Settlement[] }>(`/settlements/history/${eventId}`),

  // Finalize an event and enable refunds
  finalize: (eventId: string) =>
    api.post<{
      event_id: string;
      status: string;
      settlements: SettlementParticipant[];
      total_refundable: number;
      message?: string;
    }>(`/settlements/finalize/${eventId}`),

  // Get settlement summary for an event
  getSummary: (eventId: string) =>
    api.get<SettlementSummary>(`/settlements/${eventId}/summary`),

  // Request refund for remaining balance
  requestRefund: (eventId: string, walletAddress?: string, useFinternet = true) =>
    api.post<{
      refund_id: string;
      amount: number;
      status: string;
      payment_url?: string;
      intent_id?: string;
      finternet_id?: string;
    }>(`/settlements/${eventId}/refund`, {
      wallet_address: walletAddress,
      use_finternet: useFinternet,
    }),

  // Confirm refund after Finternet payment
  confirmRefund: (eventId: string, refundId: string, signature?: string, payerAddress?: string) =>
    api.post<{
      refund_id: string;
      amount: number;
      status: string;
    }>(`/settlements/${eventId}/refund/confirm`, {
      refund_id: refundId,
      signature,
      payer_address: payerAddress,
    }),

  // Get user's refund history
  getRefunds: () =>
    api.get<{ refunds: Refund[] }>('/settlements/refunds'),
};

// =====================
// PAYMENTS API
// =====================

export type PaymentStatus =
  | 'INITIATED'
  | 'REQUIRES_SIGNATURE'
  | 'PROCESSING'
  | 'SUCCEEDED'
  | 'SETTLED'
  | 'FINAL'
  | 'CANCELLED'
  | 'FAILED';

export type PaymentType = 'CONDITIONAL' | 'DELIVERY_VS_PAYMENT';

export interface PaymentIntent {
  id: string;
  status: PaymentStatus;
  amount: string;
  currency: string;
  type: PaymentType;
  settlementMethod: string;
  settlementDestination?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  data?: {
    paymentUrl?: string;
    typedData?: EIP712TypedData;
    transactionHash?: string;
    settlementStatus?: string;
  };
  createdAt: string;
  updatedAt: string;
}

export interface EIP712TypedData {
  domain: {
    name: string;
    version: string;
    chainId: number;
    verifyingContract: string;
  };
  types: Record<string, Array<{ name: string; type: string }>>;
  primaryType: string;
  message: Record<string, unknown>;
}

export interface LocalPaymentRecord {
  _id: string;
  finternet_id: string;
  user_id: string;
  event_id?: string;
  expense_id?: string;
  status: PaymentStatus;
  amount: string;
  currency: string;
  type: PaymentType;
  payer_address?: string;
  signature?: string;
  transaction_hash?: string;
  created_at: string;
  updated_at: string;
}

export interface PendingPayment {
  _id: string;
  expense_id: string;
  user_id: string;
  amount: number;
  status: 'pending' | 'paid';
  expense_description?: string;
  expense_amount?: number;
  event_name?: string;
}

export interface ConditionalPayment {
  id: string;
  status: string;
  escrowAddress?: string;
  releaseConditions?: {
    deliveryProofRequired: boolean;
    disputeWindow: number;
  };
  deliveryProof?: {
    hash: string;
    uri?: string;
    submittedAt: string;
    submittedBy: string;
  };
  dispute?: {
    reason: string;
    raisedAt: string;
    raisedBy: string;
  };
}

export interface CreatePaymentIntentData {
  amount: string;
  currency?: string;
  description?: string;
  event_id?: string;
  expense_id?: string;
  type?: PaymentType;
  settlement_method?: 'OFF_RAMP_MOCK' | 'BANK_TRANSFER';
  settlement_destination?: string;
}

export interface CreatePaymentIntentResponse {
  intent: PaymentIntent;
  payment_url: string;
  local_id: string;
}

export interface GetPaymentIntentResponse {
  intent: PaymentIntent | null;
  local: LocalPaymentRecord | null;
  api_error?: { message: string; code: string };
}

export interface ConfirmPaymentData {
  signature: string;
  payer_address: string;
}

export interface ConfirmPaymentResponse {
  intent: PaymentIntent;
  status: PaymentStatus;
}

export interface DeliveryProofData {
  proof_hash: string;
  submitted_by: string;
  proof_uri?: string;
}

export interface DisputeData {
  reason: string;
  raised_by: string;
  dispute_window?: string;
}

export const paymentsAPI = {
  // Create a new payment intent
  createIntent: (data: CreatePaymentIntentData) =>
    api.post<CreatePaymentIntentResponse>('/payments/intent', data),

  // Get payment intent by ID (Finternet ID or local MongoDB ID)
  getIntent: (intentId: string) =>
    api.get<GetPaymentIntentResponse>(`/payments/intent/${intentId}`),

  // Confirm payment with wallet signature
  confirmIntent: (intentId: string, data: ConfirmPaymentData) =>
    api.post<ConfirmPaymentResponse>(`/payments/intent/${intentId}/confirm`, data),

  // Cancel a payment intent
  cancelIntent: (intentId: string) =>
    api.post<{ intent: PaymentIntent; status: 'CANCELLED' }>(`/payments/intent/${intentId}/cancel`),

  // Get pending payments for current user
  getPending: () =>
    api.get<{ pending_payments: PendingPayment[] }>('/payments/pending'),

  // Get payment history for current user
  getHistory: (limit = 20) =>
    api.get<{ payments: LocalPaymentRecord[] }>(`/payments/history?limit=${limit}`),

  // Get escrow details for conditional payment
  getEscrow: (intentId: string) =>
    api.get<{ escrow: ConditionalPayment }>(`/payments/intent/${intentId}/escrow`),

  // Submit delivery proof for conditional payment
  submitDeliveryProof: (intentId: string, data: DeliveryProofData) =>
    api.post<{ delivery_proof: ConditionalPayment }>(`/payments/intent/${intentId}/escrow/delivery-proof`, data),

  // Raise a dispute for conditional payment
  raiseDispute: (intentId: string, data: DisputeData) =>
    api.post<{ dispute: ConditionalPayment }>(`/payments/intent/${intentId}/escrow/dispute`, data),

  // Confirm deposit payment
  confirmDeposit: (intentId: string, signature?: string, payerAddress?: string) =>
    api.post<{
      message: string;
      amount?: number;
      status: string;
      finternet_id?: string;
    }>('/payments/deposit/confirm', {
      intent_id: intentId,
      signature,
      payer_address: payerAddress,
    }),
};
