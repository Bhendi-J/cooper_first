import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { authApi } from "@/lib/api";

interface User {
  id: string;
  email: string;
  name?: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem("token"));
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing session with backend
    if (token) {
      checkAuth();
    } else {
      setIsLoading(false);
    }
  }, []);

  const checkAuth = async () => {
    try {
      const response = await authApi.getCurrentUser();
      if (response.data.user) {
        setUser({
          id: response.data.user._id || response.data.user.id,
          email: response.data.user.email,
          name: response.data.user.name || response.data.user.email.split("@")[0],
        });
      }
    } catch {
      // Token invalid, clear it
      localStorage.removeItem("token");
      setToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    const response = await authApi.login(email, password);
    const data = response.data;
    
    // Save token
    if (data.access_token) {
      localStorage.setItem("token", data.access_token);
      setToken(data.access_token);
    }
    
    const userData = data.user;
    setUser({
      id: userData._id || userData.id,
      email: userData.email,
      name: userData.name || userData.email.split("@")[0],
    });
  };

  const register = async (name: string, email: string, password: string) => {
    const response = await authApi.register({ name, email, password });
    const data = response.data;
    
    // Save token from register response
    if (data.access_token) {
      localStorage.setItem("token", data.access_token);
      setToken(data.access_token);
    }
    
    const userData = data.user;
    setUser({
      id: userData._id || userData.id,
      email: userData.email,
      name: userData.name || userData.email.split("@")[0],
    });
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignore logout errors
    }
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
