import axios from "axios";

// API instance - uses Vite proxy in development (same origin)
// In production, set VITE_API_URL environment variable
const api = axios.create({
  baseURL: "/api",  // Relative URL - goes through Vite proxy to Flask
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

// Auth API calls
export const authApi = {
  login: (email: string, password: string) =>
    api.post("/auth/login", { email, password }),

  logout: () => api.post("/auth/logout"),

  getCurrentUser: () => api.get("/auth/me"),

  register: (email: string, password: string) =>
    api.post("/users", { email, password }),
};

// Users API calls
export const usersApi = {
  getAll: () => api.get("/users/all"),

  getById: (id: string) => api.get(`/users/${id}`),

  update: (id: string, data: { email?: string; password?: string }) =>
    api.put(`/users/${id}`, data),

  delete: (id: string) => api.delete(`/users/${id}`),
};

// Search API calls
export const searchApi = {
  search: (query: string) => api.get(`/search?q=${encodeURIComponent(query)}`),
};

export default api;
