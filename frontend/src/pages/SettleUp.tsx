import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { settlementsAPI, eventsAPI, Balance, Debt } from '@/lib/api';
import {
    Wallet,
    ArrowLeft,
    ArrowRight,
    CheckCircle,
    Users,
    DollarSign,
    TrendingUp,
    TrendingDown,
    Send,
    Loader2,
    Sparkles,
    CreditCard,
} from 'lucide-react';

export default function SettleUp() {
    const { id: eventId } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { toast } = useToast();

    const [loading, setLoading] = useState(true);
    const [settling, setSettling] = useState<string | null>(null);
    const [balances, setBalances] = useState<Balance[]>([]);
    const [debts, setDebts] = useState<Debt[]>([]);
    const [totalOwed, setTotalOwed] = useState(0);
    const [eventName, setEventName] = useState('');

    useEffect(() => {
        if (eventId) {
            loadData();
        }
    }, [eventId]);

    const loadData = async () => {
        try {
            setLoading(true);

            // Load event info
            const eventRes = await eventsAPI.getById(eventId!);
            setEventName(eventRes.data.name);

            // Load balances and debts
            const [balancesRes, debtsRes] = await Promise.all([
                settlementsAPI.getBalances(eventId!),
                settlementsAPI.getDebts(eventId!)
            ]);

            setBalances(balancesRes.data.balances);
            setDebts(debtsRes.data.debts);
            setTotalOwed(debtsRes.data.total_owed);
        } catch (error: any) {
            toast({
                title: 'Error',
                description: error.response?.data?.error || 'Failed to load settlement data',
                variant: 'destructive',
            });
        } finally {
            setLoading(false);
        }
    };

    const handleSettle = async (debt: Debt) => {
        setSettling(`${debt.from_user}-${debt.to_user}`);
        try {
            // Record the settlement
            await settlementsAPI.settle({
                event_id: eventId!,
                from_user_id: debt.from_user,
                to_user_id: debt.to_user,
                amount: debt.amount,
                payment_method: 'finternet'
            });

            toast({
                title: '🎉 Settlement Recorded!',
                description: `${debt.from_username} paid $${debt.amount.toFixed(2)} to ${debt.to_username}`,
            });

            // Reload data
            await loadData();
        } catch (error: any) {
            toast({
                title: 'Error',
                description: error.response?.data?.error || 'Failed to record settlement',
                variant: 'destructive',
            });
        } finally {
            setSettling(null);
        }
    };

    const handleFinalizeAll = async () => {
        try {
            await settlementsAPI.finalize(eventId!);
            toast({
                title: '✅ All Settled!',
                description: 'The event has been finalized.',
            });
            navigate(`/events/${eventId}`);
        } catch (error: any) {
            toast({
                title: 'Cannot Finalize',
                description: error.response?.data?.error || 'Some balances are not settled',
                variant: 'destructive',
            });
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    const allSettled = debts.length === 0;

    return (
        <div className="min-h-screen bg-background">
            {/* Header */}
            <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
                <div className="container mx-auto px-6 py-4 flex items-center justify-between">
                    <Link to={`/events/${eventId}`} className="flex items-center gap-2">
                        <Button variant="ghost" size="sm">
                            <ArrowLeft className="w-4 h-4 mr-2" />
                            Back to Event
                        </Button>
                    </Link>
                    <div className="flex items-center gap-2">
                        <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
                            <Wallet className="w-5 h-5 text-primary-foreground" />
                        </div>
                        <span className="text-xl font-display font-bold">Settle Up</span>
                    </div>
                </div>
            </nav>

            <main className="container mx-auto px-6 py-8 max-w-4xl">
                {/* Event Title */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center mb-8"
                >
                    <h1 className="text-3xl font-display font-bold gradient-text mb-2">
                        {eventName}
                    </h1>
                    <p className="text-muted-foreground">
                        {allSettled ? 'All settled up! 🎉' : `$${totalOwed.toFixed(2)} total to settle`}
                    </p>
                </motion.div>

                {/* Balance Cards */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="mb-8"
                >
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <Users className="w-5 h-5" />
                        Participant Balances
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {balances.map((balance, index) => (
                            <motion.div
                                key={balance.user_id}
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: index * 0.05 }}
                                className={`glass-card p-4 rounded-xl border-2 ${balance.balance > 0
                                        ? 'border-success/30 bg-success/5'
                                        : balance.balance < 0
                                            ? 'border-destructive/30 bg-destructive/5'
                                            : 'border-border'
                                    }`}
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${balance.balance > 0
                                                ? 'bg-success/20 text-success'
                                                : balance.balance < 0
                                                    ? 'bg-destructive/20 text-destructive'
                                                    : 'bg-muted text-muted-foreground'
                                            }`}>
                                            {balance.balance > 0 ? (
                                                <TrendingUp className="w-5 h-5" />
                                            ) : balance.balance < 0 ? (
                                                <TrendingDown className="w-5 h-5" />
                                            ) : (
                                                <CheckCircle className="w-5 h-5" />
                                            )}
                                        </div>
                                        <div>
                                            <p className="font-medium">{balance.username}</p>
                                            <p className="text-xs text-muted-foreground">
                                                Spent: ${balance.total_spent.toFixed(2)}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <p className={`text-lg font-bold ${balance.balance > 0
                                                ? 'text-success'
                                                : balance.balance < 0
                                                    ? 'text-destructive'
                                                    : ''
                                            }`}>
                                            {balance.balance >= 0 ? '+' : ''}${balance.balance.toFixed(2)}
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            {balance.balance > 0 ? 'is owed' : balance.balance < 0 ? 'owes' : 'settled'}
                                        </p>
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </motion.div>

                {/* Suggested Settlements */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="mb-8"
                >
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <Send className="w-5 h-5" />
                        Suggested Payments
                    </h2>

                    {debts.length === 0 ? (
                        <div className="glass-card p-8 rounded-xl text-center">
                            <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ type: 'spring', stiffness: 200 }}
                                className="w-20 h-20 rounded-full bg-success/20 flex items-center justify-center mx-auto mb-4"
                            >
                                <Sparkles className="w-10 h-10 text-success" />
                            </motion.div>
                            <h3 className="text-xl font-bold mb-2">All Settled Up!</h3>
                            <p className="text-muted-foreground mb-6">
                                Everyone's balances are squared away.
                            </p>
                            <Button variant="gradient" onClick={handleFinalizeAll}>
                                <CheckCircle className="w-4 h-4 mr-2" />
                                Finalize Event
                            </Button>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            <AnimatePresence>
                                {debts.map((debt, index) => (
                                    <motion.div
                                        key={`${debt.from_user}-${debt.to_user}`}
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0, x: 20 }}
                                        transition={{ delay: index * 0.05 }}
                                        className="glass-card p-4 rounded-xl flex items-center justify-between"
                                    >
                                        <div className="flex items-center gap-4">
                                            {/* From User */}
                                            <div className="flex items-center gap-2">
                                                <div className="w-10 h-10 rounded-full bg-destructive/20 flex items-center justify-center">
                                                    <span className="font-medium text-destructive">
                                                        {debt.from_username.charAt(0).toUpperCase()}
                                                    </span>
                                                </div>
                                                <span className="font-medium">{debt.from_username}</span>
                                            </div>

                                            {/* Arrow */}
                                            <div className="flex items-center gap-2 px-4">
                                                <ArrowRight className="w-5 h-5 text-muted-foreground" />
                                                <span className="font-bold text-primary">
                                                    ${debt.amount.toFixed(2)}
                                                </span>
                                                <ArrowRight className="w-5 h-5 text-muted-foreground" />
                                            </div>

                                            {/* To User */}
                                            <div className="flex items-center gap-2">
                                                <div className="w-10 h-10 rounded-full bg-success/20 flex items-center justify-center">
                                                    <span className="font-medium text-success">
                                                        {debt.to_username.charAt(0).toUpperCase()}
                                                    </span>
                                                </div>
                                                <span className="font-medium">{debt.to_username}</span>
                                            </div>
                                        </div>

                                        {/* Pay Button */}
                                        <Button
                                            variant="gradient"
                                            size="sm"
                                            onClick={() => handleSettle(debt)}
                                            disabled={settling !== null}
                                        >
                                            {settling === `${debt.from_user}-${debt.to_user}` ? (
                                                <>
                                                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                                                    Processing...
                                                </>
                                            ) : (
                                                <>
                                                    <CreditCard className="w-4 h-4 mr-2" />
                                                    Pay
                                                </>
                                            )}
                                        </Button>
                                    </motion.div>
                                ))}
                            </AnimatePresence>
                        </div>
                    )}
                </motion.div>

                {/* Quick Info */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="glass-card p-6 rounded-xl"
                >
                    <h3 className="font-semibold mb-4 flex items-center gap-2">
                        <DollarSign className="w-5 h-5" />
                        How it works
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                        <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                                <span className="text-primary font-bold">1</span>
                            </div>
                            <p className="text-muted-foreground">
                                We calculate who owes money and who is owed based on all expenses.
                            </p>
                        </div>
                        <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                                <span className="text-primary font-bold">2</span>
                            </div>
                            <p className="text-muted-foreground">
                                Payment suggestions minimize the number of transactions needed.
                            </p>
                        </div>
                        <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                                <span className="text-primary font-bold">3</span>
                            </div>
                            <p className="text-muted-foreground">
                                Click "Pay" to record a settlement (Finternet blockchain).
                            </p>
                        </div>
                    </div>
                </motion.div>
            </main>
        </div>
    );
}
