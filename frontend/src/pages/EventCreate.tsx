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
    initialDeposit: '',
    maxExpense: '',
    approvalThreshold: '',
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
      const response = await eventsAPI.create({
        name: formData.name,
        description: formData.description || undefined,
        start_date: formData.startDate || undefined,
        end_date: formData.endDate || undefined,
        rules: {
          spending_limit: formData.maxExpense ? parseFloat(formData.maxExpense) : undefined,
          approval_required: !!formData.approvalThreshold,
          auto_approve_under: formData.approvalThreshold ? parseFloat(formData.approvalThreshold) : undefined,
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

              <div className="space-y-2">
                <Label htmlFor="initialDeposit">Initial Deposit per Person</Label>
                <div className="relative">
                  <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                  <Input
                    id="initialDeposit"
                    name="initialDeposit"
                    type="number"
                    placeholder="5000"
                    value={formData.initialDeposit}
                    onChange={handleInputChange}
                    className="h-12 pl-11 bg-background-surface border-border focus:border-primary"
                    required
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Each member will deposit this amount to join the event
                </p>
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
                      Set maximum amounts for transactions
                    </p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="maxExpense">Maximum Single Expense</Label>
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
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="approvalThreshold">Require Approval Above</Label>
                    <div className="relative">
                      <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                      <Input
                        id="approvalThreshold"
                        name="approvalThreshold"
                        type="number"
                        placeholder="10000"
                        value={formData.approvalThreshold}
                        onChange={handleInputChange}
                        className="h-12 pl-11 bg-background border-border focus:border-primary"
                      />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Expenses above this amount need group approval
                    </p>
                  </div>
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
