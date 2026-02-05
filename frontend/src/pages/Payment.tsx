import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { createPaymentIntent } from '@/lib/paymentApi';
import {
    Wallet,
    CreditCard,
    ArrowLeft,
    Loader2,
    ExternalLink,
    Shield,
    CheckCircle,
} from 'lucide-react';

export default function Payment() {
    const navigate = useNavigate();
    const { toast } = useToast();
    const [searchParams] = useSearchParams();

    // Get payment details from URL params
    const amount = searchParams.get('amount') || '10.00';
    const description = searchParams.get('description') || 'Cooper Payment';
    const returnUrl = searchParams.get('returnUrl') || '/dashboard';

    const [isLoading, setIsLoading] = useState(false);
    const [paymentUrl, setPaymentUrl] = useState<string | null>(null);
    const [intentId, setIntentId] = useState<string | null>(null);

    const handleCreatePayment = async () => {
        setIsLoading(true);
        try {
            const intent = await createPaymentIntent({
                amount,
                currency: 'USD',
                description,
            });

            setIntentId(intent.id);
            setPaymentUrl(intent.paymentUrl || null);

            toast({
                title: 'Payment Created',
                description: 'Redirecting to Finternet payment page...',
            });

            // Open Finternet payment page in new tab
            if (intent.paymentUrl) {
                // Store the intent ID and return URL for reference
                localStorage.setItem('finternet_intent_id', intent.id);
                localStorage.setItem('finternet_return_url', returnUrl);
                // Open in new tab instead of redirecting
                window.open(intent.paymentUrl, '_blank');
                
                toast({
                    title: 'Payment Page Opened',
                    description: 'Complete the payment in the new tab.',
                });
                
                // Navigate back to the return URL
                setTimeout(() => {
                    navigate(returnUrl);
                }, 1500);
            }
        } catch (error: any) {
            toast({
                title: 'Payment Failed',
                description: error.message || 'Failed to create payment. Please try again.',
                variant: 'destructive',
            });
        } finally {
            setIsLoading(false);
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
                    <Button variant="ghost" onClick={() => navigate(-1)}>
                        <ArrowLeft className="w-5 h-5 mr-2" />
                        Back
                    </Button>
                </div>
            </nav>

            <main className="container mx-auto px-6 py-12">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="max-w-lg mx-auto"
                >
                    {/* Payment Card */}
                    <div className="glass-card p-8 rounded-2xl">
                        <div className="text-center mb-8">
                            <div className="w-16 h-16 rounded-2xl gradient-primary flex items-center justify-center mx-auto mb-4">
                                <CreditCard className="w-8 h-8 text-primary-foreground" />
                            </div>
                            <h1 className="text-2xl font-display font-bold mb-2">Complete Payment</h1>
                            <p className="text-muted-foreground">
                                Secure payment via Finternet Payment Gateway
                            </p>
                        </div>

                        {/* Payment Details */}
                        <div className="space-y-4 mb-8">
                            <div className="flex justify-between items-center p-4 bg-background-surface rounded-xl">
                                <span className="text-muted-foreground">Amount</span>
                                <span className="text-2xl font-bold">${amount} USDC</span>
                            </div>
                            <div className="flex justify-between items-center p-4 bg-background-surface rounded-xl">
                                <span className="text-muted-foreground">Description</span>
                                <span className="font-medium text-right max-w-[200px] truncate">
                                    {description}
                                </span>
                            </div>
                        </div>

                        {/* Security Info */}
                        <div className="flex items-start gap-3 p-4 bg-success/10 rounded-xl mb-8">
                            <Shield className="w-5 h-5 text-success flex-shrink-0 mt-0.5" />
                            <div>
                                <p className="text-sm font-medium text-success">Secure Blockchain Payment</p>
                                <p className="text-xs text-muted-foreground mt-1">
                                    Your payment is processed securely via Finternet's programmable payment gateway
                                    using blockchain technology.
                                </p>
                            </div>
                        </div>

                        {/* Action Button */}
                        <Button
                            variant="gradient"
                            size="lg"
                            className="w-full"
                            onClick={handleCreatePayment}
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Creating Payment...
                                </>
                            ) : (
                                <>
                                    Pay ${amount} USDC
                                    <ExternalLink className="w-4 h-4 ml-2" />
                                </>
                            )}
                        </Button>

                        <p className="text-xs text-muted-foreground text-center mt-4">
                            You'll be redirected to Finternet to complete this payment with your crypto wallet.
                        </p>
                    </div>

                    {/* How it works */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        className="mt-8"
                    >
                        <h2 className="text-lg font-semibold mb-4 text-center">How it works</h2>
                        <div className="space-y-3">
                            {[
                                { step: 1, text: 'Click "Pay" to create a secure payment request' },
                                { step: 2, text: 'Connect your crypto wallet on Finternet' },
                                { step: 3, text: 'Sign the transaction to authorize payment' },
                                { step: 4, text: 'Return to Cooper with payment confirmed' },
                            ].map((item) => (
                                <div
                                    key={item.step}
                                    className="flex items-center gap-4 p-3 bg-background-surface rounded-xl"
                                >
                                    <div className="w-8 h-8 rounded-full gradient-primary-subtle flex items-center justify-center text-sm font-bold text-primary">
                                        {item.step}
                                    </div>
                                    <p className="text-sm text-muted-foreground">{item.text}</p>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                </motion.div>
            </main>
        </div>
    );
}
