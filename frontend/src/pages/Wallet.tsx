import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuthStore } from '@/store/authStore';
import { walletsAPI, WalletTransaction, usersAPI } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import {
  Wallet,
  ArrowUpRight,
  ArrowDownRight,
  ArrowUp,
  ArrowDown,
  RefreshCw,
  Send,
  Plus,
  Minus,
  ChevronLeft,
  Clock,
  DollarSign,
  CreditCard,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Loader2,
  X,
  Search,
} from 'lucide-react';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

// Transaction type icons and colors
const getTransactionIcon = (type: string, source?: string, purpose?: string) => {
  if (type === 'credit') {
    if (source === 'event_withdrawal' || source === 'event_settlement' || source === 'event_deleted') {
      return { icon: ArrowDownRight, color: 'text-success', bg: 'bg-success/10' };
    }
    if (source === 'transfer_in') {
      return { icon: ArrowDown, color: 'text-info', bg: 'bg-info/10' };
    }
    if (source === 'topup') {
      return { icon: Plus, color: 'text-success', bg: 'bg-success/10' };
    }
    return { icon: ArrowUpRight, color: 'text-success', bg: 'bg-success/10' };
  } else {
    if (purpose === 'expense_shortfall' || purpose === 'expense_shortfall_partial') {
      return { icon: AlertCircle, color: 'text-warning', bg: 'bg-warning/10' };
    }
    if (purpose === 'transfer_out') {
      return { icon: Send, color: 'text-info', bg: 'bg-info/10' };
    }
    if (purpose === 'withdrawal') {
      return { icon: Minus, color: 'text-destructive', bg: 'bg-destructive/10' };
    }
    return { icon: ArrowDownRight, color: 'text-destructive', bg: 'bg-destructive/10' };
  }
};

const getTransactionLabel = (tx: WalletTransaction) => {
  if (tx.type === 'credit') {
    switch (tx.source) {
      case 'event_withdrawal':
        return 'Event Withdrawal';
      case 'event_settlement':
        return 'Event Settlement';
      case 'event_deleted':
        return 'Event Deleted';
      case 'transfer_in':
        return 'Transfer Received';
      case 'topup':
        return 'Wallet Top-up';
      case 'refund':
        return 'Refund';
      default:
        return 'Credit';
    }
  } else {
    switch (tx.purpose) {
      case 'expense_shortfall':
      case 'expense_shortfall_partial':
        return 'Expense Coverage';
      case 'transfer_out':
        return 'Transfer Sent';
      case 'withdrawal':
        return 'Withdrawal';
      case 'debt_settlement':
        return 'Debt Payment';
      default:
        return 'Debit';
    }
  }
};

