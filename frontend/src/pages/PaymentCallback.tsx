import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { getPaymentStatus, getPaymentTrackingStatus, simulatePaymentSuccess } from '@/lib/paymentApi';
import { eventsAPI, expensesAPI } from '@/lib/api';

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

type PaymentStatusType = 'loading' | 'success' | 'processing' | 'failed';

export default function PaymentCallback() {
    const navigate = useNavigate();
    const { toast } = useToast();
    const [searchParams] = useSearchParams();

    // Get intent ID from URL or localStorage
    const intentIdFromUrl = searchParams.get('intent');
    const intentId = intentIdFromUrl || localStorage.getItem('finternet_intent_id') || localStorage.getItem('pendingPaymentIntentId');
    const returnUrl = localStorage.getItem('finternet_return_url') || '/dashboard';
    
    // Check if this is an expense payment (vs deposit)
    const pendingExpenseId = localStorage.getItem('pendingExpenseId');
    const pendingEventId = localStorage.getItem('pendingExpenseEventId');
    const isExpensePayment = !!pendingExpenseId;

    const [status, setStatus] = useState<PaymentStatusType>('loading');
    const [paymentData, setPaymentData] = useState<any>(null);
    const [pollCount, setPollCount] = useState(0);
    const [isSimulating, setIsSimulating] = useState(false);

    // Handle pending expense payment confirmation
    const handlePendingExpense = async () => {
        if (!pendingExpenseId) return false;
        
        try {
            const response = await expensesAPI.confirmPayment(pendingExpenseId);
            
            if (response.data.expense_id) {
                setPaymentData({
                    ...paymentData,
                    expense_id: response.data.expense_id,
                    amount: response.data.amount,
                    purpose: 'expense',
                });
                
                toast({
                    title: '🎉 Expense Created!',
                    description: `$${response.data.amount} expense has been recorded.`,
                });
                
                // Cleanup localStorage
                localStorage.removeItem('pendingExpenseId');
                localStorage.removeItem('pendingExpenseEventId');
                localStorage.removeItem('pendingPaymentIntentId');
                
                return true;
            }
            return false;
        } catch (error: any) {
            console.error('Failed to confirm expense:', error);
            const paymentStatus = error.response?.data?.payment_status;
            
            // If payment is still processing, don't treat as failure
            if (paymentStatus === 'PROCESSING' || paymentStatus === 'INITIATED') {
                return false; // Not ready yet
            }
            
            // Real failure
            throw error;
        }
    };

    // Handle pending deposit after payment success
    const handlePendingDeposit = async (amount: number) => {
        const pendingEventId = localStorage.getItem('pending_deposit_event_id');
        const pendingAmount = localStorage.getItem('pending_deposit_amount');

        if (pendingEventId && pendingAmount) {
            try {
                await eventsAPI.deposit(pendingEventId, parseFloat(pendingAmount));
                toast({
                    title: 'Deposit Added!',
                    description: `$${pendingAmount} has been added to your event balance.`,
                });
            } catch (error) {
                console.error('Failed to process deposit:', error);
                // Don't show error - the payment was successful, just the local update failed
            }
        }
    };

    // Manual confirm for demo/testing
    const handleSimulateSuccess = async () => {
        if (!intentId) return;
        
        setIsSimulating(true);
        try {
            const result = await simulatePaymentSuccess(intentId);
            
            // Payment confirmed - set success immediately
            setStatus('success');
            setPaymentData({
                amount: result.amount,
                purpose: result.purpose,
                transaction_hash: result.transactionHash,
            });
            
            toast({
                title: '🎉 Payment Confirmed!',
                description: 'Your deposit has been added to your balance.',
            });
            
            // Cleanup localStorage
            localStorage.removeItem('finternet_intent_id');
            localStorage.removeItem('pending_deposit_event_id');
            localStorage.removeItem('pending_deposit_amount');
            
            // Auto-redirect after 2 seconds
            setTimeout(() => {
                navigate(returnUrl);
            }, 2000);
            
        } catch (error: any) {
            console.error('Simulation error:', error);
            toast({
                title: 'Confirmation failed',
                description: error.message || 'Could not confirm payment',
                variant: 'destructive',
            });
        } finally {
            setIsSimulating(false);
        }
    };

    const checkStatus = useCallback(async () => {
        if (!intentId) {
            // For expense payments, we can still try to confirm even without intent ID
            if (isExpensePayment && pendingExpenseId) {
                try {
                    const success = await handlePendingExpense();
                    if (success) {
                        setStatus('success');
                        return;
                    }
                } catch (error) {
                    console.error('Expense confirmation failed:', error);
                }
            }
            setStatus('failed');
            return;
        }

        try {
            // First try Finternet API to check payment status
            const finternetData = await getPaymentStatus(intentId);
            setPaymentData(finternetData);
            
            if (finternetData.status === 'SUCCEEDED' || finternetData.status === 'SETTLED' || finternetData.status === 'FINAL') {
                // Handle expense payment vs deposit
                if (isExpensePayment) {
                    try {
                        const success = await handlePendingExpense();
                        if (success) {
                            setStatus('success');
                            // Auto-redirect after 2 seconds
                            setTimeout(() => navigate(returnUrl), 2000);
                            return;
                        }
                    } catch (error) {
                        console.error('Expense confirmation failed:', error);
                        setStatus('failed');
                        return;
                    }
                }
                
                setStatus('success');
                
                // Handle pending deposit if any
                await handlePendingDeposit(parseFloat(finternetData.amount) || 0);
                
                // Cleanup localStorage
                localStorage.removeItem('finternet_intent_id');
                localStorage.removeItem('finternet_return_url');
                localStorage.removeItem('pending_deposit_event_id');
                localStorage.removeItem('pending_deposit_amount');
                
                toast({
                    title: '🎉 Payment Confirmed!',
                    description: `Your payment has been processed successfully.`,
                });
                
                // Auto-redirect after 2 seconds
                setTimeout(() => navigate(returnUrl), 2000);
                return;
            } else if (finternetData.status === 'CANCELLED') {
                setStatus('failed');
                return;
            } else {
                // Finternet shows PROCESSING - but check our internal status
                // This handles the case when simulate-success was used
                try {
                    const trackingData = await getPaymentTrackingStatus(intentId);
                    if (trackingData.status === 'confirmed') {
                        setPaymentData(trackingData);
                        setStatus('success');
                        await handlePendingDeposit(trackingData.amount);
                        localStorage.removeItem('finternet_intent_id');
                        localStorage.removeItem('finternet_return_url');
                        localStorage.removeItem('pending_deposit_event_id');
                        localStorage.removeItem('pending_deposit_amount');
                        
                        toast({
                            title: '🎉 Payment Confirmed!',
                            description: `₹${trackingData.amount} has been added to your balance.`,
                        });
                        
                        // Auto-redirect after 2 seconds
                        setTimeout(() => navigate(returnUrl), 2000);
                        return;
                    }
                } catch (e) {
                    // Internal check failed, continue with processing status
                    console.log('Internal status check failed:', e);
                }
                setStatus('processing');
            }
        } catch (error: any) {
            console.error('Failed to check payment status:', error);
            
            // Try internal tracking as fallback
            try {
                const trackingData = await getPaymentTrackingStatus(intentId);
                setPaymentData(trackingData);

                if (trackingData.status === 'confirmed') {
                    setStatus('success');
                    await handlePendingDeposit(trackingData.amount);
                    localStorage.removeItem('finternet_intent_id');
                    localStorage.removeItem('finternet_return_url');
                    localStorage.removeItem('pending_deposit_event_id');
                    localStorage.removeItem('pending_deposit_amount');
                    
                    toast({
                        title: '🎉 Payment Confirmed!',
                        description: `₹${trackingData.amount} has been added to your balance.`,
                    });
                    
                    // Auto-redirect after 2 seconds
                    setTimeout(() => navigate(returnUrl), 2000);
                    return;
                } else if (trackingData.status === 'failed' || trackingData.status === 'cancelled') {
                    setStatus('failed');
                    return;
                }
                setStatus('processing');
            } catch (trackingError) {
                // Both APIs failed
                if (pollCount < 10) {
                    setStatus('processing');
                } else {
                    setStatus('failed');
                }
            }
        }
    }, [intentId, pollCount, toast]);

    // Initial status check
    useEffect(() => {
        checkStatus();
    }, [checkStatus]);

    // Polling effect
    useEffect(() => {
        if (!intentId || status === 'success' || status === 'failed') {
            return;
        }

        // Poll every 3 seconds if still processing
        const interval = setInterval(() => {
            setPollCount((p) => p + 1);
            checkStatus();
        }, 3000);

        // Stop polling after 2 minutes
        const timeout = setTimeout(() => {
            clearInterval(interval);
            if (status === 'processing' || status === 'loading') {
                setStatus('failed');
            }
        }, 120000);

        return () => {
            clearInterval(interval);
            clearTimeout(timeout);
        };
    }, [intentId, status, checkStatus]);

    const handleRetry = () => {
        // For expense payments, go back to add expense page
        if (isExpensePayment && pendingEventId) {
            navigate(`/events/${pendingEventId}/expense/add`);
        } else {
            navigate('/payment');
        }
    };

    const handleContinue = () => {
        // For expense payments, go back to the event page
        if (isExpensePayment && pendingEventId) {
            navigate(`/events/${pendingEventId}`);
        } else {
            navigate(returnUrl);
        }
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
                                            <span className="font-medium capitalize">{paymentData.status}</span>
                                        </div>
                                        <div className="flex justify-between p-3 bg-background-surface rounded-lg">
                                            <span className="text-muted-foreground">Amount</span>
                                            <span className="font-medium">${paymentData.amount} USDC</span>
                                        </div>
                                    </div>
                                )}
                                <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground mb-6">
                                    <RefreshCw className="w-4 h-4 animate-spin" />
                                    Checking status... ({pollCount})
                                </div>
                                
                                {/* Demo: Manual confirm button */}
                                <div className="border-t border-border pt-6 mt-6">
                                    <p className="text-sm text-muted-foreground mb-3">
                                        Completed payment on Finternet? Click below to confirm:
                                    </p>
                                    <Button 
                                        variant="gradient" 
                                        onClick={handleSimulateSuccess}
                                        disabled={isSimulating}
                                    >
                                        {isSimulating ? (
                                            <>
                                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                                Confirming...
                                            </>
                                        ) : (
                                            <>
                                                <CheckCircle className="w-4 h-4 mr-2" />
                                                Confirm Payment
                                            </>
                                        )}
                                    </Button>
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
                                    Your payment has been confirmed and your balance has been updated.
                                </p>
                                {paymentData && (
                                    <div className="space-y-2 mb-6">
                                        <div className="flex justify-between p-3 bg-background-surface rounded-lg">
                                            <span className="text-muted-foreground">Amount Paid</span>
                                            <span className="font-bold text-success">
                                                ${paymentData.amount} USDC
                                            </span>
                                        </div>
                                        {paymentData.purpose && (
                                            <div className="flex justify-between p-3 bg-background-surface rounded-lg">
                                                <span className="text-muted-foreground">Purpose</span>
                                                <span className="font-medium capitalize">{paymentData.purpose}</span>
                                            </div>
                                        )}
                                        {paymentData.transaction_hash && (
                                            <div className="flex justify-between p-3 bg-background-surface rounded-lg">
                                                <span className="text-muted-foreground">Transaction</span>
                                                <span className="font-mono text-sm">
                                                    {paymentData.transaction_hash.slice(0, 10)}...
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
