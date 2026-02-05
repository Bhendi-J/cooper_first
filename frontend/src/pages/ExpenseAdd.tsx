import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { ReceiptScanner } from '@/components/ReceiptScanner';
import {
  Wallet,
  ArrowLeft,
  IndianRupee,
  Tag,
  Users,
  Check,
  Loader2,
  Receipt,
  Banknote,
  CreditCard,
  Camera,
  X,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { expensesAPI, eventsAPI, Event, Participant, ReceiptScanResult } from '@/lib/api';

// Default categories (backend may provide these)
const defaultCategories = [
  { id: 'food', label: 'Food & Drinks', icon: '🍽️' },
  { id: 'transport', label: 'Transport', icon: '🚗' },
  { id: 'accommodation', label: 'Accommodation', icon: '🏨' },
  { id: 'activities', label: 'Activities', icon: '🎯' },
  { id: 'shopping', label: 'Shopping', icon: '🛍️' },
  { id: 'other', label: 'Other', icon: '📦' },
];

export default function ExpenseAdd() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingEvent, setIsLoadingEvent] = useState(true);
  const [event, setEvent] = useState<Event | null>(null);
  const [categories] = useState(defaultCategories);
  const [showScanner, setShowScanner] = useState(false);

  const [formData, setFormData] = useState({
    amount: '',
    description: '',
    category: '',
    paymentType: 'wallet' as 'wallet' | 'cash' | 'gateway',
    splitType: 'equal' as 'equal' | 'custom' | 'exact',
  });

  // Get participants from event
  const participants = event?.participants || [];
  const [selectedMembers, setSelectedMembers] = useState<string[]>([]);
  const [customAmounts, setCustomAmounts] = useState<Record<string, string>>({});

  // Fetch event data on mount
  useEffect(() => {
    const fetchEvent = async () => {
      if (!id) return;
      try {
        const eventRes = await eventsAPI.get(id);
        setEvent(eventRes.data.event);
        // Select all participants by default
        const allIds = eventRes.data.event.participants?.map(p => p.user_id) || [];
        setSelectedMembers(allIds);
      } catch (error: any) {
        console.error('Failed to fetch event:', error);
        toast({
          title: 'Error',
          description: 'Failed to load event data',
          variant: 'destructive',
        });
        navigate('/dashboard');
      } finally {
        setIsLoadingEvent(false);
      }
    };
    fetchEvent();
  }, [id, navigate, toast]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleReceiptScan = (result: ReceiptScanResult) => {
    // Pre-fill form with scanned data
    setFormData(prev => ({
      ...prev,
      amount: result.amount?.toString() || prev.amount,
      description: result.description || result.merchant || prev.description,
      category: result.category || prev.category,
    }));
    setShowScanner(false);
    toast({
      title: 'Receipt scanned!',
      description: 'Expense details have been auto-filled.',
    });
  };

  const toggleMember = (memberId: string) => {
    if (selectedMembers.includes(memberId)) {
      setSelectedMembers(selectedMembers.filter((id) => id !== memberId));
    } else {
      setSelectedMembers([...selectedMembers, memberId]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    
    setIsLoading(true);

    try {
      // Build split details based on split type
      let splitDetails: Record<string, any> = {};
      let splitType = formData.splitType;
      
      if (formData.splitType === 'equal') {
        splitType = 'equal';
      } else if (formData.splitType === 'custom') {
        // Custom: equal split among selected members only
        splitType = 'equal';
        // Only include selected members - backend will handle the split
      } else if (formData.splitType === 'exact') {
        // Exact: specific amounts per member
        splitType = 'exact';
        splitDetails = {
          amounts: Object.fromEntries(
            Object.entries(customAmounts)
              .filter(([_, v]) => parseFloat(v) > 0)
              .map(([k, v]) => [k, parseFloat(v)])
          ),
        };
      }

      const expenseData = {
        event_id: id,
        amount: parseFloat(formData.amount),
        description: formData.description || undefined,
        split_type: splitType,
        split_details: Object.keys(splitDetails).length > 0 ? splitDetails : undefined,
        selected_members: formData.splitType === 'custom' ? selectedMembers : undefined,
      };

      // Handle payment gateway option
      if (formData.paymentType === 'gateway') {
        const paymentResponse = await expensesAPI.addWithPayment(expenseData);
        
        // Store for confirmation after payment
        localStorage.setItem('pendingExpenseId', paymentResponse.data.pending_expense_id);
        localStorage.setItem('pendingExpenseEventId', id);
        
        // Direct redirect to payment gateway
        window.location.href = paymentResponse.data.payment_url;
        return;
      }

      // Regular expense flow (wallet or cash)
      const response = await expensesAPI.add(expenseData);

      // Check if expense requires approval
      if (response.data.status === 'pending_approval') {
        toast({
          title: 'Expense submitted for approval',
          description: `₹${formData.amount} expense requires creator approval before being processed.`,
        });
      } else {
        toast({
          title: 'Expense added!',
          description: `₹${formData.amount} has been recorded and split among ${selectedMembers.length} members.`,
        });
        
        // Show debt notification if any shortfalls occurred
        if (response.data.shortfall_debts && response.data.shortfall_debts.length > 0) {
          toast({
            title: 'Pool shortfall detected',
            description: 'Some participants have been notified about outstanding balances.',
            variant: 'default',
          });
        }
      }

      navigate(`/events/${id}`);
    } catch (error: any) {
      // Handle rule violations
      if (error.response?.data?.violations) {
        toast({
          title: 'Expense violates rules',
          description: error.response.data.violations.map((v: any) => v.message || v.type).join(', '),
          variant: 'destructive',
        });
      } else {
        toast({
          title: 'Failed to add expense',
          description: error.response?.data?.error || 'Something went wrong',
          variant: 'destructive',
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const perPersonAmount = formData.amount && selectedMembers.length > 0
    ? (parseFloat(formData.amount) / selectedMembers.length).toFixed(2)
    : '0.00';

  if (isLoadingEvent) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to={`/events/${id}`}>
              <Button variant="ghost" size="icon">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
                <Receipt className="w-5 h-5 text-primary-foreground" />
              </div>
              <span className="text-xl font-display font-bold">Add Expense</span>
            </div>
          </div>
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => setShowScanner(!showScanner)}
          >
            <Camera className="w-4 h-4 mr-2" />
            Scan Receipt
          </Button>
        </div>
      </nav>

      <main className="container mx-auto px-6 py-8 max-w-2xl">
        {/* Receipt Scanner Modal */}
        {showScanner && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6"
          >
            <ReceiptScanner 
              onScanComplete={handleReceiptScan}
              onCancel={() => setShowScanner(false)}
            />
          </motion.div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Amount */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-8 rounded-xl text-center"
          >
            <Label className="text-muted-foreground text-sm">Enter Amount</Label>
            <div className="flex items-center justify-center gap-2 mt-4">
              <span className="text-4xl text-muted-foreground">₹</span>
              <Input
                name="amount"
                type="number"
                placeholder="0"
                value={formData.amount}
                onChange={handleInputChange}
                className="text-5xl font-display font-bold text-center bg-transparent border-none shadow-none focus-visible:ring-0 w-48 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                required
              />
            </div>
            {formData.amount && (
              <p className="text-sm text-muted-foreground mt-4">
                ₹{perPersonAmount} per person
              </p>
            )}
          </motion.div>

          {/* Description */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="space-y-2"
          >
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              name="description"
              placeholder="What was this expense for?"
              value={formData.description}
              onChange={handleInputChange}
              className="bg-background-surface border-border focus:border-primary min-h-[80px]"
              required
            />
          </motion.div>

          {/* Category */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="space-y-3"
          >
            <Label>Category</Label>
            <div className="grid grid-cols-3 gap-3">
              {categories.map((cat) => (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => setFormData({ ...formData, category: cat.id })}
                  className={`p-4 rounded-xl text-center transition-all hover-lift ${
                    formData.category === cat.id
                      ? 'glass-card-glow border-primary'
                      : 'glass-card'
                  }`}
                >
                  <span className="text-2xl mb-2 block">{cat.icon}</span>
                  <span className="text-sm font-medium">{cat.label}</span>
                </button>
              ))}
            </div>
          </motion.div>

          {/* Payment Type */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="space-y-3"
          >
            <Label>Payment Method</Label>
            <div className="grid grid-cols-3 gap-4">
              <button
                type="button"
                onClick={() => setFormData({ ...formData, paymentType: 'wallet' })}
                className={`p-5 rounded-xl flex flex-col items-center gap-3 transition-all ${
                  formData.paymentType === 'wallet'
                    ? 'glass-card-glow border-primary'
                    : 'glass-card'
                }`}
              >
                <div
                  className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                    formData.paymentType === 'wallet'
                      ? 'gradient-primary'
                      : 'bg-background-surface'
                  }`}
                >
                  <CreditCard
                    className={`w-6 h-6 ${
                      formData.paymentType === 'wallet'
                        ? 'text-primary-foreground'
                        : 'text-muted-foreground'
                    }`}
                  />
                </div>
                <div className="text-center">
                  <p className="font-semibold text-sm">Shared Wallet</p>
                  <p className="text-xs text-muted-foreground">From pool</p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setFormData({ ...formData, paymentType: 'gateway' })}
                className={`p-5 rounded-xl flex flex-col items-center gap-3 transition-all ${
                  formData.paymentType === 'gateway'
                    ? 'glass-card-glow border-primary'
                    : 'glass-card'
                }`}
              >
                <div
                  className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                    formData.paymentType === 'gateway'
                      ? 'gradient-primary'
                      : 'bg-background-surface'
                  }`}
                >
                  <IndianRupee
                    className={`w-6 h-6 ${
                      formData.paymentType === 'gateway'
                        ? 'text-primary-foreground'
                        : 'text-muted-foreground'
                    }`}
                  />
                </div>
                <div className="text-center">
                  <p className="font-semibold text-sm">Pay Now</p>
                  <p className="text-xs text-muted-foreground">UPI/Card</p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setFormData({ ...formData, paymentType: 'cash' })}
                className={`p-5 rounded-xl flex flex-col items-center gap-3 transition-all ${
                  formData.paymentType === 'cash'
                    ? 'glass-card-glow border-primary'
                    : 'glass-card'
                }`}
              >
                <div
                  className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                    formData.paymentType === 'cash'
                      ? 'gradient-primary'
                      : 'bg-background-surface'
                  }`}
                >
                  <Banknote
                    className={`w-6 h-6 ${
                      formData.paymentType === 'cash'
                        ? 'text-primary-foreground'
                        : 'text-muted-foreground'
                    }`}
                  />
                </div>
                <div className="text-center">
                  <p className="font-semibold text-sm">Cash</p>
                  <p className="text-xs text-muted-foreground">Manual</p>
                </div>
              </button>
            </div>
          </motion.div>

          {/* Split Type */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="space-y-3"
          >
            <Label>Split Type</Label>
            <div className="grid grid-cols-3 gap-3">
              <button
                type="button"
                onClick={() => {
                  setFormData({ ...formData, splitType: 'equal' });
                  setSelectedMembers(participants.map((p) => p.user_id));
                }}
                className={`p-4 rounded-xl text-center transition-all ${
                  formData.splitType === 'equal'
                    ? 'glass-card-glow border-primary'
                    : 'glass-card'
                }`}
              >
                <Users className="w-5 h-5 mx-auto mb-2" />
                <p className="font-semibold text-sm">Equal</p>
                <p className="text-xs text-muted-foreground">All members</p>
              </button>

              <button
                type="button"
                onClick={() => setFormData({ ...formData, splitType: 'custom' })}
                className={`p-4 rounded-xl text-center transition-all ${
                  formData.splitType === 'custom'
                    ? 'glass-card-glow border-primary'
                    : 'glass-card'
                }`}
              >
                <Tag className="w-5 h-5 mx-auto mb-2" />
                <p className="font-semibold text-sm">Select</p>
                <p className="text-xs text-muted-foreground">Pick members</p>
              </button>

              <button
                type="button"
                onClick={() => {
                  setFormData({ ...formData, splitType: 'exact' });
                  // Initialize custom amounts for each participant
                  const amounts: Record<string, string> = {};
                  participants.forEach(p => { amounts[p.user_id] = ''; });
                  setCustomAmounts(amounts);
                }}
                className={`p-4 rounded-xl text-center transition-all ${
                  formData.splitType === 'exact'
                    ? 'glass-card-glow border-primary'
                    : 'glass-card'
                }`}
              >
                <IndianRupee className="w-5 h-5 mx-auto mb-2" />
                <p className="font-semibold text-sm">Exact</p>
                <p className="text-xs text-muted-foreground">Set amounts</p>
              </button>
            </div>
          </motion.div>

          {/* Member Selection (Custom Split) */}
          {formData.splitType === 'custom' && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="space-y-3"
            >
              <Label>Select Members</Label>
              <div className="glass-card p-4 rounded-xl">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {participants.map((member) => (
                    <button
                      key={member.user_id}
                      type="button"
                      onClick={() => toggleMember(member.user_id)}
                      className={`p-3 rounded-lg flex items-center gap-3 transition-all ${
                        selectedMembers.includes(member.user_id)
                          ? 'bg-primary/10 border border-primary'
                          : 'bg-background hover:bg-background-surface'
                      }`}
                    >
                      <div
                        className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${
                          selectedMembers.includes(member.user_id)
                            ? 'gradient-primary text-primary-foreground'
                            : 'bg-background-surface text-muted-foreground'
                        }`}
                      >
                        {member.user_name?.charAt(0) || 'U'}
                      </div>
                      <span className="font-medium">{member.user_name}</span>
                      {selectedMembers.includes(member.user_id) && (
                        <Check className="w-4 h-4 ml-auto text-primary" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
              <p className="text-sm text-muted-foreground">
                {selectedMembers.length} members selected • ₹{perPersonAmount} per person
              </p>
            </motion.div>
          )}

          {/* Exact Amounts (Per Member) */}
          {formData.splitType === 'exact' && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="space-y-3"
            >
              <div className="flex items-center justify-between">
                <Label>Set Amount Per Member</Label>
                <span className={`text-sm ${
                  Object.values(customAmounts).reduce((sum, v) => sum + (parseFloat(v) || 0), 0) === parseFloat(formData.amount || '0')
                    ? 'text-success'
                    : 'text-warning'
                }`}>
                  Total: ₹{Object.values(customAmounts).reduce((sum, v) => sum + (parseFloat(v) || 0), 0).toFixed(2)}
                  {formData.amount && ` / ₹${formData.amount}`}
                </span>
              </div>
              <div className="glass-card p-4 rounded-xl space-y-3">
                {participants.map((member) => (
                  <div key={member.user_id} className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-background-surface flex items-center justify-center text-sm font-bold flex-shrink-0">
                      {member.user_name?.charAt(0) || 'U'}
                    </div>
                    <span className="font-medium flex-1">{member.user_name}</span>
                    <div className="relative w-28">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">₹</span>
                      <Input
                        type="number"
                        placeholder="0"
                        value={customAmounts[member.user_id] || ''}
                        onChange={(e) => setCustomAmounts({
                          ...customAmounts,
                          [member.user_id]: e.target.value
                        })}
                        className="pl-7 h-10 bg-background text-right"
                      />
                    </div>
                  </div>
                ))}
              </div>
              {formData.amount && Object.values(customAmounts).reduce((sum, v) => sum + (parseFloat(v) || 0), 0) !== parseFloat(formData.amount) && (
                <p className="text-sm text-warning">
                  ⚠️ Individual amounts must add up to ₹{formData.amount}
                </p>
              )}
            </motion.div>
          )}

          {/* Submit */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
            className="pt-4"
          >
            <Button
              type="submit"
              variant="gradient"
              size="xl"
              className="w-full"
              disabled={isLoading || !formData.amount || !formData.category}
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  <Receipt className="w-5 h-5" />
                  Add Expense
                </>
              )}
            </Button>

            {formData.paymentType === 'cash' && (
              <p className="text-xs text-center text-warning mt-3">
                Cash payments require approval from all members
              </p>
            )}
          </motion.div>
        </form>
      </main>
    </div>
  );
}
