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
  split_type: 'equal' | 'weighted' | 'percentage' | 'exact' | 'custom';
  splits: Array<{
    user_id: string;
    amount: number;
    status: 'paid' | 'pending';
  }>;
  status: 'pending' | 'pending_approval' | 'approved' | 'rejected' | 'cancelled' | 'verified';
  approval_status?: 'pending' | 'approved' | 'rejected';
  merkle_proof?: string[];
  created_at: string;
}

export interface Category {
  _id: string;
  name: string;
  icon?: string;
}

// =====================
// NOTIFICATIONS TYPES
// =====================
export interface Notification {
  _id: string;
  user_id: string;
  type: string;
  title: string;
  message: string;
  data?: Record<string, any>;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  read: boolean;
  created_at: string;
  read_at?: string;
}

// =====================
// DEBT TYPES
// =====================
export interface UserDebt {
  _id: string;
  user_id: string;
  event_id: string;
  expense_id?: string;
  amount: number;
  remaining_amount: number;
  status: 'outstanding' | 'partially_paid' | 'settled' | 'forgiven';
  created_at: string;
  days_overdue?: number;
}

export interface DebtRestrictions {
  has_restrictions: boolean;
  warning: boolean;
  restricted: boolean;
  critical: boolean;
  oldest_debt_days?: number;
  total_outstanding?: number;
}

// =====================
// RELIABILITY TYPES
// =====================
export interface ReliabilityScore {
  score: number;
  tier: 'excellent' | 'good' | 'fair' | 'poor' | 'restricted';
  factors: {
    shortfall_count?: number;
    late_settlements?: number;
    debt_age_days?: number;
  };
  restrictions: {
    expense_multiplier?: number;
    deposit_multiplier?: number;
    force_approval?: boolean;
    can_join_events?: boolean;
  };
}

// =====================
// JOIN REQUEST TYPES
// =====================
export interface JoinRequest {
  _id: string;
  event_id: string;
  user_id: string;
  user_name?: string;
  user_email?: string;
  status: 'pending' | 'approved' | 'rejected';
  join_method: string;
  created_at: string;
}

// =====================
// APPROVAL TYPES
// =====================
export interface PendingApproval {
  _id: string;
  event_id: string;
  payer_id: string;
  payer_name?: string;
  amount: number;
  description?: string;
  status?: 'pending' | 'pending_approval' | 'approved' | 'rejected';
  approval_status?: 'pending' | 'approved' | 'rejected';
  category_id?: string;
  split_type?: string;
  created_at?: string;
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
  creator_deposit?: number;
  use_wallet?: boolean;  // If true, deduct deposit from wallet instead of payment gateway
  rules?: {
    spending_limit?: number;
    approval_required?: boolean;
    auto_approve_under?: number;
    min_deposit?: number;
    max_deposit?: number;
    max_expense_per_transaction?: number;
    min_expense_per_transaction?: number;
    approval_required_threshold?: number;
  };
}

