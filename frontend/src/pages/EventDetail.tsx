import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Wallet,
  ArrowLeft,
  Users,
  Plus,
  ArrowUpRight,
  ArrowDownRight,
  Copy,
  Share2,
  Settings,
  CheckCircle2,
  Clock,
  AlertCircle,
  PieChart,
  TrendingUp,
  Calendar,
  Loader2,
  X,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { eventsAPI, expensesAPI, Event, Expense } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';

const categoryColors: Record<string, string> = {
  Accommodation: 'bg-blue-500/20 text-blue-400',
  Food: 'bg-orange-500/20 text-orange-400',
  Activities: 'bg-purple-500/20 text-purple-400',
  Transport: 'bg-green-500/20 text-green-400',
  Shopping: 'bg-pink-500/20 text-pink-400',
  Other: 'bg-gray-500/20 text-gray-400',
};

export default function EventDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuthStore();
  
  const [activeTab, setActiveTab] = useState<'expenses' | 'members' | 'analytics'>('expenses');
  const [isLoading, setIsLoading] = useState(true);
  const [event, setEvent] = useState<Event | null>(null);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [inviteCode, setInviteCode] = useState('');
  
  // Deposit modal state
  const [showDepositModal, setShowDepositModal] = useState(false);
  const [depositAmount, setDepositAmount] = useState('');
  const [isDepositing, setIsDepositing] = useState(false);

  useEffect(() => {
    const fetchEventData = async () => {
      if (!id) return;
      
      setIsLoading(true);
      try {
        const [eventRes, expensesRes] = await Promise.all([
          eventsAPI.get(id),
          expensesAPI.getByEvent(id),
        ]);
        
        setEvent(eventRes.data.event);
        setExpenses(expensesRes.data.expenses || []);
        
        // Try to get invite code
        try {
          const inviteRes = await eventsAPI.getInviteLink(id);
          setInviteCode(inviteRes.data.invite_code);
        } catch {
          // Invite code may not be available
        }
      } catch (error: any) {
        console.error('Failed to fetch event:', error);
        if (error.response?.status === 404) {
          toast({
            title: 'Event not found',
            description: 'This event may have been deleted.',
            variant: 'destructive',
          });
          navigate('/dashboard');
        } else if (error.response?.status === 403) {
          toast({
            title: 'Access denied',
            description: 'You are not a participant of this event.',
            variant: 'destructive',
          });
          navigate('/dashboard');
        }
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchEventData();
  }, [id, navigate, toast]);

  const copyCode = () => {
    if (inviteCode) {
      navigator.clipboard.writeText(inviteCode);
      toast({
        title: 'Code copied!',
        description: 'Share this code with others to join.',
      });
    }
  };

  const handleDeposit = async () => {
    if (!depositAmount || !id) return;
    
    setIsDepositing(true);
    try {
      await eventsAPI.deposit(id, parseFloat(depositAmount));
      toast({
        title: 'Deposit successful!',
        description: `₹${depositAmount} has been added to the pool.`,
      });
      setShowDepositModal(false);
      setDepositAmount('');
      
      // Refresh event data
      const eventRes = await eventsAPI.get(id);
      setEvent(eventRes.data.event);
    } catch (error: any) {
      toast({
        title: 'Deposit failed',
        description: error.response?.data?.error || 'Something went wrong',
        variant: 'destructive',
      });
    } finally {
      setIsDepositing(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!event) {
    return null;
  }

  const totalSpent = event.total_spent || 0;
  const totalPool = event.total_pool || 0;
  const participants = event.participants || [];
  
  // Find current user's participant record
  const currentUserParticipant = participants.find(
    (p) => p.user_id === user?.id
  );
  const yourBalance = currentUserParticipant?.balance || 0;
  const yourDeposit = currentUserParticipant?.deposit_amount || 0;

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/dashboard">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <div>
              <h1 className="font-display font-bold text-lg">{event.name}</h1>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Calendar className="w-4 h-4" />
                <span>
                  {event.start_date || 'No start date'} - {event.end_date || 'No end date'}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {inviteCode && (
              <Button variant="ghost" size="icon" onClick={copyCode}>
                <Copy className="w-5 h-5" />
              </Button>
            )}
            <Button variant="ghost" size="icon">
              <Share2 className="w-5 h-5" />
            </Button>
            <Button variant="ghost" size="icon">
              <Settings className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </nav>

      <main className="container mx-auto px-6 py-8">
        {/* Stats Cards */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8"
        >
          <div className="glass-card p-5 rounded-xl">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg gradient-primary flex items-center justify-center">
                <Wallet className="w-6 h-6 text-primary-foreground" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Pool Balance</p>
                <p className="text-2xl font-bold">₹{totalPool.toLocaleString()}</p>
              </div>
            </div>
          </div>

          <div className="glass-card p-5 rounded-xl">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-destructive/10 flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-destructive" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Spent</p>
                <p className="text-2xl font-bold">₹{totalSpent.toLocaleString()}</p>
              </div>
            </div>
          </div>

          <div className="glass-card p-5 rounded-xl">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-info/10 flex items-center justify-center">
                <Users className="w-6 h-6 text-info" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Members</p>
                <p className="text-2xl font-bold">{participants.length}</p>
              </div>
            </div>
          </div>

          <div className="glass-card p-5 rounded-xl">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-warning/10 flex items-center justify-center">
                <PieChart className="w-6 h-6 text-warning" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Expenses</p>
                <p className="text-2xl font-bold">{expenses.length}</p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Your Balance Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-card-glow p-6 rounded-xl mb-8"
        >
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <p className="text-muted-foreground mb-1">Your Balance</p>
              <p className="text-4xl font-display font-bold">
                ₹{yourBalance.toLocaleString()}
              </p>
              {yourDeposit > 0 && (
                <div className="flex items-center gap-2 mt-2">
                  <div className="w-full max-w-xs h-2 bg-background rounded-full overflow-hidden">
                    <div
                      className="h-full gradient-primary rounded-full"
                      style={{
                        width: `${Math.min(100, (yourBalance / yourDeposit) * 100)}%`,
                      }}
                    />
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {Math.round((yourBalance / yourDeposit) * 100)}% remaining
                  </span>
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <Link to={`/events/${id}/expense`}>
                <Button variant="gradient" size="lg">
                  <Plus className="w-5 h-5" />
                  Add Expense
                </Button>
              </Link>
              <Button variant="outline" size="lg" onClick={() => setShowDepositModal(true)}>
                <ArrowUpRight className="w-5 h-5" />
                Deposit
              </Button>
            </div>
          </div>
        </motion.div>

        {/* Invite Code Display */}
        {inviteCode && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="glass-card p-4 rounded-xl mb-8 flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <Share2 className="w-5 h-5 text-primary" />
              <span className="text-muted-foreground">Invite Code:</span>
              <span className="font-mono font-bold text-lg tracking-widest">{inviteCode}</span>
            </div>
            <Button variant="ghost" size="sm" onClick={copyCode}>
              <Copy className="w-4 h-4 mr-2" />
              Copy
            </Button>
          </motion.div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-border">
          {(['expenses', 'members', 'analytics'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 font-medium capitalize transition-colors relative ${
                activeTab === tab
                  ? 'text-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab}
              {activeTab === tab && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute bottom-0 left-0 right-0 h-0.5 gradient-primary"
                />
              )}
            </button>
          ))}
        </div>

        {/* Expenses Tab */}
        {activeTab === 'expenses' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-4"
          >
            {expenses.length === 0 ? (
              <div className="glass-card p-8 rounded-xl text-center">
                <ArrowDownRight className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">No expenses yet</h3>
                <p className="text-muted-foreground mb-4">
                  Start tracking expenses for this event.
                </p>
                <Link to={`/events/${id}/expense`}>
                  <Button variant="gradient">
                    <Plus className="w-4 h-4" />
                    Add First Expense
                  </Button>
                </Link>
              </div>
            ) : (
              expenses.map((expense, index) => (
                <motion.div
                  key={expense._id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="glass-card p-5 rounded-xl hover-lift cursor-pointer"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-lg bg-destructive/10 flex items-center justify-center">
                        <ArrowDownRight className="w-6 h-6 text-destructive" />
                      </div>
                      <div>
                        <h3 className="font-semibold">{expense.description || 'Expense'}</h3>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <span>
                            {new Date(expense.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${categoryColors.Other}`}>
                        {expense.split_type}
                      </span>
                      <div className="text-right">
                        <p className="font-bold text-lg">₹{expense.amount.toLocaleString()}</p>
                        <p className="text-xs text-muted-foreground">
                          {expense.split_type === 'equal' ? 'Split equally' : 'Custom split'}
                        </p>
                      </div>
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center ${
                          expense.status === 'verified'
                            ? 'bg-success/10 text-success'
                            : 'bg-warning/10 text-warning'
                        }`}
                      >
                        {expense.status === 'verified' ? (
                          <CheckCircle2 className="w-4 h-4" />
                        ) : (
                          <Clock className="w-4 h-4" />
                        )}
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))
            )}
          </motion.div>
        )}

        {/* Members Tab */}
        {activeTab === 'members' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid grid-cols-1 md:grid-cols-2 gap-4"
          >
            {participants.length === 0 ? (
              <div className="col-span-2 glass-card p-8 rounded-xl text-center">
                <Users className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">No other members yet</h3>
                <p className="text-muted-foreground">
                  Share the invite code to add members.
                </p>
              </div>
            ) : (
              participants.map((member, index) => (
                <motion.div
                  key={member._id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="glass-card p-5 rounded-xl"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 rounded-full gradient-primary flex items-center justify-center text-lg font-bold text-primary-foreground">
                      {member.user_name?.charAt(0) || 'U'}
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-lg">
                        {member.user_name}
                        {member.user_id === user?.id && (
                          <span className="ml-2 text-xs bg-primary/20 text-primary px-2 py-0.5 rounded-full">
                            You
                          </span>
                        )}
                      </h3>
                      <p className="text-sm text-muted-foreground">
                        Deposited: ₹{member.deposit_amount.toLocaleString()}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-muted-foreground">Balance</p>
                      <p className="text-xl font-bold">₹{member.balance.toLocaleString()}</p>
                    </div>
                  </div>

                  {member.deposit_amount > 0 && (
                    <div className="mt-4">
                      <div className="w-full h-2 bg-background rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            member.balance / member.deposit_amount > 0.3
                              ? 'gradient-primary'
                              : 'bg-warning'
                          }`}
                          style={{ width: `${Math.min(100, (member.balance / member.deposit_amount) * 100)}%` }}
                        />
                      </div>
                      {member.balance / member.deposit_amount <= 0.3 && (
                        <div className="flex items-center gap-1 mt-2 text-warning text-xs">
                          <AlertCircle className="w-3 h-3" />
                          <span>Low balance</span>
                        </div>
                      )}
                    </div>
                  )}
                </motion.div>
              ))
            )}
          </motion.div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid grid-cols-1 md:grid-cols-2 gap-6"
          >
            <div className="glass-card p-6 rounded-xl">
              <h3 className="font-display font-semibold text-lg mb-4">Event Summary</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-background rounded-lg">
                  <span className="text-muted-foreground">Total Pool</span>
                  <span className="font-semibold">₹{totalPool.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between p-4 bg-background rounded-lg">
                  <span className="text-muted-foreground">Total Spent</span>
                  <span className="font-semibold">₹{totalSpent.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between p-4 bg-background rounded-lg">
                  <span className="text-muted-foreground">Remaining</span>
                  <span className="font-semibold text-success">
                    ₹{(totalPool - totalSpent).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>

            <div className="glass-card p-6 rounded-xl">
              <h3 className="font-display font-semibold text-lg mb-4">Event Rules</h3>
              <div className="space-y-4">
                {event.rules?.spending_limit && (
                  <div className="flex items-center justify-between p-4 bg-background rounded-lg">
                    <span className="text-muted-foreground">Spending Limit</span>
                    <span className="font-semibold">
                      ₹{event.rules.spending_limit.toLocaleString()}
                    </span>
                  </div>
                )}
                {event.rules?.auto_approve_under && (
                  <div className="flex items-center justify-between p-4 bg-background rounded-lg">
                    <span className="text-muted-foreground">Auto-approve Under</span>
                    <span className="font-semibold">
                      ₹{event.rules.auto_approve_under.toLocaleString()}
                    </span>
                  </div>
                )}
                <div className="flex items-center justify-between p-4 bg-background rounded-lg">
                  <span className="text-muted-foreground">Approval Required</span>
                  <span className="font-semibold">
                    {event.rules?.approval_required ? 'Yes' : 'No'}
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </main>

      {/* Deposit Modal */}
      {showDepositModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-card p-6 rounded-xl w-full max-w-md"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-display font-bold">Deposit Funds</h3>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowDepositModal(false)}
              >
                <X className="w-5 h-5" />
              </Button>
            </div>
            <p className="text-muted-foreground mb-6">
              Add money to the event pool.
            </p>
            <div className="space-y-4">
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">₹</span>
                <Input
                  type="number"
                  placeholder="Enter amount"
                  value={depositAmount}
                  onChange={(e) => setDepositAmount(e.target.value)}
                  className="h-12 pl-8 text-lg"
                />
              </div>
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => {
                    setShowDepositModal(false);
                    setDepositAmount('');
                  }}
                >
                  Cancel
                </Button>
                <Button
                  variant="gradient"
                  className="flex-1"
                  onClick={handleDeposit}
                  disabled={!depositAmount || isDepositing}
                >
                  {isDepositing ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    'Deposit'
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
