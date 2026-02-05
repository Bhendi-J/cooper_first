import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Wallet,
  ArrowLeft,
  Calendar,
  IndianRupee,
  Users,
  Copy,
  Check,
  Share2,
  Loader2,
  Plus,
  X,
  Shield,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { eventsAPI } from '@/lib/api';

const ruleTemplates = [
  { id: 'max-expense', label: 'Max expense per transaction', value: 5000 },
  { id: 'approval', label: 'Require approval above', value: 10000 },
  { id: 'categories', label: 'Restricted categories', value: ['Alcohol', 'Gambling'] },
];

export default function EventCreate() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [step, setStep] = useState(1);
  const [copied, setCopied] = useState(false);

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    startDate: '',
    endDate: '',
    // Deposit rules
    minDeposit: '',
    maxDeposit: '',
    creatorDeposit: '',  // Creator's initial deposit
    // Expense rules
    maxExpense: '',
    minExpense: '',
    approvalThreshold: '',
    requireApproval: false,
  });

  const [createdEvent, setCreatedEvent] = useState<{
    id: string;
    code: string;
    link: string;
  } | null>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      // Validate creator deposit if min/max deposit is set
      const minDep = formData.minDeposit ? parseFloat(formData.minDeposit) : 0;
      const maxDep = formData.maxDeposit ? parseFloat(formData.maxDeposit) : Infinity;
      const creatorDep = formData.creatorDeposit ? parseFloat(formData.creatorDeposit) : 0;
      
      if (minDep > 0 && creatorDep < minDep) {
        toast({
          title: 'Invalid deposit',
          description: `Your deposit must be at least $${minDep.toFixed(2)}`,
          variant: 'destructive',
        });
        setIsLoading(false);
        return;
      }
      
      if (maxDep < Infinity && creatorDep > maxDep) {
        toast({
          title: 'Invalid deposit',
          description: `Your deposit cannot exceed $${maxDep.toFixed(2)}`,
          variant: 'destructive',
        });
        setIsLoading(false);
        return;
      }
      
      const response = await eventsAPI.create({
        name: formData.name,
        description: formData.description || undefined,
        start_date: formData.startDate || undefined,
        end_date: formData.endDate || undefined,
        creator_deposit: creatorDep,
        rules: {
          // Deposit limits
          min_deposit: formData.minDeposit ? parseFloat(formData.minDeposit) : undefined,
          max_deposit: formData.maxDeposit ? parseFloat(formData.maxDeposit) : undefined,
          // Expense limits
          max_expense_per_transaction: formData.maxExpense ? parseFloat(formData.maxExpense) : undefined,
          min_expense_per_transaction: formData.minExpense ? parseFloat(formData.minExpense) : undefined,
          // Approval settings
          approval_required: formData.requireApproval,
          approval_required_threshold: formData.approvalThreshold ? parseFloat(formData.approvalThreshold) : undefined,
          auto_approve_under: formData.approvalThreshold ? parseFloat(formData.approvalThreshold) : 100,
        },
      });

      const event = response.data.event;
      
      // Get the invite link info
      let inviteCode = event.invite_code || '';
      let frontendJoinUrl = `${window.location.origin}/join/${inviteCode}`;
      
      try {
        const inviteLinkRes = await eventsAPI.getInviteLink(event._id);
        inviteCode = inviteLinkRes.data.invite_code;
        frontendJoinUrl = inviteLinkRes.data.frontend_join_url || frontendJoinUrl;
      } catch {
        // Use default values if invite link fetch fails
      }

      setCreatedEvent({
        id: event._id,
        code: inviteCode,
        link: frontendJoinUrl,
      });
      setStep(3);

      toast({
        title: 'Event created!',
        description: 'Share the code with your group to get started.',
      });
      
      // If there's a payment URL for the deposit, open it in a new tab
      if (event.payment_url) {
        window.open(event.payment_url, '_blank');
      }
      
    } catch (error: any) {
      toast({
        title: 'Failed to create event',
        description: error.response?.data?.error || 'Something went wrong',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast({
      title: 'Copied!',
      description: 'Link copied to clipboard.',
    });
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
        <div className="container mx-auto px-6 py-4 flex items-center gap-4">
          <Link to="/dashboard">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="w-5 h-5" />
            </Button>
          </Link>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
              <Wallet className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-display font-bold">Cooper</span>
          </div>
        </div>
      </nav>

      <main className="container mx-auto px-6 py-8 max-w-2xl">
        {/* Progress Steps */}
        <div className="flex items-center justify-center gap-4 mb-12">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-all ${
                  step >= s
                    ? 'gradient-primary text-primary-foreground'
                    : 'bg-background-surface text-muted-foreground'
                }`}
              >
                {step > s ? <Check className="w-5 h-5" /> : s}
              </div>
              {s < 3 && (
                <div
                  className={`w-16 h-1 rounded-full transition-all ${
                    step > s ? 'gradient-primary' : 'bg-background-surface'
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step 1: Basic Info */}
        {step === 1 && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
          >
            <h1 className="text-3xl font-display font-bold mb-2">Create New Event</h1>
            <p className="text-muted-foreground mb-8">
              Set up your group event and define the shared wallet details.
            </p>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                setStep(2);
              }}
              className="space-y-6"
            >
              <div className="space-y-2">
                <Label htmlFor="name">Event Name</Label>
                <Input
                  id="name"
                  name="name"
                  placeholder="e.g., Goa Trip 2024"
                  value={formData.name}
                  onChange={handleInputChange}
                  className="h-12 bg-background-surface border-border focus:border-primary"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description (Optional)</Label>
                <Textarea
                  id="description"
                  name="description"
                  placeholder="What's this event about?"
                  value={formData.description}
                  onChange={handleInputChange}
                  className="bg-background-surface border-border focus:border-primary min-h-[100px]"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="startDate">Start Date</Label>
                  <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                    <Input
                      id="startDate"
                      name="startDate"
                      type="date"
                      value={formData.startDate}
                      onChange={handleInputChange}
                      className="h-12 pl-11 bg-background-surface border-border focus:border-primary"
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="endDate">End Date</Label>
                  <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                    <Input
                      id="endDate"
                      name="endDate"
                      type="date"
                      value={formData.endDate}
                      onChange={handleInputChange}
                      className="h-12 pl-11 bg-background-surface border-border focus:border-primary"
                      required
                    />
                  </div>
                </div>
              </div>

              <div className="glass-card p-6 rounded-xl">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
                    <IndianRupee className="w-5 h-5 text-success" />
                  </div>
                  <div>
                    <h3 className="font-semibold">Deposit Limits</h3>
                    <p className="text-sm text-muted-foreground">
                      Set min/max deposit amounts for members
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="minDeposit">Minimum Deposit</Label>
                    <div className="relative">
                      <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                      <Input
                        id="minDeposit"
                        name="minDeposit"
                        type="number"
                        placeholder="500"
                        value={formData.minDeposit}
                        onChange={handleInputChange}
                        className="h-12 pl-11 bg-background-surface border-border focus:border-primary"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="maxDeposit">Maximum Deposit</Label>
                    <div className="relative">
                      <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                      <Input
                        id="maxDeposit"
                        name="maxDeposit"
                        type="number"
                        placeholder="50000"
                        value={formData.maxDeposit}
                        onChange={handleInputChange}
                        className="h-12 pl-11 bg-background-surface border-border focus:border-primary"
                      />
                    </div>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Members can deposit any amount within this range
                </p>
                
                {/* Creator's initial deposit */}
                {(formData.minDeposit || formData.maxDeposit) && (
                  <div className="mt-4 pt-4 border-t border-border">
                    <Label htmlFor="creatorDeposit" className="text-success">Your Initial Deposit (Required)</Label>
                    <div className="relative mt-2">
                      <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-success" />
                      <Input
                        id="creatorDeposit"
                        name="creatorDeposit"
                        type="number"
                        placeholder={formData.minDeposit || "Enter amount"}
                        value={formData.creatorDeposit}
                        onChange={handleInputChange}
                        className="h-12 pl-11 bg-background-surface border-success/50 focus:border-success"
                        required={!!formData.minDeposit}
                        min={formData.minDeposit || 0}
                        max={formData.maxDeposit || undefined}
                      />
                    </div>
                    <p className="text-xs text-success mt-1">
                      As the creator, you must deposit between ${formData.minDeposit || '0'} - ${formData.maxDeposit || '∞'}
                    </p>
                  </div>
                )}
              </div>

              <Button type="submit" variant="gradient" size="lg" className="w-full">
                Continue to Rules
              </Button>
            </form>
          </motion.div>
        )}

        {/* Step 2: Rules */}
        {step === 2 && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
          >
            <h1 className="text-3xl font-display font-bold mb-2">Set Spending Rules</h1>
            <p className="text-muted-foreground mb-8">
              Define rules to keep spending fair and transparent.
            </p>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="glass-card p-6 rounded-xl">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-lg bg-warning/10 flex items-center justify-center">
                    <Shield className="w-5 h-5 text-warning" />
                  </div>
                  <div>
                    <h3 className="font-semibold">Spending Limits</h3>
                    <p className="text-sm text-muted-foreground">
                      Set limits for individual transactions
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="minExpense">Minimum Expense</Label>
                    <div className="relative">
                      <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                      <Input
                        id="minExpense"
                        name="minExpense"
                        type="number"
                        placeholder="10"
                        value={formData.minExpense}
                        onChange={handleInputChange}
                        className="h-12 pl-11 bg-background border-border focus:border-primary"
                      />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Minimum amount per expense
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="maxExpense">Maximum Expense</Label>
                    <div className="relative">
                      <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                      <Input
                        id="maxExpense"
                        name="maxExpense"
                        type="number"
                        placeholder="No limit"
                        value={formData.maxExpense}
                        onChange={handleInputChange}
                        className="h-12 pl-11 bg-background border-border focus:border-primary"
                      />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Maximum amount per expense
                    </p>
                  </div>
                </div>
              </div>

              <div className="glass-card p-6 rounded-xl">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Check className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-semibold">Approval Settings</h3>
                    <p className="text-sm text-muted-foreground">
                      Control when expenses need approval
                    </p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-background rounded-lg">
                    <div>
                      <p className="font-medium">Require approval for all expenses</p>
                      <p className="text-sm text-muted-foreground">All expenses must be approved by you</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, requireApproval: !formData.requireApproval })}
                      className={`w-12 h-6 rounded-full transition-colors ${
                        formData.requireApproval ? 'bg-primary' : 'bg-muted'
                      }`}
                    >
                      <div
                        className={`w-5 h-5 bg-white rounded-full transition-transform ${
                          formData.requireApproval ? 'translate-x-6' : 'translate-x-0.5'
                        }`}
                      />
                    </button>
                  </div>

                  {!formData.requireApproval && (
                    <div className="space-y-2">
                      <Label htmlFor="approvalThreshold">Auto-approve expenses under</Label>
                      <div className="relative">
                        <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                        <Input
                          id="approvalThreshold"
                          name="approvalThreshold"
                          type="number"
                          placeholder="100"
                          value={formData.approvalThreshold}
                          onChange={handleInputChange}
                          className="h-12 pl-11 bg-background border-border focus:border-primary"
                        />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Expenses above this amount need your approval
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex gap-4">
                <Button
                  type="button"
                  variant="outline"
                  size="lg"
                  onClick={() => setStep(1)}
                  className="flex-1"
                >
                  Back
                </Button>
                <Button
                  type="submit"
                  variant="gradient"
                  size="lg"
                  className="flex-1"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    'Create Event'
                  )}
                </Button>
              </div>
            </form>
          </motion.div>
        )}

        {/* Step 3: Success */}
        {step === 3 && createdEvent && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center"
          >
            <div className="w-20 h-20 rounded-full gradient-primary mx-auto mb-6 flex items-center justify-center">
              <Check className="w-10 h-10 text-primary-foreground" />
            </div>

            <h1 className="text-3xl font-display font-bold mb-2">Event Created!</h1>
            <p className="text-muted-foreground mb-8">
              Share the code or link with your group to invite them.
            </p>

            <div className="glass-card p-8 rounded-xl mb-8">
              <div className="mb-6">
                <p className="text-sm text-muted-foreground mb-2">Join Code</p>
                <div className="flex items-center justify-center gap-3">
                  <span className="text-4xl font-display font-bold tracking-widest gradient-text">
                    {createdEvent.code}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => copyToClipboard(createdEvent.code)}
                  >
                    {copied ? (
                      <Check className="w-5 h-5 text-success" />
                    ) : (
                      <Copy className="w-5 h-5" />
                    )}
                  </Button>
                </div>
              </div>

              <div className="pt-6 border-t border-border">
                <p className="text-sm text-muted-foreground mb-3">Or share this link</p>
                <div className="flex items-center gap-2">
                  <Input
                    value={createdEvent.link}
                    readOnly
                    className="bg-background text-center font-mono text-sm"
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => copyToClipboard(createdEvent.link)}
                  >
                    <Copy className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>

            <div className="flex gap-4">
              <Button
                variant="outline"
                size="lg"
                className="flex-1"
                onClick={() => {
                  // Share functionality
                  if (navigator.share) {
                    navigator.share({
                      title: formData.name,
                      text: `Join my event "${formData.name}" on Cooper`,
                      url: createdEvent.link,
                    });
                  }
                }}
              >
                <Share2 className="w-5 h-5" />
                Share
              </Button>
              <Link to={`/events/${createdEvent.id}`} className="flex-1">
                <Button variant="gradient" size="lg" className="w-full">
                  Go to Event
                </Button>
              </Link>
            </div>
          </motion.div>
        )}
      </main>
    </div>
  );
}
