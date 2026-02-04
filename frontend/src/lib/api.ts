import axios from "axios";

// API instance - uses Vite proxy in development (same origin)
// In production, set VITE_API_URL environment variable
const api = axios.create({
  baseURL: "/api/v1",  // Relative URL - goes through Vite proxy to Flask
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses (token expired/invalid)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && localStorage.getItem("token")) {
      // Token is invalid, but don't clear on /auth/me (initial check)
      const url = error.config?.url || "";
      if (!url.includes("/auth/me")) {
        console.warn("Token expired or invalid");
      }
    }
    return Promise.reject(error);
  }
);

// Auth API calls
export const authApi = {
  login: (email: string, password: string) =>
    api.post("/auth/login", { email, password }),

  logout: () => api.post("/auth/logout"),

  getCurrentUser: () => api.get("/auth/me"),

  register: (data: { name: string; email: string; password: string }) =>
    api.post("/auth/register", data),
};

// Users API calls
export const usersApi = {
  getAll: () => api.get("/users/all"),
  getById: (id: string) => api.get(`/users/${id}`),
  getProfile: () => api.get("/users/profile"),
  update: (id: string, data: { email?: string; password?: string }) =>
    api.put(`/users/${id}`, data),
  delete: (id: string) => api.delete(`/users/${id}`),
};

// Events API calls
export const eventsApi = {
  getAll: () => api.get("/events/"),
  getById: (id: string) => api.get(`/events/${id}`),
  create: (data: { name: string; description?: string; start_date?: string; end_date?: string }) =>
    api.post("/events/", data),
  join: (eventId: string) => api.post(`/events/${eventId}/join`),
  joinByCode: (inviteCode: string) => api.post(`/events/join/${inviteCode}`),
  getEventByCode: (inviteCode: string) => api.get(`/events/join/${inviteCode}`),
  getInviteLink: (eventId: string) => api.get(`/events/${eventId}/invite-link`),
  toggleInviteLink: (eventId: string, data: { enabled?: boolean; regenerate?: boolean }) =>
    api.put(`/events/${eventId}/invite-link`, data),
  deposit: (eventId: string, amount: number) =>
    api.post(`/events/${eventId}/deposit`, { amount }),
  invite: (eventId: string, data: { email?: string; user_id?: string }) =>
    api.post(`/events/${eventId}/invite`, data),
  getInvites: () => api.get("/events/invites"),
  acceptInvite: (inviteId: string) => api.post(`/events/invites/${inviteId}/accept`),
  rejectInvite: (inviteId: string) => api.post(`/events/invites/${inviteId}/reject`),
};

// Friends API calls
export const friendsApi = {
  getAll: () => api.get("/events/friends"),
  getRequests: () => api.get("/events/friends/requests"),
  sendRequest: (data: { email?: string; user_id?: string }) =>
    api.post("/events/friends/request", data),
  acceptRequest: (requestId: string) =>
    api.post(`/events/friends/request/${requestId}/accept`),
  rejectRequest: (requestId: string) =>
    api.post(`/events/friends/request/${requestId}/reject`),
  remove: (friendId: string) =>
    api.delete(`/events/friends/${friendId}/remove`),
};

// Expenses API calls
export const expensesApi = {
  create: (data: { event_id: string; amount: number; description?: string; category_id?: string }) =>
    api.post("/expenses/", data),
  getByEvent: (eventId: string) =>
    api.get(`/expenses/event/${eventId}`),
  verify: (expenseId: string, proof?: object[]) =>
    api.post(`/expenses/${expenseId}/verify`, { proof }),
  getCategories: () => api.get("/expenses/categories"),
};

// Payments API calls
export const paymentsApi = {
  createIntent: (data: { expense_id: string; amount: number }) =>
    api.post("/payments/intent", data),
  confirmPayment: (paymentId: string) =>
    api.post(`/payments/${paymentId}/confirm`),
  getStatus: (paymentId: string) =>
    api.get(`/payments/${paymentId}/status`),
};

// Wallets API calls
export const walletsApi = {
  getBalance: () => api.get("/wallets/balance"),
  deposit: (amount: number) => api.post("/wallets/deposit", { amount }),
  withdraw: (amount: number) => api.post("/wallets/withdraw", { amount }),
};

// Settlements API calls
export const settlementsApi = {
  getByEvent: (eventId: string) => api.get(`/settlements/event/${eventId}`),
  settle: (settlementId: string) => api.post(`/settlements/${settlementId}/settle`),
};

// Search API calls
export const searchApi = {
  search: (query: string) => api.get(`/search?q=${encodeURIComponent(query)}`),
};

export default api;
