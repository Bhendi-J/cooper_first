import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

export default function DashboardPage() {
  const { user, isLoading, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && !user) {
      navigate("/login");
    }
  }, [user, isLoading, navigate]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Loading...</p>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="min-h-screen pt-20 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="bg-card border border-border rounded-lg p-6 mb-6">
          <h1 className="text-2xl font-bold mb-2">Dashboard</h1>
          <p className="text-muted-foreground">
            Logged in as: <span className="text-foreground">{user.email}</span>
          </p>
        </div>

        {/* Add your dashboard content here */}
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Your Content</h2>
          <p className="text-muted-foreground">
            Start building your hackathon project here!
          </p>
        </div>

        <button
          onClick={logout}
          className="mt-6 px-4 py-2 bg-destructive text-destructive-foreground rounded-lg hover:opacity-90"
        >
          Logout
        </button>
      </div>
    </div>
  );
}
