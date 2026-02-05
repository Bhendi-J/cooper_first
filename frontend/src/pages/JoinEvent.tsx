import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Wallet,
  Users,
  Calendar,
  Loader2,
  CheckCircle2,
  ArrowRight,
  LogIn,
  DollarSign,
  AlertCircle,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { eventsAPI } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';

export default function JoinEvent() {
  const { code } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { isAuthenticated } = useAuthStore();

  const [isLoading, setIsLoading] = useState(true);
  const [isJoining, setIsJoining] = useState(false);
  const [eventPreview, setEventPreview] = useState<{
    _id?: string;
    name?: string;
    description?: string;
    creator_name: string;
    participant_count: number;
    start_date?: string;
    end_date?: string;
    status?: string;
    min_deposit?: number;
    max_deposit?: number;
    deposit_required?: boolean;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [depositAmount, setDepositAmount] = useState('');

  useEffect(() => {
    const fetchEventPreview = async () => {
      if (!code) {
        setError('Invalid invite code');
        setIsLoading(false);
        return;
      }

      try {
        const response = await eventsAPI.getByInviteCode(code);
        setEventPreview(response.data.event);
        if (response.data.event.min_deposit) {
          setDepositAmount(response.data.event.min_deposit.toString());
        }
      } catch (err: any) {
        setError(err.response?.data?.error || 'Invalid or expired invite code');
      } finally {
        setIsLoading(false);
      }
    };

    fetchEventPreview();
  }, [code]);

  const handleJoin = async () => {
    if (!code || !isAuthenticated) return;

    // Validate deposit amount if required
    if (eventPreview?.deposit_required) {
      const deposit = parseFloat(depositAmount);
      const minDep = eventPreview.min_deposit || 0;
      const maxDep = eventPreview.max_deposit || Infinity;

      if (isNaN(deposit) || deposit < minDep) {
        toast({
          title: 'Deposit Required',
          description: `Minimum deposit is $${minDep.toFixed(2)}`,
          variant: 'destructive',
        });
        return;
      }

      if (maxDep !== null && deposit > maxDep) {
        toast({
          title: 'Deposit Too High',
          description: `Maximum deposit is $${maxDep.toFixed(2)}`,
          variant: 'destructive',
        });
        return;
      }
    }

    setIsJoining(true);
    try {
      const response = await eventsAPI.joinByCode(code, {
        deposit_amount: depositAmount ? parseFloat(depositAmount) : 0
      });

      // Check if approval is required
      if (response.status === 202 || response.data.status === 'pending') {
        toast({
          title: 'Request Submitted',
          description: 'Your join request has been submitted for approval. You will be notified when approved.',
        });
        navigate('/dashboard');
      } else {
        toast({
          title: 'Successfully joined!',
          description: `You've joined ${response.data.event_name}`,
        });
        navigate(`/events/${response.data.event_id}`);
      }
    } catch (err: any) {
      if (err.response?.status === 409) {
        // Already a participant
        toast({
          title: 'Already a member',
          description: 'You are already a participant of this event.',
        });
        navigate('/dashboard');
      } else if (err.response?.status === 403) {
        // Reliability restrictions or not allowed
        toast({
          title: 'Cannot join event',
          description: err.response?.data?.reason || err.response?.data?.error || 'You are not allowed to join this event.',
          variant: 'destructive',
        });
      } else {
        toast({
          title: 'Failed to join',
          description: err.response?.data?.error || 'Something went wrong',
          variant: 'destructive',
        });
      }
    } finally {
      setIsJoining(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-8 rounded-xl max-w-md text-center"
        >
          <div className="w-16 h-16 rounded-full bg-destructive/10 flex items-center justify-center mx-auto mb-4">
            <Wallet className="w-8 h-8 text-destructive" />
          </div>
          <h1 className="text-2xl font-display font-bold mb-2">Invalid Invite</h1>
          <p className="text-muted-foreground mb-6">{error}</p>
          <Link to="/">
            <Button variant="gradient">Go to Home</Button>
          </Link>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-dots opacity-20" />
      <div className="absolute top-1/4 right-1/4 w-72 h-72 bg-primary/20 rounded-full blur-[100px]" />
      <div className="absolute bottom-1/4 left-1/4 w-72 h-72 bg-secondary/20 rounded-full blur-[100px]" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 w-full max-w-md"
      >
        <div className="glass-card p-8 rounded-xl">
          {/* Header */}
          <div className="text-center mb-8">
            <Link to="/" className="inline-flex items-center gap-2 mb-6">
              <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
                <Wallet className="w-5 h-5 text-primary-foreground" />
              </div>
              <span className="text-xl font-display font-bold">Cooper</span>
            </Link>
            <h1 className="text-2xl font-display font-bold mb-2">
              You're Invited!
            </h1>
            <p className="text-muted-foreground">
              Join this shared wallet event
            </p>
          </div>

          {/* Event Preview */}
          {eventPreview && (
            <div className="bg-background-surface rounded-xl p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">{eventPreview.name}</h2>

              {eventPreview.description && (
                <p className="text-muted-foreground mb-4">{eventPreview.description}</p>
              )}

              <div className="space-y-3">
                <div className="flex items-center gap-3 text-sm">
                  <Users className="w-4 h-4 text-muted-foreground" />
                  <span>{eventPreview.participant_count} participants</span>
                </div>

                <div className="flex items-center gap-3 text-sm">
                  <CheckCircle2 className="w-4 h-4 text-muted-foreground" />
                  <span>Created by {eventPreview.creator_name}</span>
                </div>

                {(eventPreview.start_date || eventPreview.end_date) && (
                  <div className="flex items-center gap-3 text-sm">
                    <Calendar className="w-4 h-4 text-muted-foreground" />
                    <span>
                      {eventPreview.start_date || 'TBD'} - {eventPreview.end_date || 'TBD'}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Deposit Input - show if deposit is required */}
          {eventPreview?.deposit_required && isAuthenticated && (
            <div className="bg-warning/10 border border-warning/30 rounded-xl p-4 mb-6">
              <div className="flex items-center gap-2 mb-3">
                <AlertCircle className="w-5 h-5 text-warning" />
                <span className="font-semibold text-warning">Deposit Required</span>
              </div>
              <p className="text-sm text-muted-foreground mb-3">
                This event requires a deposit to join.
                {eventPreview.min_deposit && eventPreview.max_deposit
                  ? ` Amount must be between $${eventPreview.min_deposit} - $${eventPreview.max_deposit}`
                  : eventPreview.min_deposit
                    ? ` Minimum: $${eventPreview.min_deposit}`
                    : eventPreview.max_deposit
                      ? ` Maximum: $${eventPreview.max_deposit}`
                      : ''}
              </p>
              <div className="space-y-2">
                <Label htmlFor="depositAmount">Your Deposit Amount</Label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                  <Input
                    id="depositAmount"
                    type="number"
                    placeholder={eventPreview.min_deposit?.toString() || "Enter amount"}
                    value={depositAmount}
                    onChange={(e) => setDepositAmount(e.target.value)}
                    className="pl-10 h-12"
                    min={eventPreview.min_deposit || 0}
                    max={eventPreview.max_deposit || undefined}
                    required
                  />
                </div>
              </div>
            </div>
          )}

          {/* Actions */}
          {isAuthenticated ? (
            <Button
              variant="gradient"
              size="lg"
              className="w-full"
              onClick={handleJoin}
              disabled={isJoining || (eventPreview?.deposit_required && !depositAmount)}
            >
              {isJoining ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  {eventPreview?.deposit_required && depositAmount
                    ? `Join & Deposit $${parseFloat(depositAmount).toFixed(2)}`
                    : 'Join Event'}
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </Button>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-center text-muted-foreground">
                Sign in or create an account to join this event
              </p>
              <div className="flex gap-3">
                <Link to={`/login?redirect=/join/${code}`} className="flex-1">
                  <Button variant="gradient" size="lg" className="w-full">
                    <LogIn className="w-5 h-5" />
                    Log In
                  </Button>
                </Link>
                <Link to={`/signup?redirect=/join/${code}`} className="flex-1">
                  <Button variant="outline" size="lg" className="w-full">
                    Sign Up
                  </Button>
                </Link>
              </div>
            </div>
          )}

          {/* Footer */}
          <p className="text-xs text-center text-muted-foreground mt-6">
            By joining, you agree to split expenses fairly with other participants.
          </p>
        </div>
      </motion.div>
    </div>
  );
}
