import { Link, useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";
import { LogOut, LayoutDashboard } from "lucide-react";

export function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const isHome = location.pathname === "/";

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="fixed top-0 left-0 right-0 z-50 glass border-b border-border/50"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <span className="text-2xl group-hover:animate-bounce-in transition-transform">
              🚀
            </span>
            <span className="font-bold text-xl gradient-text-hero">
              HackStarter
            </span>
          </Link>

          {/* Right side */}
          <div className="flex items-center gap-3">
            {user ? (
              <>
                {/* User pill */}
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-secondary/80 border border-border/50">
                  <div className="w-7 h-7 rounded-full avatar-gradient flex items-center justify-center text-white text-sm font-medium">
                    {user.email[0].toUpperCase()}
                  </div>
                  <span className="text-sm font-medium text-foreground hidden sm:block">
                    {user.name || user.email.split("@")[0]}
                  </span>
                </div>

                {/* Dashboard link */}
                {location.pathname !== "/dashboard" && (
                  <Link
                    to="/dashboard"
                    className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-secondary/80 transition-all duration-200"
                  >
                    <LayoutDashboard size={16} />
                    <span className="hidden sm:inline">Dashboard</span>
                  </Link>
                )}

                {/* Logout button */}
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all duration-200"
                >
                  <LogOut size={16} />
                  <span className="hidden sm:inline">Logout</span>
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="px-4 py-2 rounded-xl text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-secondary/80 transition-all duration-200"
                >
                  Login
                </Link>
                <Link
                  to="/register"
                  className="px-4 py-2 rounded-xl text-sm font-medium bg-gradient-primary text-primary-foreground glow-button hover:opacity-90 transition-all duration-200 press-effect"
                >
                  Get Started
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </motion.nav>
  );
}
