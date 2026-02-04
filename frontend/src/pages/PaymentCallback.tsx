import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { getPaymentStatus } from '@/lib/paymentApi';
import { eventsAPI } from '@/lib/api';

import {
    Wallet,
    CheckCircle,
    XCircle,
    Clock,
    Loader2,
    ArrowRight,
    RefreshCw,
    Home,
} from 'lucide-react';

type PaymentStatus = 'loading' | 'success' | 'processing' | 'failed';

export default function PaymentCallback() {
    const navigate = useNavigate();
    const { toast } = useToast();
    const [searchParams] = useSearchParams();

    // Get intent ID from URL or localStorage
    const intentIdFromUrl = searchParams.get('intent');
    const intentId = intentIdFromUrl || localStorage.getItem('finternet_intent_id');
    const returnUrl = localStorage.getItem('finternet_return_url') || '/dashboard';

    const [status, setStatus] = useState<PaymentStatus>('loading');
    const [paymentData, setPaymentData] = useState<any>(null);
    const [pollCount, setPollCount] = useState(0);

    useEffect(() => {
        if (!intentId) {
            setStatus('failed');
            return;
        }

        const checkStatus = async () => {
            try {
                const data = await getPaymentStatus(intentId);
                setPaymentData(data);

                if (data.status === 'SUCCEEDED' || data.status === 'SETTLED' || data.status === 'FINAL') {
                    setStatus('success');
                    // Cleanup localStorage
                    localStorage.removeItem('finternet_intent_id');
                    localStorage.removeItem('finternet_return_url');
                } else if (data.status === 'PROCESSING') {
                    setStatus('processing');
                } else if (data.status === 'INITIATED') {
                    // Still waiting - keep polling
                    setStatus('processing');
                } else if (data.status === 'CANCELLED') {
                    setStatus('failed');
                } else {
                    setStatus('processing');
                }
            } catch (error: any) {
                console.error('Failed to check payment status:', error);
                if (pollCount < 3) {
                    // Retry a few times on error
                    setPollCount((p) => p + 1);
                } else {
                    setStatus('failed');
                }
            }
        };

        checkStatus();

        // Handle post-payment actions (like event deposit)
        useEffect(() => {
            const handlePostPaymentActions = async () => {
                if (status !== 'success') return;

                const pendingEventId = localStorage.getItem('pending_deposit_event_id');
                const pendingAmount = localStorage.getItem('pending_deposit_amount');

                if (pendingEventId && pendingAmount) {
                    try {
                        // Call the deposit API
                        await eventsAPI.deposit(pendingEventId, parseFloat(pendingAmount));

                        toast({
                            title: 'Deposit Confirmed',
                            description: `₹${pendingAmount} has been added to the event pool.`,
                        });
                    } catch (error) {
                        console.error('Failed to process post-payment deposit:', error);
                        toast({
                            title: 'Deposit Update Failed',
                            description: 'Payment succeeded but failed to update event pool. Please contact support.',
                            variant: 'destructive',
                        });
                    } finally {
                        // Clean up
                        localStorage.removeItem('pending_deposit_event_id');
                        localStorage.removeItem('pending_deposit_amount');
                    }
                }
            };

            handlePostPaymentActions();
        }, [status, toast]);

        // Poll every 3 seconds if still processing
        const interval = setInterval(() => {
            if (status === 'processing' || status === 'loading') {
                setPollCount((p) => p + 1);
                checkStatus();
            }
        }, 3000);

        // Stop polling after 2 minutes
        const timeout = setTimeout(() => {
            clearInterval(interval);
        }, 120000);

        return () => {
            clearInterval(interval);
            clearTimeout(timeout);
        };
    }, [intentId, pollCount]);

    const handleRetry = () => {
        navigate('/payment');
    };

    const handleContinue = () => {
        navigate(returnUrl);
    };

    return (
        <div className="min-h-screen bg-background">
            {/* Header */}
            <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
                <div className="container mx-auto px-6 py-4 flex items-center justify-between">
                    <Link to="/dashboard" className="flex items-center gap-2">
                        <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
                            <Wallet className="w-5 h-5 text-primary-foreground" />
                        </div>
                        <span className="text-xl font-display font-bold">Cooper</span>
                    </Link>
                </div>
            </nav>

            <main className="container mx-auto px-6 py-12">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="max-w-lg mx-auto"
                >
                    <div className="glass-card p-8 rounded-2xl text-center">
                        {/* Loading State */}
                        {status === 'loading' && (
                            <>
                                <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-6">
                                    <Loader2 className="w-10 h-10 text-primary animate-spin" />
                                </div>
                                <h1 className="text-2xl font-display font-bold mb-2">
                                    Checking Payment Status
                                </h1>
                                <p className="text-muted-foreground">
                                    Please wait while we verify your payment...
                                </p>
                            </>
                        )}

                        {/* Processing State */}
                        {status === 'processing' && (
                            <>
                                <div className="w-20 h-20 rounded-full bg-warning/10 flex items-center justify-center mx-auto mb-6">
                                    <Clock className="w-10 h-10 text-warning" />
                                </div>
                                <h1 className="text-2xl font-display font-bold mb-2">
                                    Payment Processing
                                </h1>
                                <p className="text-muted-foreground mb-6">
                                    Your payment is being processed on the blockchain. This usually takes
                                    a few seconds.
                                </p>
                                {paymentData && (
                                    <div className="space-y-2 mb-6">
                                        <div className="flex justify-between p-3 bg-background-surface rounded-lg">
                                            <span className="text-muted-foreground">Status</span>
                                            <span className="font-medium">{paymentData.status}</span>
                                        </div>
                                        <div className="flex justify-between p-3 bg-background-surface rounded-lg">
                                            <span className="text-muted-foreground">Amount</span>
                                            <span className="font-medium">${paymentData.amount} USDC</span>
                                        </div>
                                    </div>
                                )}
                                <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                                    <RefreshCw className="w-4 h-4 animate-spin" />
                                    Checking status...
                                </div>
                            </>
                        )}

                        {/* Success State */}
                        {status === 'success' && (
                            <>
                                <motion.div
                                    initial={{ scale: 0 }}
                                    animate={{ scale: 1 }}
                                    transition={{ type: 'spring', stiffness: 200 }}
                                    className="w-20 h-20 rounded-full bg-success/10 flex items-center justify-center mx-auto mb-6"
                                >
                                    <CheckCircle className="w-10 h-10 text-success" />
                                </motion.div>
                                <h1 className="text-2xl font-display font-bold mb-2 gradient-text">
                                    Payment Successful!
                                </h1>
                                <p className="text-muted-foreground mb-6">
                                    Your payment has been confirmed on the blockchain.
                                </p>
                                {paymentData && (
                                    <div className="space-y-2 mb-6">
                                        <div className="flex justify-between p-3 bg-background-surface rounded-lg">
                                            <span className="text-muted-foreground">Amount Paid</span>
                                            <span className="font-bold text-success">
                                                ${paymentData.amount} USDC
                                            </span>
                                        </div>
                                        {paymentData.transactionHash && (
                                            <div className="flex justify-between p-3 bg-background-surface rounded-lg">
                                                <span className="text-muted-foreground">Transaction</span>
                                                <span className="font-mono text-sm">
                                                    {paymentData.transactionHash.slice(0, 10)}...
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                )}
                                <Button variant="gradient" size="lg" onClick={handleContinue}>
                                    Continue
                                    <ArrowRight className="w-5 h-5 ml-2" />
                                </Button>
                            </>
                        )}

                        {/* Failed State */}
                        {status === 'failed' && (
                            <>
                                <motion.div
                                    initial={{ scale: 0 }}
                                    animate={{ scale: 1 }}
                                    transition={{ type: 'spring', stiffness: 200 }}
                                    className="w-20 h-20 rounded-full bg-destructive/10 flex items-center justify-center mx-auto mb-6"
                                >
                                    <XCircle className="w-10 h-10 text-destructive" />
                                </motion.div>
                                <h1 className="text-2xl font-display font-bold mb-2">
                                    Payment Failed
                                </h1>
                                <p className="text-muted-foreground mb-6">
                                    {!intentId
                                        ? 'No payment intent found. The payment may have been cancelled.'
                                        : 'The payment could not be completed. Please try again.'}
                                </p>
                                <div className="flex flex-col gap-3">
                                    <Button variant="gradient" onClick={handleRetry}>
                                        Try Again
                                    </Button>
                                    <Button variant="outline" onClick={handleContinue}>
                                        <Home className="w-4 h-4 mr-2" />
                                        Return to Dashboard
                                    </Button>
                                </div>
                            </>
                        )}
                    </div>
                </motion.div>
            </main>
        </div>
    );
}
