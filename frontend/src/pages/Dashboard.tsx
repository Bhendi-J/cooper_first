import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuthStore } from '@/store/authStore';
import { WellnessCard } from '@/components/WellnessCard';
import { 
  eventsAPI, 
  usersAPI, 
  dashboardsAPI, 
  analyticsAPI,
  settlementsAPI,
  walletsAPI,
  Event, 
  UserSummary, 
  RecentActivity, 
  AnalyticsOverview,
  Notification,
  Pagination
} from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import {
  Wallet,
  Plus,
  Users,
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  ArrowDownRight,
  Bell,
  Settings,
  LogOut,
  Calendar,
  Copy,
  ChevronRight,
  ChevronLeft,
  PieChart,
  X,
  Loader2,
  Heart,
  BarChart3,
  Activity,
} from 'lucide-react';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  Legend,
  AreaChart,
  Area,
} from 'recharts';

// Enable dayjs relative time plugin
dayjs.extend(relativeTime);

export default function Dashboard() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [showDropdown, setShowDropdown] = useState(false);
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [joinCode, setJoinCode] = useState('');
  const [isJoining, setIsJoining] = useState(false);
  
  // Data state
  const [events, setEvents] = useState<Event[]>([]);
  const [pagination, setPagination] = useState<Pagination | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [summary, setSummary] = useState<UserSummary | null>(null);
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showNotifications, setShowNotifications] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [walletBalance, setWalletBalance] = useState(0);
  const [activeChart, setActiveChart] = useState<'pie' | 'bar' | 'area'>('pie');

  // Fetch user's events on mount and when page gets focus
  useEffect(() => {
    fetchData();
    
    // Refetch when page becomes visible (e.g., after navigating back)
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchData();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [toast]);

  // Fetch events when page changes
  useEffect(() => {
    fetchEvents();
  }, [currentPage]);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const [eventsRes, summaryRes, activityRes, analyticsRes, notifRes, walletRes] = await Promise.all([
        eventsAPI.list({ page: currentPage, limit: 5, sort: 'created_at', order: 'desc' }),
        usersAPI.getSummary(),
        dashboardsAPI.getRecentActivity(5),
        analyticsAPI.getOverview(),
        settlementsAPI.getNotifications(false, 10).catch(() => ({ data: { notifications: [], unread_count: 0 } })),
        walletsAPI.getBalance().catch(() => ({ data: { balance: 0 } })),
      ]);
      setEvents(eventsRes.data.events || []);
      setPagination(eventsRes.data.pagination || null);
      setSummary(summaryRes.data);
      setWalletBalance(walletRes.data.balance || 0);
      setRecentActivity(activityRes.data.activities || []);
      setAnalytics(analyticsRes.data);
      setNotifications(notifRes.data.notifications || []);
      setUnreadCount(notifRes.data.unread_count || 0);
    } catch (error: any) {
      console.error('Failed to fetch dashboard data:', error);
      // If token is invalid, the interceptor will redirect to login
      if (error.response?.status !== 401) {
        toast({
          title: 'Failed to load data',
          description: 'Please refresh the page to try again.',
          variant: 'destructive',
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const fetchEvents = async () => {
    try {
      const eventsRes = await eventsAPI.list({ page: currentPage, limit: 5, sort: 'created_at', order: 'desc' });
      setEvents(eventsRes.data.events || []);
      setPagination(eventsRes.data.pagination || null);
    } catch (error) {
      console.error('Failed to fetch events:', error);
    }
  };

  const handleMarkNotificationRead = async (notifId: string) => {
    try {
      await settlementsAPI.markNotificationRead(notifId);
      setNotifications(prev => prev.map(n => n._id === notifId ? { ...n, read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Failed to mark notification read:', error);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await settlementsAPI.markAllNotificationsRead();
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch (error) {
      console.error('Failed to mark all notifications read:', error);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleJoinEvent = async () => {
    if (!joinCode.trim()) return;
    setIsJoining(true);
    try {
      const response = await eventsAPI.joinByCode(joinCode.trim().toUpperCase());
      toast({
        title: 'Successfully joined!',
        description: `You've joined ${response.data.event_name}`,
      });
      setShowJoinModal(false);
      setJoinCode('');
      // Refresh events list
      const eventsRes = await eventsAPI.list();
      setEvents(eventsRes.data.events || []);
    } catch (error: any) {
      toast({
        title: 'Failed to join',
        description: error.response?.data?.error || 'Invalid invite code',
        variant: 'destructive',
      });
    } finally {
      setIsJoining(false);
    }
  };

  // Calculate totals from real data
  const totalBalance = summary?.total_balance ?? 0;
  const totalDeposits = summary?.total_deposits ?? 0;
  const activeEvents = events.filter((e) => e.status === 'active').length;

  return (
    <div className="min-h-screen bg-background">
      {/* Top Navigation */}
      <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
              <Wallet className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-display font-bold">Cooper</span>
          </Link>

          <div className="flex items-center gap-4">
            <div className="relative">
              <Button 
                variant="ghost" 
                size="icon" 
                className="relative"
                onClick={() => setShowNotifications(!showNotifications)}
              >
                <Bell className="w-5 h-5" />
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] flex items-center justify-center bg-destructive text-destructive-foreground text-xs font-bold rounded-full px-1">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </Button>

              {showNotifications && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="absolute right-0 mt-2 w-80 glass-card rounded-xl py-2 shadow-xl z-50 max-h-96 overflow-y-auto"
                >
                  <div className="flex items-center justify-between px-4 py-2 border-b border-border">
                    <h3 className="font-semibold">Notifications</h3>
                    {unreadCount > 0 && (
                      <button 
                        onClick={handleMarkAllRead}
                        className="text-xs text-primary hover:underline"
                      >
                        Mark all read
                      </button>
                    )}
                  </div>
                  {notifications.length === 0 ? (
                    <div className="px-4 py-6 text-center text-muted-foreground">
                      No notifications yet
                    </div>
                  ) : (
                    <div className="divide-y divide-border">
                      {notifications.map((notif) => (
                        <button
                          key={notif._id}
                          onClick={() => handleMarkNotificationRead(notif._id)}
                          className={`w-full px-4 py-3 text-left hover:bg-accent transition-colors ${
                            !notif.read ? 'bg-primary/5' : ''
                          }`}
                        >
                          <div className="flex items-start gap-2">
                            {!notif.read && (
                              <span className="w-2 h-2 bg-primary rounded-full mt-1.5 flex-shrink-0" />
                            )}
                            <div className={!notif.read ? '' : 'pl-4'}>
                              <p className="font-medium text-sm">{notif.title}</p>
                              <p className="text-xs text-muted-foreground line-clamp-2">{notif.message}</p>
                              <p className="text-xs text-muted-foreground mt-1">
                                {dayjs(notif.created_at).fromNow()}
                              </p>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </motion.div>
              )}
            </div>

            <div className="relative">
              <button
                onClick={() => setShowDropdown(!showDropdown)}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-accent transition-colors"
              >
                <div className="w-9 h-9 rounded-full gradient-primary flex items-center justify-center text-sm font-bold text-primary-foreground">
                  {user?.name?.charAt(0) || 'U'}
                </div>
                <span className="hidden md:block font-medium">{user?.name || 'User'}</span>
              </button>

              {showDropdown && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="absolute right-0 mt-2 w-48 glass-card rounded-xl py-2 shadow-xl"
                >
                  <Link
                    to="/wallet"
                    className="flex items-center gap-2 px-4 py-2 hover:bg-accent transition-colors"
                  >
                    <Wallet className="w-4 h-4" />
                    <span>My Wallet</span>
                  </Link>
                  <Link
                    to="/wellness"
                    className="flex items-center gap-2 px-4 py-2 hover:bg-accent transition-colors"
                  >
                    <Heart className="w-4 h-4 text-pink-500" />
                    <span>Financial Wellness</span>
                  </Link>
                  <Link
                    to="/profile"
                    className="flex items-center gap-2 px-4 py-2 hover:bg-accent transition-colors"
                  >
                    <Settings className="w-4 h-4" />
                    <span>Settings</span>
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-2 px-4 py-2 w-full hover:bg-accent transition-colors text-destructive"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Log out</span>
                  </button>
                </motion.div>
              )}
            </div>
          </div>
        </div>
      </nav>

      <main className="container mx-auto px-6 py-8">
        {/* Welcome Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-3xl font-display font-bold mb-2">
            Welcome back, <span className="gradient-text">{user?.name?.split(' ')[0] || 'User'}</span>
          </h1>
          <p className="text-muted-foreground">
            Here's what's happening with your shared wallets.
          </p>
        </motion.div>

        {/* Quick Stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
        >
          <Link to="/wallet" className="glass-card p-6 rounded-xl hover:ring-2 ring-primary/50 transition-all cursor-pointer">
            <div className="flex items-center justify-between mb-4">
              <p className="text-muted-foreground">Wallet Balance</p>
              <div className="w-10 h-10 rounded-lg gradient-primary-subtle flex items-center justify-center">
                <Wallet className="w-5 h-5 text-primary" />
              </div>
            </div>
            <p className="text-3xl font-bold">${walletBalance.toLocaleString()}</p>
            <p className="text-sm flex items-center gap-1 mt-2 text-primary">
              <ChevronRight className="w-4 h-4" />
              Manage wallet
            </p>
          </Link>

          <div className="glass-card p-6 rounded-xl">
            <div className="flex items-center justify-between mb-4">
              <p className="text-muted-foreground">Event Balance</p>
              <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-success" />
              </div>
            </div>
            <p className="text-3xl font-bold">${totalBalance.toLocaleString()}</p>
            <p className={`text-sm flex items-center gap-1 mt-2 ${totalBalance >= 0 ? 'text-success' : 'text-destructive'}`}>
              {totalBalance >= 0 ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
              {totalBalance >= 0 ? 'Across events' : 'You owe money'}
            </p>
          </div>

          <div className="glass-card p-6 rounded-xl">
            <div className="flex items-center justify-between mb-4">
              <p className="text-muted-foreground">Active Events</p>
              <div className="w-10 h-10 rounded-lg bg-info/10 flex items-center justify-center">
                <Calendar className="w-5 h-5 text-info" />
              </div>
            </div>
            <p className="text-3xl font-bold">{activeEvents}</p>
            <p className="text-sm text-muted-foreground mt-2">
              {events.length - activeEvents} completed
            </p>
          </div>

          <div className="glass-card p-6 rounded-xl">
            <div className="flex items-center justify-between mb-4">
              <p className="text-muted-foreground">Your Expenses</p>
              <div className="w-10 h-10 rounded-lg bg-warning/10 flex items-center justify-center">
                <PieChart className="w-5 h-5 text-warning" />
              </div>
            </div>
            <p className="text-3xl font-bold">${(summary?.total_expense_amount || 0).toLocaleString()}</p>
            <p className="text-sm text-muted-foreground mt-2">{summary?.expense_count || 0} expenses paid</p>
          </div>
        </motion.div>

        {/* Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex flex-wrap gap-4 mb-8"
        >
          <Link to="/events/create">
            <Button variant="gradient" size="lg">
              <Plus className="w-5 h-5" />
              Create New Event
            </Button>
          </Link>
          <Button variant="outline" size="lg" onClick={() => setShowJoinModal(true)}>
            <Copy className="w-5 h-5" />
            Join with Code
          </Button>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Events List */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="lg:col-span-2"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-display font-semibold">Your Events</h2>
            </div>

            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
              </div>
            ) : events.length === 0 ? (
              <div className="glass-card p-8 rounded-xl text-center">
                <Users className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">No events yet</h3>
                <p className="text-muted-foreground mb-4">
                  Create your first event or join one with a code.
                </p>
                <div className="flex gap-3 justify-center">
                  <Link to="/events/create">
                    <Button variant="gradient">
                      <Plus className="w-4 h-4" />
                      Create Event
                    </Button>
                  </Link>
                  <Button variant="outline" onClick={() => setShowJoinModal(true)}>
                    <Copy className="w-4 h-4" />
                    Join Event
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {events.map((event, index) => (
                  <motion.div
                    key={event._id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.4 + index * 0.1 }}
                  >
                    <Link to={`/events/${event._id}`}>
                      <div className="glass-card p-6 rounded-xl hover-lift cursor-pointer group">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div
                              className={`w-14 h-14 rounded-xl flex items-center justify-center ${
                                event.status === 'active'
                                  ? 'gradient-primary'
                                  : 'bg-muted'
                              }`}
                            >
                              <Users className="w-6 h-6 text-primary-foreground" />
                            </div>
                            <div>
                              <h3 className="font-semibold text-lg group-hover:text-primary transition-colors">
                                {event.name}
                              </h3>
                              <p className="text-sm text-muted-foreground">
                                {event.participants?.length || 1} members • {event.start_date || 'No date set'}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-6">
                            <div className="text-right">
                              <p className="text-sm text-muted-foreground">Total Pool</p>
                              <p className="font-semibold text-lg">
                                ₹{(event.total_pool || 0).toLocaleString()}
                              </p>
                            </div>
                            <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
                          </div>
                        </div>

                        {event.status === 'active' && event.total_pool > 0 && (
                          <div className="mt-4 pt-4 border-t border-border">
                            <div className="flex items-center justify-between text-sm">
                              <span className="text-muted-foreground">Total Spent</span>
                              <span className="font-medium">
                                ₹{(event.total_spent || 0).toLocaleString()}
                              </span>
                            </div>
                            <div className="w-full h-2 bg-background-surface rounded-full mt-2 overflow-hidden">
                              <div
                                className="h-full gradient-primary rounded-full"
                                style={{
                                  width: `${event.total_pool > 0 ? (event.total_spent / event.total_pool) * 100 : 0}%`,
                                }}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    </Link>
                  </motion.div>
                ))}

                {/* Pagination */}
                {pagination && pagination.total_pages > 1 && (
                  <div className="flex items-center justify-between mt-6 pt-4 border-t border-border">
                    <p className="text-sm text-muted-foreground">
                      Page {pagination.page} of {pagination.total_pages} ({pagination.total} events)
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                        disabled={!pagination.has_prev}
                      >
                        <ChevronLeft className="w-4 h-4" />
                        Prev
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(prev => prev + 1)}
                        disabled={!pagination.has_next}
                      >
                        Next
                        <ChevronRight className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </motion.div>

          {/* Recent Activity */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            {/* Wellness Summary Card */}
            <div className="mb-4">
              <Link to="/wellness">
                <WellnessCard compact />
              </Link>
            </div>

            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-display font-semibold">Recent Activity</h2>
            </div>

            <div className="glass-card rounded-xl p-4">
              {recentActivity.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No recent activity yet
                </p>
              ) : (
                <div className="space-y-4">
                  {recentActivity.map((activity) => (
                    <Link
                      key={activity._id}
                      to={`/events/${activity.event_id}`}
                      className="flex items-center gap-3 p-2 rounded-lg hover:bg-accent/50 transition-colors"
                    >
                      <div
                        className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          activity.type === 'deposit'
                            ? 'bg-success/10'
                            : 'bg-destructive/10'
                        }`}
                      >
                        {activity.type === 'deposit' ? (
                          <ArrowUpRight className="w-5 h-5 text-success" />
                        ) : (
                          <ArrowDownRight className="w-5 h-5 text-destructive" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{activity.description || 'Expense'}</p>
                        <p className="text-xs text-muted-foreground">{activity.event_name}</p>
                      </div>
                      <div className="text-right">
                        <p
                          className={`font-semibold ${
                            activity.type === 'deposit'
                              ? 'text-success'
                              : 'text-destructive'
                          }`}
                        >
                          {activity.type === 'deposit' ? '+' : '-'}₹
                          {activity.amount.toLocaleString()}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {dayjs(activity.created_at).fromNow()}
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </div>

        {/* Analytics Charts */}
        {analytics && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="mt-8"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-display font-semibold">Analytics</h2>
              {/* Weekly Comparison */}
              {analytics.weekly_comparison && (
                <div className="flex items-center gap-4 text-sm">
                  <div className="text-right">
                    <p className="text-muted-foreground">This Week</p>
                    <p className="font-semibold">₹{analytics.weekly_comparison.this_week.toLocaleString()}</p>
                  </div>
                  <div className={`flex items-center gap-1 px-3 py-1 rounded-full ${
                    analytics.weekly_comparison.change_percent >= 0 
                      ? 'bg-destructive/10 text-destructive' 
                      : 'bg-success/10 text-success'
                  }`}>
                    {analytics.weekly_comparison.change_percent >= 0 ? (
                      <TrendingUp className="w-4 h-4" />
                    ) : (
                      <TrendingDown className="w-4 h-4" />
                    )}
                    <span className="font-medium">
                      {Math.abs(analytics.weekly_comparison.change_percent)}%
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="glass-card p-4 rounded-xl">
                <p className="text-xs text-muted-foreground mb-1">Total Expenses</p>
                <p className="text-xl font-bold">₹{(analytics.total_expenses || 0).toLocaleString()}</p>
              </div>
              <div className="glass-card p-4 rounded-xl">
                <p className="text-xs text-muted-foreground mb-1">Avg. Expense</p>
                <p className="text-xl font-bold">₹{(analytics.avg_expense || 0).toLocaleString()}</p>
              </div>
              <div className="glass-card p-4 rounded-xl">
                <p className="text-xs text-muted-foreground mb-1">Transactions</p>
                <p className="text-xl font-bold">{analytics.expense_count || 0}</p>
              </div>
              <div className="glass-card p-4 rounded-xl">
                <p className="text-xs text-muted-foreground mb-1">Categories</p>
                <p className="text-xl font-bold">{analytics.category_totals?.length || 0}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Category Chart with Toggle */}
              <div className="glass-card p-6 rounded-xl">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">Spending by Category</h3>
                  <div className="flex gap-1 bg-background-surface rounded-lg p-1">
                    <button
                      onClick={() => setActiveChart('pie')}
                      className={`p-2 rounded-md transition-colors ${activeChart === 'pie' ? 'bg-primary text-primary-foreground' : 'hover:bg-accent'}`}
                    >
                      <PieChart className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setActiveChart('bar')}
                      className={`p-2 rounded-md transition-colors ${activeChart === 'bar' ? 'bg-primary text-primary-foreground' : 'hover:bg-accent'}`}
                    >
                      <BarChart3 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                
                {analytics.category_totals && analytics.category_totals.length > 0 ? (
                  <>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        {activeChart === 'pie' ? (
                          <RechartsPieChart>
                            <Pie
                              data={analytics.category_totals}
                              dataKey="total"
                              nameKey="category_name"
                              cx="50%"
                              cy="50%"
                              innerRadius={50}
                              outerRadius={80}
                              paddingAngle={2}
                              label={({ category_name, percent }) =>
                                percent > 0.05 ? `${(percent * 100).toFixed(0)}%` : ''
                              }
                            >
                              {analytics.category_totals.map((entry) => (
                                <Cell key={entry.category_id} fill={entry.color} />
                              ))}
                            </Pie>
                            <Tooltip
                              formatter={(value: number, name: string) => [`₹${value.toLocaleString()}`, name]}
                              contentStyle={{
                                backgroundColor: 'hsl(var(--card))',
                                border: '1px solid hsl(var(--border))',
                                borderRadius: '8px',
                              }}
                            />
                          </RechartsPieChart>
                        ) : (
                          <BarChart data={analytics.category_totals} layout="vertical">
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                            <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${v >= 1000 ? `${(v/1000).toFixed(0)}k` : v}`} />
                            <YAxis type="category" dataKey="category_name" tick={{ fontSize: 11 }} width={90} />
                            <Tooltip
                              formatter={(value: number) => [`₹${value.toLocaleString()}`, 'Amount']}
                              contentStyle={{
                                backgroundColor: 'hsl(var(--card))',
                                border: '1px solid hsl(var(--border))',
                                borderRadius: '8px',
                              }}
                            />
                            <Bar dataKey="total" radius={[0, 4, 4, 0]}>
                              {analytics.category_totals.map((entry) => (
                                <Cell key={entry.category_id} fill={entry.color} />
                              ))}
                            </Bar>
                          </BarChart>
                        )}
                      </ResponsiveContainer>
                    </div>
                    <div className="mt-4 grid grid-cols-2 gap-2">
                      {analytics.category_totals.slice(0, 6).map((cat) => (
                        <div key={cat.category_id} className="flex items-center gap-2 text-sm p-2 rounded-lg hover:bg-accent/50 transition-colors">
                          <span className="text-lg">{cat.icon}</span>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium truncate">{cat.category_name}</p>
                            <p className="text-xs text-muted-foreground">{cat.count} expenses</p>
                          </div>
                          <p className="font-semibold" style={{ color: cat.color }}>
                            ₹{cat.total.toLocaleString()}
                          </p>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="h-64 flex flex-col items-center justify-center text-muted-foreground">
                    <PieChart className="w-12 h-12 mb-4 opacity-50" />
                    <p>No expense data yet</p>
                    <p className="text-sm">Add expenses to see category breakdown</p>
                  </div>
                )}
              </div>

              {/* Daily/Monthly Expenses Chart */}
              <div className="glass-card p-6 rounded-xl">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">Expense Trends</h3>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Activity className="w-4 h-4" />
                    Last 30 days
                  </div>
                </div>
                
                {analytics.daily_expenses && analytics.daily_expenses.some(d => d.total > 0) ? (
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={analytics.daily_expenses}>
                        <defs>
                          <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis
                          dataKey="date"
                          tick={{ fontSize: 11 }}
                          tickFormatter={(value) => dayjs(value).format('D')}
                          stroke="hsl(var(--muted-foreground))"
                        />
                        <YAxis
                          tick={{ fontSize: 11 }}
                          tickFormatter={(value) => `₹${value >= 1000 ? `${(value / 1000).toFixed(0)}k` : value}`}
                          stroke="hsl(var(--muted-foreground))"
                        />
                        <Tooltip
                          formatter={(value: number) => [`₹${value.toLocaleString()}`, 'Spent']}
                          labelFormatter={(label) => dayjs(label).format('MMMM D, YYYY')}
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            border: '1px solid hsl(var(--border))',
                            borderRadius: '8px',
                          }}
                        />
                        <Area
                          type="monotone"
                          dataKey="total"
                          stroke="hsl(var(--primary))"
                          strokeWidth={2}
                          fillOpacity={1}
                          fill="url(#colorTotal)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-64 flex flex-col items-center justify-center text-muted-foreground">
                    <Activity className="w-12 h-12 mb-4 opacity-50" />
                    <p>No expense trends yet</p>
                    <p className="text-sm">Start adding expenses to see trends</p>
                  </div>
                )}

                {/* Top Events */}
                {analytics.top_events && analytics.top_events.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-border">
                    <p className="text-sm font-medium mb-2">Top Spending Events</p>
                    <div className="space-y-2">
                      {analytics.top_events.slice(0, 3).map((event, index) => (
                        <Link
                          key={event.event_id}
                          to={`/events/${event.event_id}`}
                          className="flex items-center justify-between p-2 rounded-lg hover:bg-accent/50 transition-colors"
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-muted-foreground w-5">#{index + 1}</span>
                            <span className="text-sm font-medium truncate">{event.event_name}</span>
                          </div>
                          <span className="text-sm font-semibold text-primary">₹{event.total.toLocaleString()}</span>
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </main>

      {/* Join Event Modal */}
      {showJoinModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-card p-6 rounded-xl w-full max-w-md"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-display font-bold">Join Event</h3>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowJoinModal(false)}
              >
                <X className="w-5 h-5" />
              </Button>
            </div>
            <p className="text-muted-foreground mb-6">
              Enter the invite code shared by the event organizer.
            </p>
            <div className="space-y-4">
              <Input
                placeholder="Enter invite code (e.g., ABC123)"
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                className="h-12 text-center text-lg uppercase tracking-widest"
                maxLength={8}
              />
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => {
                    setShowJoinModal(false);
                    setJoinCode('');
                  }}
                >
                  Cancel
                </Button>
                <Button
                  variant="gradient"
                  className="flex-1"
                  onClick={handleJoinEvent}
                  disabled={!joinCode.trim() || isJoining}
                >
                  {isJoining ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    'Join Event'
                  )}
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
