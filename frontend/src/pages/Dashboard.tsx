import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuthStore } from '@/store/authStore';
import { eventsAPI, usersAPI, Event } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import {
  Wallet,
  Plus,
  Users,
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight,
  Bell,
  Settings,
  LogOut,
  Calendar,
  Copy,
  ChevronRight,
  PieChart,
  X,
  Loader2,
} from 'lucide-react';

// Mock recent activity (backend doesn't have this endpoint yet)
const mockRecentActivity = [
  { id: '1', type: 'expense', description: 'Hotel Booking', amount: 12000, event: 'Trip', time: '2h ago' },
  { id: '2', type: 'deposit', description: 'Someone deposited', amount: 5000, event: 'Trip', time: '4h ago' },
  { id: '3', type: 'expense', description: 'Dinner', amount: 3500, event: 'Trip', time: '6h ago' },
  { id: '4', type: 'deposit', description: 'You deposited', amount: 7500, event: 'Trip', time: '1d ago' },
];

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
  const [summary, setSummary] = useState<{ events: number; expenses: number } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [recentActivity] = useState(mockRecentActivity);

  // Fetch user's events on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const [eventsRes, summaryRes] = await Promise.all([
          eventsAPI.list(),
          usersAPI.getSummary(),
        ]);
        setEvents(eventsRes.data.events || []);
        setSummary(summaryRes.data);
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
    fetchData();
  }, [toast]);

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
  const totalBalance = events.reduce((acc, event) => acc + (event.total_pool || 0), 0);
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
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-destructive rounded-full" />
            </Button>

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
          className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8"
        >
          <div className="glass-card p-6 rounded-xl">
            <div className="flex items-center justify-between mb-4">
              <p className="text-muted-foreground">Your Total Balance</p>
              <div className="w-10 h-10 rounded-lg gradient-primary-subtle flex items-center justify-center">
                <Wallet className="w-5 h-5 text-primary" />
              </div>
            </div>
            <p className="text-3xl font-bold">₹{totalBalance.toLocaleString()}</p>
            <p className="text-sm text-success flex items-center gap-1 mt-2">
              <ArrowUpRight className="w-4 h-4" />
              Across all events
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
              <p className="text-muted-foreground">Total Expenses</p>
              <div className="w-10 h-10 rounded-lg bg-warning/10 flex items-center justify-center">
                <PieChart className="w-5 h-5 text-warning" />
              </div>
            </div>
            <p className="text-3xl font-bold">{summary?.expenses || 0}</p>
            <p className="text-sm text-muted-foreground mt-2">Expenses you've added</p>
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
              </div>
            )}
          </motion.div>

          {/* Recent Activity */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-display font-semibold">Recent Activity</h2>
            </div>

            <div className="glass-card rounded-xl p-4">
              <div className="space-y-4">
                {recentActivity.map((activity) => (
                  <div
                    key={activity.id}
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
                      <p className="font-medium truncate">{activity.description}</p>
                      <p className="text-xs text-muted-foreground">{activity.event}</p>
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
                      <p className="text-xs text-muted-foreground">{activity.time}</p>
                    </div>
                  </div>
                ))}
              </div>

              <p className="text-sm text-muted-foreground text-center mt-4 pt-4 border-t border-border">
                Activity data coming soon
              </p>
            </div>
          </motion.div>
        </div>
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
