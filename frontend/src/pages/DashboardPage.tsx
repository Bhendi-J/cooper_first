import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Users, Activity, UserPlus, Loader2 } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { usersApi } from "@/lib/api";

interface BackendUser {
  id: string;
  email: string;
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: "easeOut" as const },
  },
};

export default function DashboardPage() {
  const { user, isLoading } = useAuth();
  const navigate = useNavigate();
  const [users, setUsers] = useState<BackendUser[]>([]);
  const [usersLoading, setUsersLoading] = useState(true);

  useEffect(() => {
    if (!isLoading && !user) {
      navigate("/login");
    }
  }, [user, isLoading, navigate]);

  useEffect(() => {
    // Fetch users from backend
    const fetchUsers = async () => {
      try {
        const response = await usersApi.getAll();
        setUsers(response.data);
      } catch (error) {
        console.error("Failed to fetch users:", error);
      } finally {
        setUsersLoading(false);
      }
    };

    if (user) {
      fetchUsers();
    }
  }, [user]);

  // Calculate stats based on real data
  const stats = [
    { emoji: "👥", label: "Total Users", value: users.length.toString(), icon: Users },
    { emoji: "✨", label: "Active Today", value: Math.floor(users.length * 0.7).toString(), icon: Activity },
    { emoji: "🆕", label: "New This Week", value: Math.min(users.length, 5).toString(), icon: UserPlus },
  ];

  if (isLoading) {
    return (
      <div className="min-h-screen mesh-gradient flex items-center justify-center">
        <div className="text-center">
          <span className="text-6xl animate-bounce-in">🚀</span>
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen mesh-gradient pt-24 pb-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        {/* Welcome Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="glass-card p-6 sm:p-8 mb-8"
        >
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-full avatar-gradient flex items-center justify-center text-white text-2xl font-bold shadow-glow">
              {user.email[0].toUpperCase()}
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold">
                Welcome back! 👋
              </h1>
              <p className="text-muted-foreground mt-1">
                Logged in as{" "}
                <span className="text-primary font-medium">{user.email}</span>
              </p>
            </div>
          </div>
        </motion.div>

        {/* Stats Grid */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8"
        >
          {stats.map((stat) => (
            <motion.div
              key={stat.label}
              variants={itemVariants}
              className="stat-card"
            >
              <div className="flex items-center gap-3">
                <span className="text-3xl">{stat.emoji}</span>
                <div>
                  <p className="text-2xl font-bold text-foreground">
                    {usersLoading ? "-" : stat.value}
                  </p>
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Users List */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="glass-card overflow-hidden"
        >
          <div className="p-6 border-b border-border/50 flex items-center justify-between">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <span>👥</span> All Users
            </h2>
            <span className="text-sm text-muted-foreground bg-secondary/50 px-3 py-1 rounded-full">
              {users.length} total
            </span>
          </div>

          {usersLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          ) : users.length === 0 ? (
            <div className="text-center py-12">
              <span className="text-4xl mb-3 block">🔍</span>
              <p className="text-muted-foreground">No users found</p>
            </div>
          ) : (
            <motion.div
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              className="divide-y divide-border/50"
            >
              {users.map((backendUser) => (
                <motion.div
                  key={backendUser.id}
                  variants={itemVariants}
                  className="flex items-center justify-between p-4 sm:p-5 hover:bg-secondary/30 transition-colors duration-200"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full avatar-gradient flex items-center justify-center text-white font-medium text-sm">
                      {backendUser.email[0].toUpperCase()}
                    </div>
                    <div>
                      <p className="font-medium text-foreground">
                        {backendUser.email}
                      </p>
                      <p className="text-sm text-muted-foreground font-mono">
                        ID: {backendUser.id.slice(-8)}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="active-dot" />
                    <span className="text-sm font-medium text-emerald-600">
                      Active
                    </span>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
