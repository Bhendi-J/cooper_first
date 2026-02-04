import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
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
  Upload,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { expensesAPI, eventsAPI, Event, Participant } from '@/lib/api';

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
  const [isScanning, setIsScanning] = useState(false);

  const handleScanReceipt = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsScanning(true);
    toast({
      title: "Scanning receipt...",
      description: "Gemini AI is analyzing your receipt.",
    });

    try {
      const res = await expensesAPI.scanReceipt(file);
      const { amount, description, currency, items, date } = res.data;

      setFormData(prev => ({
        ...prev,
        amount: amount ? amount.toString() : prev.amount,
        description: description || prev.description,
      }));

      // Build detailed message
      let itemsList = '';
      if (items && items.length > 0) {
        itemsList = '\n\nItems:\n' + items.map((item: any) =>
          `• ${item.name}: ${currency || '₹'}${item.price || '?'}`
        ).join('\n');
      }

      toast({
        title: "Receipt scanned!",
        description: `Amount: ${currency || '₹'}${amount || 'Unknown'}${date ? `\nDate: ${date}` : ''}${itemsList}`,
      });
    } catch (error: any) {
      console.error("Scan failed:", error);
      const errorMsg = error.response?.data?.error || error.message || "Could not read receipt data.";
      toast({
        title: "Scan failed",
        description: errorMsg,
        variant: "destructive",
      });
    } finally {
      setIsScanning(false);
      // Reset input
      e.target.value = '';
    }
  };

  const [formData, setFormData] = useState({
    amount: '',
    description: '',
    category: '',
    paymentType: 'wallet' as 'wallet' | 'cash',
    splitType: 'equal' as 'equal' | 'custom',
  });

  // Get participants from event
  const participants = event?.participants || [];
  const [selectedMembers, setSelectedMembers] = useState<string[]>([]);

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
      await expensesAPI.add({
        event_id: id,
        amount: parseFloat(formData.amount),
        description: formData.description || undefined,
        // category_id would be used if backend returns category IDs
      });

      toast({
        title: 'Expense added!',
        description: `₹${formData.amount} has been recorded and split among ${selectedMembers.length} members.`,
      });

      navigate(`/events/${id}`);
    } catch (error: any) {
      toast({
        title: 'Failed to add expense',
        description: error.response?.data?.error || 'Something went wrong',
        variant: 'destructive',
      });
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
        <div className="container mx-auto px-6 py-4 flex items-center gap-4">
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
      </nav>

      <main className="container mx-auto px-6 py-8 max-w-2xl">
        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Amount */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-8 rounded-xl text-center relative"
          >
            <div className="absolute top-4 right-4">
              <input
                type="file"
                accept="image/*"
                id="receipt-upload"
                className="hidden"
                onChange={handleScanReceipt}
                disabled={isScanning}
              />
              <label htmlFor="receipt-upload">
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-2"
                  asChild
                  disabled={isScanning}
                >
                  <span className="cursor-pointer">
                    {isScanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Camera className="w-4 h-4" />}
                    Scan Receipt
                  </span>
                </Button>
              </label>
            </div>
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
                  className={`p-4 rounded-xl text-center transition-all hover-lift ${formData.category === cat.id
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
            <div className="grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setFormData({ ...formData, paymentType: 'wallet' })}
                className={`p-5 rounded-xl flex items-center gap-4 transition-all ${formData.paymentType === 'wallet'
                  ? 'glass-card-glow border-primary'
                  : 'glass-card'
                  }`}
              >
                <div
                  className={`w-12 h-12 rounded-lg flex items-center justify-center ${formData.paymentType === 'wallet'
                    ? 'gradient-primary'
                    : 'bg-background-surface'
                    }`}
                >
                  <CreditCard
                    className={`w-6 h-6 ${formData.paymentType === 'wallet'
                      ? 'text-primary-foreground'
                      : 'text-muted-foreground'
                      }`}
                  />
                </div>
                <div className="text-left">
                  <p className="font-semibold">Shared Wallet</p>
                  <p className="text-sm text-muted-foreground">Pay from pool</p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setFormData({ ...formData, paymentType: 'cash' })}
                className={`p-5 rounded-xl flex items-center gap-4 transition-all ${formData.paymentType === 'cash'
                  ? 'glass-card-glow border-primary'
                  : 'glass-card'
                  }`}
              >
                <div
                  className={`w-12 h-12 rounded-lg flex items-center justify-center ${formData.paymentType === 'cash'
                    ? 'gradient-primary'
                    : 'bg-background-surface'
                    }`}
                >
                  <Banknote
                    className={`w-6 h-6 ${formData.paymentType === 'cash'
                      ? 'text-primary-foreground'
                      : 'text-muted-foreground'
                      }`}
                  />
                </div>
                <div className="text-left">
                  <p className="font-semibold">Cash</p>
                  <p className="text-sm text-muted-foreground">Needs approval</p>
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
            <div className="grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => {
                  setFormData({ ...formData, splitType: 'equal' });
                  setSelectedMembers(participants.map((p) => p.user_id));
                }}
                className={`p-4 rounded-xl text-center transition-all ${formData.splitType === 'equal'
                  ? 'glass-card-glow border-primary'
                  : 'glass-card'
                  }`}
              >
                <Users className="w-6 h-6 mx-auto mb-2" />
                <p className="font-semibold">Split Equally</p>
                <p className="text-xs text-muted-foreground">Among all members</p>
              </button>

              <button
                type="button"
                onClick={() => setFormData({ ...formData, splitType: 'custom' })}
                className={`p-4 rounded-xl text-center transition-all ${formData.splitType === 'custom'
                  ? 'glass-card-glow border-primary'
                  : 'glass-card'
                  }`}
              >
                <Tag className="w-6 h-6 mx-auto mb-2" />
                <p className="font-semibold">Custom Split</p>
                <p className="text-xs text-muted-foreground">Select members</p>
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
                      className={`p-3 rounded-lg flex items-center gap-3 transition-all ${selectedMembers.includes(member.user_id)
                        ? 'bg-primary/10 border border-primary'
                        : 'bg-background hover:bg-background-surface'
                        }`}
                    >
                      <div
                        className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${selectedMembers.includes(member.user_id)
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