export default function WalletPage() {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { toast } = useToast();

  // State
  const [balance, setBalance] = useState<number>(0);
  const [transactions, setTransactions] = useState<WalletTransaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isTransacting, setIsTransacting] = useState(false);
  
  // Modal states
  const [showDepositModal, setShowDepositModal] = useState(false);
  const [showWithdrawModal, setShowWithdrawModal] = useState(false);
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [depositAmount, setDepositAmount] = useState('');
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [transferAmount, setTransferAmount] = useState('');
  const [transferEmail, setTransferEmail] = useState('');
  const [transferNotes, setTransferNotes] = useState('');
  const [searchingUser, setSearchingUser] = useState(false);
  const [foundUser, setFoundUser] = useState<{ _id: string; name: string; email: string } | null>(null);
  
  // Withdrawal fee
  const [withdrawalFeePercent, setWithdrawalFeePercent] = useState(1); // Default 1%

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalTransactions, setTotalTransactions] = useState(0);

  // Stats
  const [stats, setStats] = useState({
    totalDeposits: 0,
    totalWithdrawals: 0,
    totalTransfersIn: 0,
    totalTransfersOut: 0,
  });

  // Fetch wallet data
  const fetchWalletData = async () => {
    try {
      setIsLoading(true);
      const [balanceRes, txRes, feeRes] = await Promise.all([
        walletsAPI.getBalance(),
        walletsAPI.getTransactions(currentPage, 10),
        walletsAPI.getWithdrawalFee().catch(() => ({ data: { fee_percent: 1 } })),
      ]);
      
      setBalance(balanceRes.data.balance);
      setTransactions(txRes.data.transactions);
      setTotalPages(txRes.data.pages);
      setTotalTransactions(txRes.data.total);
      setWithdrawalFeePercent(feeRes.data.fee_percent);

      // Calculate stats from transactions - ALL credits and debits
      const allTx = txRes.data.transactions;
      
      // All money coming IN (all credits)
      const allCredits = allTx.filter(t => t.type === 'credit');
      
      // All money going OUT (all debits)
      const allDebits = allTx.filter(t => t.type === 'debit');
      
      // Transfers in/out specifically
      const transfersIn = allTx.filter(t => t.type === 'credit' && t.source === 'transfer_in');
      const transfersOut = allTx.filter(t => t.type === 'debit' && t.purpose === 'transfer_out');

      setStats({
        totalDeposits: allCredits.reduce((acc, t) => acc + t.amount, 0),
        totalWithdrawals: allDebits.reduce((acc, t) => acc + t.amount, 0),
        totalTransfersIn: transfersIn.reduce((acc, t) => acc + t.amount, 0),
        totalTransfersOut: transfersOut.reduce((acc, t) => acc + t.amount, 0),
      });
    } catch (error: any) {
      console.error('Failed to fetch wallet data:', error);
      toast({
        title: 'Error',
        description: 'Failed to load wallet data',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchWalletData();
  }, [currentPage]);

  // Handle deposit via Finternet
  const handleDeposit = async () => {
    const amount = parseFloat(depositAmount);
    if (isNaN(amount) || amount <= 0) {
      toast({ title: 'Invalid amount', variant: 'destructive' });
      return;
    }

    setIsTransacting(true);
    try {
      const res = await walletsAPI.deposit(amount, true); // Use Finternet
      
      // Balance is updated immediately before gateway redirect
      if (res.data.new_balance !== undefined) {
        setBalance(res.data.new_balance);
      }
      
      // Close modal and reset
      setShowDepositModal(false);
      setDepositAmount('');
      fetchWalletData();
      
      // Open payment gateway in new tab (for show - funds already credited)
      if (res.data.payment_url) {
        window.open(res.data.payment_url, '_blank');
      }
    } catch (error: any) {
      toast({
        title: 'Deposit Failed',
        description: error.response?.data?.error || 'Please try again',
        variant: 'destructive',
      });
    } finally {
      setIsTransacting(false);
    }
  };

  // Calculate withdrawal fee preview
  const withdrawalFee = parseFloat(withdrawAmount || '0') * (withdrawalFeePercent / 100);
  const netWithdrawal = parseFloat(withdrawAmount || '0') - withdrawalFee;

  // Handle withdraw
  const handleWithdraw = async () => {
    const amount = parseFloat(withdrawAmount);
    if (isNaN(amount) || amount <= 0) {
      toast({ title: 'Invalid amount', variant: 'destructive' });
      return;
    }

    if (amount > balance) {
      toast({ title: 'Insufficient balance', variant: 'destructive' });
      return;
    }

    setIsTransacting(true);
    try {
      const res = await walletsAPI.withdraw(amount);
      
      // Balance is updated immediately before gateway redirect
      setBalance(res.data.new_balance);
      
      // Close modal and reset
      setShowWithdrawModal(false);
      setWithdrawAmount('');
      fetchWalletData();
      
      // Open payment gateway in new tab (for show - funds already debited)
      if (res.data.payment_url) {
        window.open(res.data.payment_url, '_blank');
      }
    } catch (error: any) {
      toast({
        title: 'Withdrawal Failed',
        description: error.response?.data?.error || 'Please try again',
        variant: 'destructive',
      });
    } finally {
      setIsTransacting(false);
    }
  };

  // Search user for transfer
  const handleSearchUser = async () => {
    if (!transferEmail.trim()) return;
    
    setSearchingUser(true);
    setFoundUser(null);
    try {
      const res = await usersAPI.search(transferEmail.trim());
      const users = res.data.users || [];
      const exactMatch = users.find((u: any) => u.email.toLowerCase() === transferEmail.toLowerCase());
      if (exactMatch) {
        setFoundUser(exactMatch);
      } else if (users.length > 0) {
        setFoundUser(users[0]);
      } else {
        toast({ title: 'User not found', variant: 'destructive' });
      }
    } catch (error) {
      toast({ title: 'User not found', variant: 'destructive' });
    } finally {
      setSearchingUser(false);
    }
  };

  // Handle transfer
  const handleTransfer = async () => {
    if (!foundUser) {
      toast({ title: 'Please search for a recipient first', variant: 'destructive' });
      return;
    }

    const amount = parseFloat(transferAmount);
    if (isNaN(amount) || amount <= 0) {
      toast({ title: 'Invalid amount', variant: 'destructive' });
      return;
    }

    if (amount > balance) {
      toast({ title: 'Insufficient balance', variant: 'destructive' });
      return;
    }

    setIsTransacting(true);
    try {
      const res = await walletsAPI.transfer(foundUser._id, amount, transferNotes);
      setBalance(res.data.new_balance);
      toast({
        title: 'Transfer Successful',
        description: `$${amount.toFixed(2)} sent to ${foundUser.name}`,
      });
      setShowTransferModal(false);
      setTransferAmount('');
      setTransferEmail('');
      setTransferNotes('');
      setFoundUser(null);
      fetchWalletData();
    } catch (error: any) {
      toast({
        title: 'Transfer Failed',
        description: error.response?.data?.error || 'Please try again',
        variant: 'destructive',
      });
    } finally {
      setIsTransacting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate('/dashboard')}>
              <ChevronLeft className="w-5 h-5" />
            </Button>
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
                <Wallet className="w-5 h-5 text-primary-foreground" />
              </div>
              <span className="text-xl font-display font-bold">My Wallet</span>
            </div>
          </div>
          
          <Button variant="ghost" size="icon" onClick={fetchWalletData}>
            <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </nav>

      <main className="container mx-auto px-6 py-8 max-w-4xl">
        {/* Balance Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-8 rounded-2xl mb-8 text-center relative overflow-hidden"
        >
          <div className="absolute inset-0 gradient-primary opacity-5" />
          <div className="relative">
            <p className="text-muted-foreground mb-2">Available Balance</p>
            <p className="text-5xl font-bold mb-6">${balance.toFixed(2)}</p>
            
            <div className="flex flex-wrap justify-center gap-4">
              <Button variant="gradient" size="lg" onClick={() => setShowDepositModal(true)}>
                <Plus className="w-5 h-5" />
                Add Money
              </Button>
              <Button variant="outline" size="lg" onClick={() => setShowWithdrawModal(true)}>
                <Minus className="w-5 h-5" />
                Withdraw
              </Button>
              <Button variant="outline" size="lg" onClick={() => setShowTransferModal(true)}>
                <Send className="w-5 h-5" />
                Transfer
              </Button>
            </div>
          </div>
        </motion.div>

        {/* Quick Stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8"
        >
          <div className="glass-card p-4 rounded-xl">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-success/10 flex items-center justify-center">
                <ArrowUp className="w-4 h-4 text-success" />
              </div>
              <span className="text-sm text-muted-foreground">Total In</span>
            </div>
            <p className="text-xl font-bold">${stats.totalDeposits.toFixed(2)}</p>
          </div>
          
          <div className="glass-card p-4 rounded-xl">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-destructive/10 flex items-center justify-center">
                <ArrowDown className="w-4 h-4 text-destructive" />
              </div>
              <span className="text-sm text-muted-foreground">Total Out</span>
            </div>
            <p className="text-xl font-bold">${stats.totalWithdrawals.toFixed(2)}</p>
          </div>
          
          <div className="glass-card p-4 rounded-xl">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-info/10 flex items-center justify-center">
                <ArrowDownRight className="w-4 h-4 text-info" />
              </div>
              <span className="text-sm text-muted-foreground">Received</span>
            </div>
            <p className="text-xl font-bold">${stats.totalTransfersIn.toFixed(2)}</p>
          </div>
          
          <div className="glass-card p-4 rounded-xl">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-warning/10 flex items-center justify-center">
                <ArrowUpRight className="w-4 h-4 text-warning" />
              </div>
              <span className="text-sm text-muted-foreground">Sent</span>
            </div>
            <p className="text-xl font-bold">${stats.totalTransfersOut.toFixed(2)}</p>
          </div>
        </motion.div>

        {/* Transaction History */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-card rounded-xl"
        >
          <div className="p-6 border-b border-border">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <Clock className="w-5 h-5" />
              Transaction History
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              {totalTransactions} total transactions
            </p>
          </div>

          {transactions.length === 0 ? (
            <div className="p-12 text-center">
              <Wallet className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No transactions yet</p>
              <p className="text-sm text-muted-foreground">Add money to get started</p>
            </div>
          ) : (
            <>
              <div className="divide-y divide-border">
                {transactions.map((tx) => {
                  const { icon: Icon, color, bg } = getTransactionIcon(tx.type, tx.source, tx.purpose);
                  const isCredit = tx.type === 'credit';
                  
                  return (
                    <div key={tx._id} className="p-4 hover:bg-accent/50 transition-colors">
                      <div className="flex items-center gap-4">
                        <div className={`w-10 h-10 rounded-full ${bg} flex items-center justify-center`}>
                          <Icon className={`w-5 h-5 ${color}`} />
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <p className="font-medium">{getTransactionLabel(tx)}</p>
                          <p className="text-sm text-muted-foreground truncate">
                            {tx.notes || (tx.source || tx.purpose || 'Transaction')}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {dayjs(tx.created_at).format('MMM D, YYYY h:mm A')}
                          </p>
                        </div>
                        
                        <div className="text-right">
                          <p className={`font-semibold ${isCredit ? 'text-success' : 'text-destructive'}`}>
                            {isCredit ? '+' : '-'}${tx.amount.toFixed(2)}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Balance: ${tx.balance_after.toFixed(2)}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="p-4 border-t border-border flex items-center justify-between">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={currentPage === 1}
                    onClick={() => setCurrentPage(p => p - 1)}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    Page {currentPage} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={currentPage === totalPages}
                    onClick={() => setCurrentPage(p => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          )}
        </motion.div>

        {/* Info Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-8 glass-card p-6 rounded-xl bg-primary/5"
        >
          <h3 className="font-semibold flex items-center gap-2 mb-3">
            <AlertCircle className="w-5 h-5 text-primary" />
            How Your Wallet Works
          </h3>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-success mt-0.5" />
              <span><strong>Add Money:</strong> Securely add funds via Finternet payment gateway.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-success mt-0.5" />
              <span><strong>Event Settlements:</strong> When you leave an event or an event ends, your remaining balance is credited to your wallet.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-success mt-0.5" />
              <span><strong>Auto-Coverage:</strong> If you don't have enough in an event's pool for your expense share, it's automatically covered from your wallet.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-success mt-0.5" />
              <span><strong>Transfers:</strong> Send money directly to other Cooper users instantly.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-warning mt-0.5" />
              <span><strong>Withdrawals:</strong> A small {withdrawalFeePercent}% donation supports Cooper's mission when you withdraw.</span>
            </li>
          </ul>
        </motion.div>
      </main>

      {/* Deposit Modal */}
      {showDepositModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-card rounded-2xl p-6 w-full max-w-md"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">Add Money</h2>
              <Button variant="ghost" size="icon" onClick={() => setShowDepositModal(false)}>
                <X className="w-5 h-5" />
              </Button>
            </div>
            
            <div className="mb-6">
              <label className="block text-sm font-medium mb-2">Amount</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  value={depositAmount}
                  onChange={(e) => setDepositAmount(e.target.value)}
                  className="pl-7 text-lg"
                />
              </div>
            </div>

            <div className="flex gap-2 mb-4">
              {[10, 25, 50, 100].map((amt) => (
                <Button
                  key={amt}
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => setDepositAmount(amt.toString())}
                >
                  ${amt}
                </Button>
              ))}
            </div>

            <Button
              variant="gradient"
              className="w-full"
              disabled={!depositAmount || isTransacting}
              onClick={handleDeposit}
            >
              {isTransacting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CreditCard className="w-4 h-4 mr-2" />}
              Pay via Finternet
            </Button>

            <p className="text-xs text-muted-foreground text-center mt-3">
              Secure payment powered by Finternet Gateway
            </p>
          </motion.div>
        </div>
      )}

      {/* Withdraw Modal */}
      {showWithdrawModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-card rounded-2xl p-6 w-full max-w-md"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">Withdraw Money</h2>
              <Button variant="ghost" size="icon" onClick={() => setShowWithdrawModal(false)}>
                <X className="w-5 h-5" />
              </Button>
            </div>

            <div className="bg-accent/50 rounded-lg p-4 mb-6">
              <p className="text-sm text-muted-foreground">Available Balance</p>
              <p className="text-2xl font-bold">${balance.toFixed(2)}</p>
            </div>
            
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Amount to Withdraw</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  max={balance}
                  placeholder="0.00"
                  value={withdrawAmount}
                  onChange={(e) => setWithdrawAmount(e.target.value)}
                  className="pl-7 text-lg"
                />
              </div>
            </div>

            {/* Fee breakdown */}
            {parseFloat(withdrawAmount || '0') > 0 && (
              <div className="bg-warning/10 border border-warning/30 rounded-lg p-3 mb-4">
                <p className="text-sm font-medium text-warning mb-2">Withdrawal Summary</p>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Withdrawal amount:</span>
                    <span>${parseFloat(withdrawAmount).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-warning">
                    <span>Platform donation ({withdrawalFeePercent}%):</span>
                    <span>-${withdrawalFee.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between font-semibold pt-1 border-t border-border">
                    <span>You receive:</span>
                    <span className="text-success">${netWithdrawal.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            )}

            <Button
              variant="outline"
              size="sm"
              className="mb-4"
              onClick={() => setWithdrawAmount(balance.toString())}
            >
              Withdraw All (${balance.toFixed(2)})
            </Button>

            <Button
              variant="gradient"
              className="w-full"
              disabled={!withdrawAmount || parseFloat(withdrawAmount) > balance || isTransacting}
              onClick={handleWithdraw}
            >
              {isTransacting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Withdraw (Receive ${netWithdrawal > 0 ? netWithdrawal.toFixed(2) : '0.00'})
            </Button>

            <p className="text-xs text-muted-foreground text-center mt-3">
              {withdrawalFeePercent}% of withdrawals support Cooper's mission
            </p>
          </motion.div>
        </div>
      )}

      {/* Transfer Modal */}
      {showTransferModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-card rounded-2xl p-6 w-full max-w-md"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">Transfer Money</h2>
              <Button variant="ghost" size="icon" onClick={() => {
                setShowTransferModal(false);
                setFoundUser(null);
                setTransferEmail('');
              }}>
                <X className="w-5 h-5" />
              </Button>
            </div>

            <div className="bg-accent/50 rounded-lg p-4 mb-6">
              <p className="text-sm text-muted-foreground">Available Balance</p>
              <p className="text-2xl font-bold">${balance.toFixed(2)}</p>
            </div>
            
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Recipient Email</label>
              <div className="flex gap-2">
                <Input
                  type="email"
                  placeholder="user@example.com"
                  value={transferEmail}
                  onChange={(e) => {
                    setTransferEmail(e.target.value);
                    setFoundUser(null);
                  }}
                />
                <Button
                  variant="outline"
                  onClick={handleSearchUser}
                  disabled={!transferEmail.trim() || searchingUser}
                >
                  {searchingUser ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                </Button>
              </div>
            </div>

            {foundUser && (
              <div className="bg-success/10 border border-success/30 rounded-lg p-3 mb-4 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-success/20 flex items-center justify-center">
                  <CheckCircle className="w-5 h-5 text-success" />
                </div>
                <div>
                  <p className="font-medium">{foundUser.name}</p>
                  <p className="text-sm text-muted-foreground">{foundUser.email}</p>
                </div>
              </div>
            )}
            
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Amount</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  max={balance}
                  placeholder="0.00"
                  value={transferAmount}
                  onChange={(e) => setTransferAmount(e.target.value)}
                  className="pl-7 text-lg"
                  disabled={!foundUser}
                />
              </div>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium mb-2">Note (optional)</label>
              <Input
                type="text"
                placeholder="What's this for?"
                value={transferNotes}
                onChange={(e) => setTransferNotes(e.target.value)}
                disabled={!foundUser}
              />
            </div>

            <Button
              variant="gradient"
              className="w-full"
              disabled={!foundUser || !transferAmount || parseFloat(transferAmount) > balance || isTransacting}
              onClick={handleTransfer}
            >
              {isTransacting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
              Send ${parseFloat(transferAmount || '0').toFixed(2)}
            </Button>
          </motion.div>
        </div>
      )}
    </div>
  );
}