export const eventsAPI = {
  // Create a new event
  create: (data: CreateEventData) =>
    api.post<{ event: Event }>('/events/', data),

  // List all events for the current user with pagination
  list: (params?: { page?: number; limit?: number; sort?: string; order?: 'asc' | 'desc'; status?: string }) =>
    api.get<{ events: Event[]; pagination: Pagination }>('/events/', { params }),

  // Get a single event by ID
  get: (id: string) => api.get<{ event: Event }>(`/events/${id}`),

  // Join an event by event ID (deprecated, use joinByCode instead)
  join: (id: string) => api.post<{ message: string }>(`/events/${id}/join`),

  // Leave an event and withdraw balance
  leave: (id: string) =>
    api.post<{
      message: string;
      amount_withdrawn: number;
      event_name: string;
    }>(`/events/${id}/leave`),

  // Get event preview by invite code (public)
  getByInviteCode: (code: string) =>
    api.get<{ event: Partial<Event> & { creator_name: string; participant_count: number } }>(
      `/events/join/${code}`
    ),

  // Join an event using invite code with optional deposit
  joinByCode: (code: string, data?: { deposit_amount?: number }) =>
    api.post<{ 
      message: string; 
      event_id?: string; 
      event_name?: string;
      status?: 'pending' | 'approved';
      request_id?: string;
      deposit_amount?: number;
    }>(`/events/join/${code}`, data || {}),

  // Get pending join requests for an event (creator only)
  getJoinRequests: (eventId: string) =>
    api.get<{ requests: JoinRequest[] }>(`/events/${eventId}/join-requests`),

  // Approve a join request (creator only)
  approveJoinRequest: (eventId: string, requestId: string) =>
    api.post<{ message: string; status: string }>(`/events/${eventId}/join-requests/${requestId}/approve`),

  // Reject a join request (creator only)
  rejectJoinRequest: (eventId: string, requestId: string, reason?: string) =>
    api.post<{ message: string; status: string }>(`/events/${eventId}/join-requests/${requestId}/reject`, { reason }),

  // Deposit money to an event (direct mode)
  deposit: (id: string, amount: number) =>
    api.post<{ message: string; amount: number }>(`/events/${id}/deposit`, { amount }),

  // Deposit money via Finternet (returns payment URL or confirms immediately)
  depositWithFinternet: (id: string, amount: number, currency = 'USDC') =>
    api.post<{
      message: string;
      payment_url: string;
      intent_id: string;
      finternet_id: string;
      amount: number;
      status?: 'CONFIRMED' | 'INITIATED' | 'PROCESSING';
      transaction_hash?: string;
      block_number?: number;
      chain?: string;
      confirmations?: number;
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

  // Transfer event ownership to another participant
  transferOwnership: (id: string, newOwnerId: string) =>
    api.post<{
      message: string;
      new_owner_id: string;
      new_owner_name: string;
    }>(`/events/${id}/transfer-ownership`, { new_owner_id: newOwnerId }),

  // Delete an event (creator only)
  delete: (id: string) =>
    api.delete<{
      message: string;
      event_name: string;
      participants_notified: number;
    }>(`/events/${id}`),

  // End an event and distribute balances (creator only)
  end: (id: string) =>
    api.post<{
      message: string;
      event_name: string;
      status: string;
      settlements: Array<{
        user_id: string;
        user_name: string;
        deposit_amount: number;
        total_spent: number;
        balance_returned: number;
        net_position: number;
      }>;
      total_pool: number;
      total_spent: number;
      participants_count: number;
    }>(`/events/${id}/end`),

  // Recalculate pool from scratch (creator only)
  recalculatePool: (id: string) =>
    api.post<{
      message: string;
      before: { total_pool: number; total_spent: number };
      after: {
        total_deposits: number;
        total_spent: number;
        total_pool: number;
        participants_updated: number;
        expenses_counted: number;
      };
    }>(`/events/${id}/recalculate-pool`),

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
  split_type?: 'equal' | 'weighted' | 'percentage' | 'exact';
  split_details?: {
    weights?: Record<string, number>;
    percentages?: Record<string, number>;
    amounts?: Record<string, number>;
  };
  selected_members?: string[];  // For custom splits: only these members are included
}

export interface AddExpenseResponse {
  expense: Expense;
  merkle_root?: string;
  status?: 'pending_approval' | 'approved';
  message?: string;
  shortfall_debts?: Array<{
    user_id: string;
    amount: number;
    debt_id: string;
  }>;
}

export const expensesAPI = {
  // Add a new expense
  add: (data: CreateExpenseData) =>
    api.post<AddExpenseResponse>('/expenses/', data),

  // Add expense with payment gateway
  addWithPayment: (data: CreateExpenseData) =>
    api.post<{
      pending_expense_id: string;
      payment_intent_id: string;
      payment_url: string;
      amount: number;
      message: string;
    }>('/expenses/pay', data),

  // Confirm expense payment
  confirmPayment: (pendingId: string) =>
    api.post<{
      message: string;
      expense_id: string;
      amount: number;
    }>(`/expenses/pay/${pendingId}/confirm`),

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

  // Get pending approvals for an event (creator only)
  getPendingApprovals: (eventId: string) =>
    api.get<{ pending_approvals: PendingApproval[] }>(`/expenses/pending-approvals/${eventId}`),

  // Approve an expense (creator only)
  approve: (expenseId: string) =>
    api.post<{ 
      message: string; 
      expense_id: string;
      shortfall_debts?: Array<{ user_id: string; amount: number; debt_id: string }>;
    }>(`/expenses/${expenseId}/approve`),

  // Reject an expense (creator only)
  reject: (expenseId: string, reason?: string) =>
    api.post<{ message: string; expense_id: string }>(`/expenses/${expenseId}/reject`, { reason }),

  // Cancel a pending expense (expense creator only)
  cancel: (expenseId: string) =>
    api.post<{ message: string; expense_id: string }>(`/expenses/${expenseId}/cancel`),
  
  // =====================
  // CASH EXPENSE METHODS
  // =====================
  
  // Add a cash expense that requires approval from all members
  addCash: (data: CreateExpenseData) =>
    api.post<{
      expense: Expense;
      status: 'pending_member_approval' | 'approved';
      members_pending?: string[];
      message: string;
    }>('/expenses/cash', data),
  
  // Approve a cash expense (as a member in the split)
  approveCash: (expenseId: string) =>
    api.post<{
      message: string;
      status: 'pending_member_approval' | 'approved';
      members_remaining?: number;
      all_approved: boolean;
    }>(`/expenses/cash/${expenseId}/approve`),
  
  // Reject a cash expense (as a member in the split)
  rejectCash: (expenseId: string, reason?: string) =>
    api.post<{ message: string; status: 'rejected' }>(`/expenses/cash/${expenseId}/reject`, { reason }),
  
  // Get pending cash approvals for the current user
  getPendingCashApprovals: () =>
    api.get<{
      pending_approvals: Array<{
        _id: string;
        event_id: string;
        event_name: string;
        payer_id: string;
        payer_name: string;
        amount: number;
        description: string;
        your_share: number;
        created_at: string;
        members_approved: number;
        members_pending: number;
      }>;
    }>('/expenses/cash/pending'),
};

// =====================
// USERS API
// =====================
export interface UserSummary {
  events: number;
  expense_count: number;
  total_expense_amount: number;
  total_balance: number;
  total_deposits: number;
  net_position: number;
}

export const usersAPI = {
  // Get current user's profile
  getProfile: () => api.get<User>('/users/profile'),

  // Get user's summary stats
  getSummary: () => api.get<UserSummary>('/users/summary'),

  // Search for users by email or name
  search: (query: string) =>
    api.get<{ users: Array<{ _id: string; name: string; email: string }> }>(`/users/search?q=${encodeURIComponent(query)}`),
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
  icon: string;
  color: string;
  total: number;
  count: number;
}

export interface DailyExpense {
  date: string;
  total: number;
  count: number;
}

export interface WeeklyComparison {
  this_week: number;
  last_week: number;
  change_percent: number;
}

export interface TopEvent {
  event_id: string;
  event_name: string;
  total: number;
}

export interface MonthlyTrend {
  month: string;
  total: number;
  count: number;
}

export interface AnalyticsOverview {
  category_totals: CategoryTotal[];
  daily_expenses: DailyExpense[];
  weekly_comparison: WeeklyComparison;
  top_events: TopEvent[];
  monthly_trend: MonthlyTrend[];
  total_expenses: number;
  avg_expense: number;
  expense_count: number;
}

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export const analyticsAPI = {
  // Get analytics overview for current user
  getOverview: () => api.get<AnalyticsOverview>('/analytics/overview'),
};

// =====================
// WALLETS API
// =====================
export interface WalletTransaction {
  _id: string;
  wallet_id: string;
  user_id: string;
  type: 'credit' | 'debit';
  amount: number;
  source?: string;
  purpose?: string;
  reference_id?: string;
  notes?: string;
  balance_after: number;
  created_at: string;
}

export const walletsAPI = {
  // Get current user's wallet balance
  getBalance: () =>
    api.get<{ user_id: string; balance: number }>('/wallets/balance'),

  // Get wallet balance for a specific user
  getUserBalance: (userId: string) =>
    api.get<{ user_id: string; balance: number }>(`/wallets/balance/${userId}`),

  // Initiate deposit via Finternet (returns payment URL)
  deposit: (amount: number, useFinternet = true) =>
    api.post<{
      status: string;
      message: string;
      intent_id?: string;
      payment_url?: string;
      amount: number;
      new_balance?: number;
    }>('/wallets/deposit', { amount, use_finternet: useFinternet }),

  // Confirm deposit after Finternet payment
  confirmDeposit: (intentId: string) =>
    api.post<{
      status: string;
      message: string;
      amount: number;
      new_balance: number;
    }>('/wallets/deposit/confirm', { intent_id: intentId }),

  // Withdraw from wallet (1% fee applies) via Finternet
  withdraw: (amount: number) =>
    api.post<{
      status: string;
      message: string;
      gross_amount: number;
      fee_amount: number;
      fee_percent: number;
      net_amount: number;
      amount_withdrawn: number;
      new_balance: number;
      payment_url?: string;
    }>('/wallets/withdraw', { amount }),

  // Get withdrawal fee info
  getWithdrawalFee: () =>
    api.get<{ fee_percent: number; description: string }>('/wallets/withdrawal-fee'),

  // Get wallet transaction history
  getTransactions: (page = 1, perPage = 20) =>
    api.get<{ 
      transactions: WalletTransaction[]; 
      page: number; 
      per_page: number; 
      total: number; 
      pages: number 
    }>(`/wallets/transactions?page=${page}&per_page=${perPage}`),

  // Transfer to another user
  transfer: (toUserId: string, amount: number, notes?: string) =>
    api.post<{ status: string; message: string; new_balance: number }>('/wallets/transfer', {
      to_user_id: toUserId,
      amount,
      notes,
    }),
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
    api.post<{ 
      settlement: Settlement;
      debts_settled?: Array<{ debt_id: string; amount_settled: number; status: string }>;
    }>('/settlements/settle', data),

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

  // ==================== DEBT ENDPOINTS ====================
  
  // Get current user's outstanding debts
  getMyDebts: () =>
    api.get<{ debts: UserDebt[]; restrictions: DebtRestrictions }>('/settlements/debts/my'),

  // Settle a specific debt (creates payment intent)
  settleDebt: (debtId: string, amount?: number) =>
    api.post<{
      id: string;
      status: string;
      paymentUrl: string;
      amount: number;
      debt_id: string;
    }>(`/settlements/debts/${debtId}/settle`, amount ? { amount } : {}),

  // Forgive a debt (creator only)
  forgiveDebt: (debtId: string, reason?: string) =>
    api.post<{ message: string; debt_id: string }>(`/settlements/debts/${debtId}/forgive`, { reason }),

  // ==================== NOTIFICATION ENDPOINTS ====================

  // Get notifications for current user
  getNotifications: (unreadOnly = false, limit = 50) =>
    api.get<{ notifications: Notification[]; unread_count: number }>(
      `/settlements/notifications?unread_only=${unreadOnly}&limit=${limit}`
    ),

  // Mark a notification as read
  markNotificationRead: (notificationId: string) =>
    api.post<{ success: boolean }>(`/settlements/notifications/${notificationId}/read`),

  // Mark all notifications as read
  markAllNotificationsRead: () =>
    api.post<{ marked_read: number }>('/settlements/notifications/read-all'),

  // ==================== RELIABILITY ENDPOINTS ====================

  // Get reliability score for current user
  getReliabilityScore: () =>
    api.get<ReliabilityScore>('/settlements/reliability/score'),
};

// =====================
// NOTIFICATIONS API (Standalone)
// =====================
export const notificationsAPI = {
  // Get notifications with pagination
  getAll: (page = 1, perPage = 20, unreadOnly = false) =>
    api.get<{ 
      notifications: Notification[]; 
      page: number; 
      per_page: number; 
      total: number; 
      pages: number;
      unread_count: number 
    }>(`/notifications?page=${page}&per_page=${perPage}&unread_only=${unreadOnly}`),

  // Get unread count only
  getUnreadCount: () =>
    api.get<{ unread_count: number }>('/notifications/unread-count'),

  // Mark as read
  markAsRead: (notificationId: string) =>
    api.post<{ status: string; message: string }>(`/notifications/${notificationId}/read`),

  // Mark all as read
  markAllAsRead: () =>
    api.post<{ status: string; message: string }>('/notifications/read-all'),

  // Delete a notification
  delete: (notificationId: string) =>
    api.delete<{ status: string; message: string }>(`/notifications/${notificationId}`),

  // Clear all notifications
  clearAll: () =>
    api.delete<{ status: string; message: string }>('/notifications/clear'),

  // Poll for new notifications (for real-time without WebSocket)
  poll: (since?: string) =>
    api.get<{ notifications: Notification[]; timestamp: string }>(
      `/notifications/poll${since ? `?since=${since}` : ''}`
    ),
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

  // ==================== NEW PAYMENT ENDPOINTS ====================

  // Create a deposit intent for an event
  createDepositIntent: (eventId: string, amount: number) =>
    api.post<{
      id: string;
      status: string;
      paymentUrl: string;
      amount: number;
      currency: string;
    }>('/payments/deposit', { event_id: eventId, amount }),

  // Create a wallet top-up intent
  createTopupIntent: (amount: number) =>
    api.post<{
      id: string;
      status: string;
      paymentUrl: string;
      amount: number;
      currency: string;
    }>('/payments/topup', { amount }),

  // Create a debt settlement intent
  createDebtSettlementIntent: (debtId?: string, amount?: number) =>
    api.post<{
      id: string;
      status: string;
      paymentUrl: string;
      amount: number;
      currency: string;
    }>('/payments/debts/settle', { debt_id: debtId, amount }),
};

// =====================
// WELLNESS API - Supportive financial companion
// =====================

export interface WellnessStatus {
  label: string;
  emoji: string;
  color: string;
  description: string;
}

export interface WellnessInsight {
  type: 'positive' | 'neutral' | 'info';
  icon: string;
  message: string;
}

export interface SpendingCategory {
  category: string;
  emoji: string;
  amount: number;
  percentage: number;
}

export interface WellnessSummary {
  wellness_score: number;
  wellness_status: WellnessStatus;
  spending_summary: {
    last_30_days: number;
    transaction_count: number;
    average_transaction: number;
  };
  pending_summary: {
    total_pending: number;
    pending_count: number;
    message: string;
  };
  positive_actions: {
    payments_made: number;
    payments_count: number;
    message: string;
  };
  spending_breakdown: SpendingCategory[];
  insights: WellnessInsight[];
  encouragement: string;
}

export interface WellnessReminder {
  type: string;
  priority: string;
  icon: string;
  title: string;
  message: string;
  action?: string;
  event_id?: string;
  dismissible: boolean;
}

export interface ReceiptScanResult {
  amount?: number;
  currency?: string;
  description?: string;
  date?: string;
  merchant?: string;
  category?: string;
  items?: Array<{ name: string; price: number }>;
  error?: string;
}

export const wellnessApi = {
  // Get personalized wellness summary
  getSummary: () =>
    api.get<{ summary: WellnessSummary; privacy_note: string }>('/wellness/summary'),

  // Get gentle reminders (never urgent)
  getReminders: () =>
    api.get<{ reminders: WellnessReminder[]; message: string }>('/wellness/reminders'),

  // Dismiss a reminder
  dismissReminder: (reminderType: string, referenceId?: string) =>
    api.post('/wellness/dismiss-reminder', { 
      reminder_type: reminderType, 
      reference_id: referenceId 
    }),

  // Get spending breakdown by category
  getSpendingBreakdown: (days?: number) =>
    api.get<{
      period_days: number;
      total_spent: number;
      transaction_count: number;
      breakdown: SpendingCategory[];
      insights: WellnessInsight[];
    }>('/wellness/spending-breakdown', { params: { days } }),
};

// =====================
// OCR / RECEIPT SCANNING
// =====================

export const receiptApi = {
  // Scan a receipt image and extract expense details
  scanReceipt: async (file: File): Promise<ReceiptScanResult> => {
    const formData = new FormData();
    formData.append('receipt', file);
    
    const response = await api.post<ReceiptScanResult>('/expenses/scan-receipt', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  },
};
