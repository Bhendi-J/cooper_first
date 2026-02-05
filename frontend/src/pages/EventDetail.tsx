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
  LogOut,
  Crown,
  RefreshCw,
  Flag,
  QrCode,
  Download,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { eventsAPI, expensesAPI, Event, Expense, PendingApproval } from '@/lib/api';
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

  const [activeTab, setActiveTab] = useState<'expenses' | 'members' | 'analytics' | 'approvals'>('expenses');
  const [isLoading, setIsLoading] = useState(true);
  const [event, setEvent] = useState<Event | null>(null);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [inviteCode, setInviteCode] = useState('');

  // Deposit modal state
  const [showDepositModal, setShowDepositModal] = useState(false);
  const [depositAmount, setDepositAmount] = useState('');
  const [isDepositing, setIsDepositing] = useState(false);
  
  // Leave event state
  const [showLeaveModal, setShowLeaveModal] = useState(false);
  
  // QR code modal state
  const [showQRModal, setShowQRModal] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);
  
  // Delete event state (for creator)
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  
  // End event state (for creator)
  const [showEndModal, setShowEndModal] = useState(false);
  const [isEnding, setIsEnding] = useState(false);
  
  // Transfer ownership state
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [transferTargetId, setTransferTargetId] = useState<string | null>(null);
  const [transferTargetName, setTransferTargetName] = useState('');
  const [isTransferring, setIsTransferring] = useState(false);
  
  // Approvals state (for creator only)
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [isLoadingApprovals, setIsLoadingApprovals] = useState(false);
  const [processingApprovalId, setProcessingApprovalId] = useState<string | null>(null);

  useEffect(() => {
    const fetchEventData = async () => {
      if (!id) return;

      setIsLoading(true);
      try {
        const [eventRes, expensesRes] = await Promise.all([
          eventsAPI.get(id),
          expensesAPI.getByEvent(id),
        ]);

        const eventData = eventRes.data?.event;
        if (!eventData) {
          console.error('Event data is null/undefined in response:', eventRes.data);
          toast({
            title: 'Error loading event',
            description: 'Event data could not be loaded.',
            variant: 'destructive',
          });
          navigate('/dashboard');
          return;
        }
        setEvent(eventData);
        setExpenses(expensesRes.data?.expenses || []);

        // Fetch pending approvals if user is creator
        if (eventData.creator_id === user?.id) {
          try {
            const approvalsRes = await expensesAPI.getPendingApprovals(id);
            setPendingApprovals(approvalsRes.data.pending_approvals || []);
          } catch {
            // Non-critical error
          }
        }

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
  }, [id, navigate, toast, user?.id]);

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
      // Use Finternet gateway for deposit
      const response = await eventsAPI.depositWithFinternet(id, parseFloat(depositAmount));
      
      // Show confirmation toast with tx details
      toast({
        title: '✓ Transaction Initiated',
        description: `TX: ${response.data.transaction_hash?.slice(0, 12)}... | Redirecting to gateway...`,
      });
      
      // Store info for callback
      localStorage.setItem('finternet_intent_id', response.data.intent_id);
      localStorage.setItem('finternet_return_url', `/events/${id}`);
      localStorage.setItem('pending_deposit_event_id', id);
      localStorage.setItem('pending_deposit_amount', depositAmount);
      
      // Redirect to payment gateway
      window.location.href = response.data.payment_url;
      
    } catch (error: any) {
      console.error('Deposit error:', error);
      toast({
        title: 'Deposit failed',
        description: error.response?.data?.error || error.message || 'Failed to process deposit. Please try again.',
        variant: 'destructive',
      });
      setIsDepositing(false);
      setShowDepositModal(false);
      setDepositAmount('');
    }
  };

  const handleLeaveEvent = async () => {
    if (!id) return;

    setIsLeaving(true);
    
    try {
      const response = await eventsAPI.leave(id);
      
      toast({
        title: 'Left event successfully',
        description: response.data.amount_withdrawn > 0 
          ? `₹${response.data.amount_withdrawn.toLocaleString()} has been withdrawn from the pool.`
          : 'You have left the event.',
      });
      
      // Navigate back to dashboard
      navigate('/dashboard');
      
    } catch (error: any) {
      console.error('Leave event error:', error);
      toast({
        title: 'Cannot leave event',
        description: error.response?.data?.error || error.message || 'Failed to leave event. Please try again.',
        variant: 'destructive',
      });
      setIsLeaving(false);
      setShowLeaveModal(false);
    }
  };

  const handleDeleteEvent = async () => {
    if (!id) return;

    setIsDeleting(true);
    
    try {
      const response = await eventsAPI.delete(id);
      
      toast({
        title: 'Event deleted',
        description: `"${response.data.event_name}" has been permanently deleted.`,
      });
      
      // Navigate back to dashboard
      navigate('/dashboard');
      
    } catch (error: any) {
      console.error('Delete event error:', error);
      toast({
        title: 'Cannot delete event',
        description: error.response?.data?.error || error.message || 'Failed to delete event. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  const handleEndEvent = async () => {
    if (!id) return;

    setIsEnding(true);
    
    try {
      const response = await eventsAPI.end(id);
      
      // Show detailed settlement summary
      const settledCount = response.data.settlements.length;
      const totalReturned = response.data.settlements
        .filter(s => s.balance_returned > 0)
        .reduce((sum, s) => sum + s.balance_returned, 0);
      
      toast({
        title: '✓ Event Ended',
        description: `${settledCount} participants settled. $${totalReturned.toFixed(2)} distributed.`,
      });
      
      // Refresh event to show completed status
      const eventRes = await eventsAPI.get(id);
      if (eventRes.data?.event) {
        setEvent(eventRes.data.event);
      }
      setShowEndModal(false);
      
    } catch (error: any) {
      console.error('End event error:', error);
      toast({
        title: 'Cannot end event',
        description: error.response?.data?.error || error.message || 'Failed to end event. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsEnding(false);
    }
  };

  const handleTransferOwnership = async () => {
    if (!id || !transferTargetId) return;

    setIsTransferring(true);
    
    try {
      const response = await eventsAPI.transferOwnership(id, transferTargetId);
      
      toast({
        title: 'Ownership transferred',
        description: `${response.data.new_owner_name} is now the event owner.`,
      });
      
      // Refresh event data
      const eventRes = await eventsAPI.get(id);
      setEvent(eventRes.data.event);
      
      setShowTransferModal(false);
      setTransferTargetId(null);
      setTransferTargetName('');
      
    } catch (error: any) {
      console.error('Transfer ownership error:', error);
      toast({
        title: 'Transfer failed',
        description: error.response?.data?.error || error.message || 'Failed to transfer ownership.',
        variant: 'destructive',
      });
    } finally {
      setIsTransferring(false);
    }
  };

  const openTransferModal = (memberId: string, memberName: string) => {
    setTransferTargetId(memberId);
    setTransferTargetName(memberName);
    setShowTransferModal(true);
  };

  // Fetch pending approvals (creator only)
  const fetchPendingApprovals = async () => {
    if (!id || !event || event.creator_id !== user?.id) return;
    
    setIsLoadingApprovals(true);
    try {
      const response = await expensesAPI.getPendingApprovals(id);
      setPendingApprovals(response.data.pending_approvals || []);
    } catch (error) {
      console.error('Failed to fetch pending approvals:', error);
    } finally {
      setIsLoadingApprovals(false);
    }
  };

  // Handle approve expense
  const handleApproveExpense = async (expenseId: string) => {
    setProcessingApprovalId(expenseId);
    try {
      await expensesAPI.approve(expenseId);
      toast({
        title: '✓ Expense Approved',
        description: 'The expense has been approved and processed.',
      });
      // Refresh approvals and expenses
      await fetchPendingApprovals();
      try {
        const expensesRes = await expensesAPI.getByEvent(id!);
        setExpenses(expensesRes.data.expenses || []);
      } catch (e) {
        console.error('Failed to refresh expenses:', e);
      }
      // Refresh event data for updated totals
      try {
        const eventRes = await eventsAPI.get(id!);
        if (eventRes.data?.event) {
          setEvent(eventRes.data.event);
        }
      } catch (e) {
        console.error('Failed to refresh event:', e);
      }
    } catch (error: any) {
      toast({
        title: 'Approval failed',
        description: error.response?.data?.error || 'Failed to approve expense.',
        variant: 'destructive',
      });
    } finally {
      setProcessingApprovalId(null);
    }
  };

  // Handle reject expense
  const handleRejectExpense = async (expenseId: string, reason?: string) => {
    setProcessingApprovalId(expenseId);
    try {
      await expensesAPI.reject(expenseId, reason || 'Rejected by creator');
      toast({
        title: 'Expense Rejected',
        description: 'The expense has been rejected.',
      });
      await fetchPendingApprovals();
    } catch (error: any) {
      toast({
        title: 'Rejection failed',
        description: error.response?.data?.error || 'Failed to reject expense.',
        variant: 'destructive',
      });
    } finally {
      setProcessingApprovalId(null);
    }
  };

  // Fetch approvals when switching to approvals tab
  useEffect(() => {
    if (activeTab === 'approvals' && event?.creator_id === user?.id) {
      fetchPendingApprovals();
    }
  }, [activeTab, event?.creator_id, user?.id]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!event) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-4">
        <AlertCircle className="w-16 h-16 text-muted-foreground" />
        <h2 className="text-xl font-semibold text-foreground">Event not found</h2>
        <p className="text-muted-foreground">This event may have been deleted or you don't have access.</p>
        <Link to="/dashboard">
          <Button>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Button>
        </Link>
      </div>
    );
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
              <div className="flex items-center gap-2">
                <h1 className="font-display font-bold text-lg">{event.name}</h1>
                {event.status === 'completed' && (
                  <span className="px-2 py-0.5 text-xs font-medium bg-success/20 text-success rounded-full">
                    Completed
                  </span>
                )}
              </div>
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
        {/* Completed Event Banner */}
        {event.status === 'completed' && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-4 bg-success/10 border border-success/20 rounded-xl flex items-center gap-3"
          >
            <CheckCircle2 className="w-6 h-6 text-success" />
            <div>
              <p className="font-medium text-success">Event Completed</p>
              <p className="text-sm text-muted-foreground">
                This event has ended. All balances have been distributed to participants.
              </p>
            </div>
          </motion.div>
        )}

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
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">Pool Balance</p>
                  {event.creator_id === user?.id && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="w-6 h-6"
                      onClick={async () => {
                        try {
                          const res = await eventsAPI.recalculatePool(id!);
                          toast({
                            title: 'Pool recalculated',
                            description: `Pool: $${res.data.after.total_pool} | Spent: $${res.data.after.total_spent}`,
                          });
                          // Refresh event data
                          const eventRes = await eventsAPI.get(id!);
                          if (eventRes.data?.event) setEvent(eventRes.data.event);
                        } catch (e: any) {
                          toast({
                            title: 'Recalculation failed',
                            description: e.response?.data?.error || 'Failed to recalculate',
                            variant: 'destructive',
                          });
                        }
                      }}
                      title="Recalculate pool balances"
                    >
                      <RefreshCw className="w-3 h-3" />
                    </Button>
                  )}
                </div>
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

            <div className="flex gap-3 flex-wrap">
              {event.status !== 'completed' && (
                <>
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
                </>
              )}
              {event.creator_id === user?.id ? (
                <>
                  {event.status !== 'completed' && (
                    <Button 
                      variant="outline" 
                      size="lg" 
                      className="text-warning border-warning/50 hover:bg-warning/10"
                      onClick={() => setShowEndModal(true)}
                    >
                      <Flag className="w-5 h-5" />
                      End Event
                    </Button>
                  )}
                  <Button 
                    variant="ghost" 
                    size="lg" 
                    className="text-destructive hover:text-destructive hover:bg-destructive/10"
                    onClick={() => setShowDeleteModal(true)}
                  >
                    <X className="w-5 h-5" />
                    Delete Event
                  </Button>
                </>
              ) : (
                <Button 
                  variant="ghost" 
                  size="lg" 
                  className="text-destructive hover:text-destructive hover:bg-destructive/10"
                  onClick={() => setShowLeaveModal(true)}
                >
                  <LogOut className="w-5 h-5" />
                  Leave Event
                </Button>
              )}
            </div>
          </div>
        </motion.div>

        {/* Invite Code Display */}
        {inviteCode && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="glass-card p-4 rounded-xl mb-8"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Share2 className="w-5 h-5 text-primary" />
                <span className="text-muted-foreground">Invite Code:</span>
                <span className="font-mono font-bold text-lg tracking-widest">{inviteCode}</span>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={() => setShowQRModal(true)}>
                  <QrCode className="w-4 h-4 mr-2" />
                  QR
                </Button>
                <Button variant="ghost" size="sm" onClick={copyCode}>
                  <Copy className="w-4 h-4 mr-2" />
                  Copy
                </Button>
              </div>
            </div>
          </motion.div>
        )}

        {/* QR Code Modal */}
        {showQRModal && inviteCode && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="glass-card p-6 rounded-2xl max-w-sm w-full mx-4 text-center"
            >
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-bold">Scan to Join</h3>
                <Button variant="ghost" size="icon" onClick={() => setShowQRModal(false)}>
                  <X className="w-5 h-5" />
                </Button>
              </div>
              
              <div className="bg-white p-4 rounded-xl inline-block mx-auto mb-4">
                <img
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(`${window.location.origin}/join/${inviteCode}`)}&bgcolor=ffffff&color=000000&margin=10`}
                  alt="QR Code to join event"
                  className="w-48 h-48"
                />
              </div>
              
              <p className="text-sm text-muted-foreground mb-4">
                Scan this QR code with your phone camera to join <span className="font-semibold text-foreground">{event?.name}</span>
              </p>
              
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => {
                    const link = document.createElement('a');
                    link.href = `https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=${encodeURIComponent(`${window.location.origin}/join/${inviteCode}`)}&bgcolor=ffffff&color=000000&margin=20&format=png`;
                    link.download = `${event?.name?.replace(/\s+/g, '_') || 'event'}_QR.png`;
                    link.click();
                    toast({ title: 'QR Downloaded!', description: 'Share this QR code with your group.' });
                  }}
                >
                  <Download className="w-4 h-4 mr-2" />
                  Download
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => {
                    if (navigator.share) {
                      navigator.share({
                        title: event?.name || 'Join Event',
                        text: `Join "${event?.name}" on Cooper`,
                        url: `${window.location.origin}/join/${inviteCode}`,
                      });
                    } else {
                      navigator.clipboard.writeText(`${window.location.origin}/join/${inviteCode}`);
                      toast({ title: 'Link Copied!', description: 'Share link copied to clipboard.' });
                    }
                  }}
                >
                  <Share2 className="w-4 h-4 mr-2" />
                  Share
                </Button>
              </div>
            </motion.div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-border overflow-x-auto">
          {/* Regular tabs for everyone */}
          {(['expenses', 'members', 'analytics'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 font-medium capitalize transition-colors relative whitespace-nowrap ${activeTab === tab
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
          
          {/* Approvals tab - only for creator */}
          {event.creator_id === user?.id && (
            <button
              onClick={() => setActiveTab('approvals')}
              className={`px-4 py-3 font-medium capitalize transition-colors relative whitespace-nowrap flex items-center gap-2 ${activeTab === 'approvals'
                  ? 'text-foreground'
                  : 'text-muted-foreground hover:text-foreground'
                }`}
            >
              <span>Approvals</span>
              {pendingApprovals.length > 0 && (
                <span className="bg-primary text-primary-foreground text-xs font-bold px-2 py-0.5 rounded-full">
                  {pendingApprovals.length}
                </span>
              )}
              {activeTab === 'approvals' && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute bottom-0 left-0 right-0 h-0.5 gradient-primary"
                />
              )}
            </button>
          )}
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
                        className={`w-8 h-8 rounded-full flex items-center justify-center ${expense.status === 'verified'
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
                      <h3 className="font-semibold text-lg flex items-center gap-2">
                        {member.user_name}
                        {member.user_id === event?.creator_id && (
                          <Crown className="w-4 h-4 text-warning" title="Event Owner" />
                        )}
                        {member.user_id === user?.id && (
                          <span className="text-xs bg-primary/20 text-primary px-2 py-0.5 rounded-full">
                            You
                          </span>
                        )}
                      </h3>
                      <p className="text-sm text-muted-foreground">
                        Deposited: ₹{member.deposit_amount.toLocaleString()}
                      </p>
                    </div>
                    <div className="text-right flex items-center gap-3">
                      <div>
                        <p className="text-sm text-muted-foreground">Balance</p>
                        <p className="text-xl font-bold">₹{member.balance.toLocaleString()}</p>
                      </div>
                      {/* Transfer ownership button - only visible to creator for other members */}
                      {event?.creator_id === user?.id && member.user_id !== user?.id && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-warning hover:text-warning hover:bg-warning/10"
                          onClick={() => openTransferModal(member.user_id, member.user_name)}
                          title="Transfer ownership"
                        >
                          <Crown className="w-5 h-5" />
                        </Button>
                      )}
                    </div>
                  </div>

                  {member.deposit_amount > 0 && (
                    <div className="mt-4">
                      <div className="w-full h-2 bg-background rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${member.balance / member.deposit_amount > 0.3
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

        {/* Approvals Tab - Creator Only */}
        {activeTab === 'approvals' && event.creator_id === user?.id && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-4"
          >
            {isLoadingApprovals ? (
              <div className="glass-card p-8 rounded-xl text-center">
                <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary" />
                <p className="text-muted-foreground mt-4">Loading pending approvals...</p>
              </div>
            ) : pendingApprovals.length === 0 ? (
              <div className="glass-card p-8 rounded-xl text-center">
                <CheckCircle2 className="w-12 h-12 mx-auto text-success mb-4" />
                <h3 className="text-lg font-semibold mb-2">All caught up!</h3>
                <p className="text-muted-foreground">
                  No pending expense approvals at this time.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-display font-semibold text-lg">
                    Pending Approvals ({pendingApprovals.length})
                  </h3>
                  <Button variant="ghost" size="sm" onClick={fetchPendingApprovals}>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Refresh
                  </Button>
                </div>
                
                {pendingApprovals.map((approval) => (
                  <motion.div
                    key={approval._id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass-card p-4 rounded-xl border border-warning/30"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <Clock className="w-4 h-4 text-warning" />
                          <span className="text-warning text-sm font-medium">Pending Approval</span>
                        </div>
                        <p className="font-semibold text-lg mb-1">
                          {approval.description || 'Expense'}
                        </p>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span>By: {approval.payer_name || 'Unknown'}</span>
                          <span>•</span>
                          <span className="font-mono font-bold text-foreground">
                            ₹{approval.amount.toLocaleString()}
                          </span>
                        </div>
                        {approval.reason && (
                          <p className="text-xs text-muted-foreground mt-2 bg-background/50 p-2 rounded">
                            Reason: {approval.reason}
                          </p>
                        )}
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-destructive border-destructive/30 hover:bg-destructive/10"
                          onClick={() => handleRejectExpense(approval._id)}
                          disabled={processingApprovalId === approval._id}
                        >
                          {processingApprovalId === approval._id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <X className="w-4 h-4" />
                          )}
                        </Button>
                        <Button
                          variant="gradient"
                          size="sm"
                          onClick={() => handleApproveExpense(approval._id)}
                          disabled={processingApprovalId === approval._id}
                        >
                          {processingApprovalId === approval._id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <>
                              <CheckCircle2 className="w-4 h-4 mr-1" />
                              Approve
                            </>
                          )}
                        </Button>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </main>

      {/* Deposit Modal */}
      {showDepositModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-card p-6 rounded-xl w-full max-w-md border border-primary/20"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <Wallet className="w-4 h-4 text-primary" />
                </div>
                <h3 className="text-xl font-display font-bold">Deposit USDC</h3>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowDepositModal(false)}
              >
                <X className="w-5 h-5" />
              </Button>
            </div>
            
            {/* Network Info */}
            <div className="bg-background-surface rounded-lg p-3 mb-4 border border-border/50">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Network</span>
                <span className="font-mono text-primary">Sepolia Testnet</span>
              </div>
              <div className="flex items-center justify-between text-sm mt-2">
                <span className="text-muted-foreground">Token</span>
                <span className="font-mono">USDC (ERC-20)</span>
              </div>
              <div className="flex items-center justify-between text-sm mt-2">
                <span className="text-muted-foreground">Settlement</span>
                <span className="font-mono text-xs text-success">Instant ⚡</span>
              </div>
            </div>
            
            <div className="space-y-4">
              <div className="relative">
                <Input
                  type="number"
                  placeholder="0.00"
                  value={depositAmount}
                  onChange={(e) => setDepositAmount(e.target.value)}
                  className="h-14 pl-4 pr-20 text-2xl font-mono bg-background-surface border-border/50"
                />
                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground font-mono text-sm">
                  USDC
                </span>
              </div>
              
              {/* Quick amounts */}
              <div className="flex gap-2">
                {[50, 100, 250, 500].map((amt) => (
                  <Button
                    key={amt}
                    variant="outline"
                    size="sm"
                    className="flex-1 font-mono text-xs"
                    onClick={() => setDepositAmount(String(amt))}
                  >
                    {amt}
                  </Button>
                ))}
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
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      <span className="font-mono text-sm">Processing...</span>
                    </>
                  ) : (
                    <>
                      <span>Confirm Deposit</span>
                    </>
                  )}
                </Button>
              </div>
              
              {/* Powered by */}
              <div className="text-center text-xs text-muted-foreground mt-4">
                Powered by <span className="text-primary font-semibold">Finternet</span> Payment Gateway
              </div>
            </div>
          </motion.div>
        </div>
      )}

      {/* Leave Event Modal */}
      {showLeaveModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-card p-6 rounded-xl w-full max-w-md"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-display font-bold text-destructive">Leave Event</h3>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowLeaveModal(false)}
              >
                <X className="w-5 h-5" />
              </Button>
            </div>
            <div className="space-y-4">
              <p className="text-muted-foreground">
                Are you sure you want to leave <span className="font-semibold text-foreground">{event?.name}</span>?
              </p>
              
              {yourBalance > 0 && (
                <div className="p-4 bg-success/10 border border-success/20 rounded-lg">
                  <p className="text-success font-medium">
                    Your balance of ₹{yourBalance.toLocaleString()} will be withdrawn from the pool.
                  </p>
                </div>
              )}
              
              {yourBalance < 0 && (
                <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
                  <p className="text-destructive font-medium">
                    You have outstanding debts of ₹{Math.abs(yourBalance).toLocaleString()}. Please settle them before leaving.
                  </p>
                </div>
              )}
              
              <div className="flex gap-3 pt-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setShowLeaveModal(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={handleLeaveEvent}
                  disabled={isLeaving || yourBalance < 0}
                >
                  {isLeaving ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <>
                      <LogOut className="w-4 h-4 mr-2" />
                      Leave Event
                    </>
                  )}
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      )}

      {/* Delete Event Modal (Creator Only) */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-card p-6 rounded-xl w-full max-w-md"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-display font-bold text-destructive">Delete Event</h3>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowDeleteModal(false)}
              >
                <X className="w-5 h-5" />
              </Button>
            </div>
            <div className="space-y-4">
              <p className="text-muted-foreground">
                Are you sure you want to permanently delete <span className="font-semibold text-foreground">{event?.name}</span>?
              </p>
              
              <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
                <p className="text-destructive font-medium">
                  ⚠️ This action cannot be undone!
                </p>
                <ul className="text-sm text-muted-foreground mt-2 space-y-1">
                  <li>• All expenses will be deleted</li>
                  <li>• All participants will be notified</li>
                  <li>• Pool balances will be cleared</li>
                </ul>
              </div>
              
              <div className="flex gap-3 pt-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setShowDeleteModal(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={handleDeleteEvent}
                  disabled={isDeleting}
                >
                  {isDeleting ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <>
                      <X className="w-4 h-4 mr-2" />
                      Delete Event
                    </>
                  )}
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      )}

      {/* End Event Modal (Creator Only) */}
      {showEndModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-card p-6 rounded-xl w-full max-w-md"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-display font-bold text-warning flex items-center gap-2">
                <Flag className="w-5 h-5" />
                End Event
              </h3>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowEndModal(false)}
              >
                <X className="w-5 h-5" />
              </Button>
            </div>
            <div className="space-y-4">
              <p className="text-muted-foreground">
                End <span className="font-semibold text-foreground">{event?.name}</span> and distribute all balances?
              </p>
              
              <div className="p-4 bg-primary/10 border border-primary/20 rounded-lg">
                <p className="text-primary font-medium mb-3">
                  Settlement Summary
                </p>
                <div className="space-y-2 text-sm">
                  {participants.map((p) => (
                    <div key={p.user_id} className="flex justify-between items-center">
                      <span className="text-muted-foreground">
                        {p.user_name}
                        {p.user_id === user?.id && <span className="text-xs ml-1">(you)</span>}
                      </span>
                      <span className={p.balance >= 0 ? 'text-success' : 'text-destructive'}>
                        {p.balance >= 0 ? '+' : ''}${p.balance.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="border-t border-border mt-3 pt-3 flex justify-between font-medium">
                  <span>Total Pool</span>
                  <span>${totalPool.toFixed(2)}</span>
                </div>
              </div>
              
              <div className="p-3 bg-muted/50 rounded-lg text-sm text-muted-foreground">
                <p>✓ Each participant's remaining balance will be returned to them</p>
                <p>✓ Event will be marked as completed</p>
                <p>✓ No new expenses can be added</p>
              </div>
              
              <div className="flex gap-3 pt-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setShowEndModal(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="default"
                  className="flex-1 bg-warning hover:bg-warning/90 text-warning-foreground"
                  onClick={handleEndEvent}
                  disabled={isEnding}
                >
                  {isEnding ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <>
                      <Flag className="w-4 h-4 mr-2" />
                      End & Settle
                    </>
                  )}
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      )}

      {/* Transfer Ownership Modal */}
      {showTransferModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-card p-6 rounded-xl w-full max-w-md"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-display font-bold flex items-center gap-2">
                <Crown className="w-5 h-5 text-warning" />
                Transfer Ownership
              </h3>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => {
                  setShowTransferModal(false);
                  setTransferTargetId(null);
                  setTransferTargetName('');
                }}
              >
                <X className="w-5 h-5" />
              </Button>
            </div>
            <div className="space-y-4">
              <p className="text-muted-foreground">
                Are you sure you want to transfer ownership of <span className="font-semibold text-foreground">{event?.name}</span> to <span className="font-semibold text-foreground">{transferTargetName}</span>?
              </p>
              
              <div className="p-4 bg-warning/10 border border-warning/20 rounded-lg">
                <p className="text-warning font-medium text-sm">
                  ⚠️ This action cannot be undone. You will no longer be the owner of this event.
                </p>
              </div>
              
              <div className="flex gap-3 pt-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => {
                    setShowTransferModal(false);
                    setTransferTargetId(null);
                    setTransferTargetName('');
                  }}
                >
                  Cancel
                </Button>
                <Button
                  variant="default"
                  className="flex-1 bg-warning hover:bg-warning/90 text-warning-foreground"
                  onClick={handleTransferOwnership}
                  disabled={isTransferring}
                >
                  {isTransferring ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <>
                      <Crown className="w-4 h-4 mr-2" />
                      Transfer
                    </>
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
