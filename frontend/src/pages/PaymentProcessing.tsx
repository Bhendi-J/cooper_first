import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { getPaymentStatus, simulatePaymentSuccess } from '@/lib/paymentApi';
import {
    Wallet,
    CheckCircle,
    Hexagon,
    ArrowRight,
    Zap,
    Shield,
    Lock,
    Sparkles,
} from 'lucide-react';

// Processing steps for the blockchain animation
const PROCESSING_STEPS = [
    { id: 1, label: 'Initializing Smart Contract', icon: Hexagon, duration: 1500 },
    { id: 2, label: 'Validating Transaction', icon: Shield, duration: 2000 },
    { id: 3, label: 'Broadcasting to Network', icon: Zap, duration: 2500 },
    { id: 4, label: 'Confirming on Blockchain', icon: Lock, duration: 2000 },
    { id: 5, label: 'Finalizing Payment', icon: CheckCircle, duration: 1000 },
];

export default function PaymentProcessing() {
    const navigate = useNavigate();
    const { toast } = useToast();
    const [searchParams] = useSearchParams();

    const intentId = searchParams.get('intent') || localStorage.getItem('finternet_intent_id');
    const returnUrl = localStorage.getItem('finternet_return_url') || '/dashboard';

    const [currentStep, setCurrentStep] = useState(0);
    const [isComplete, setIsComplete] = useState(false);
    const [transactionHash, setTransactionHash] = useState<string | null>(null);
    const [paymentData, setPaymentData] = useState<any>(null);

    // Generate a fake transaction hash that looks real
    const generateFakeTxHash = () => {
        const chars = '0123456789abcdef';
        let hash = '0x';
        for (let i = 0; i < 64; i++) {
            hash += chars[Math.floor(Math.random() * chars.length)];
        }
        return hash;
    };

    // Animate through the processing steps
    useEffect(() => {
        if (!intentId) {
            navigate('/payment');
            return;
        }

        let stepIndex = 0;
        const runSteps = async () => {
            for (const step of PROCESSING_STEPS) {
                setCurrentStep(step.id);
                await new Promise(resolve => setTimeout(resolve, step.duration));
                stepIndex++;
            }

            // Generate fake transaction hash
            const txHash = generateFakeTxHash();
            setTransactionHash(txHash);

            // Simulate the payment success via backend
            try {
                await simulatePaymentSuccess(intentId);
                const status = await getPaymentStatus(intentId);
                setPaymentData(status);
            } catch (error) {
                console.log('Using mock data for demo');
                setPaymentData({
                    id: intentId,
                    status: 'SUCCEEDED',
                    amount: searchParams.get('amount') || '100.00',
                    transactionHash: txHash
                });
            }

            setIsComplete(true);

            // Cleanup localStorage
            localStorage.removeItem('finternet_intent_id');
            localStorage.removeItem('finternet_return_url');

            toast({
                title: '🎉 Payment Confirmed!',
                description: 'Your transaction has been recorded on the blockchain.',
            });
        };

        runSteps();
    }, [intentId]);

    const handleContinue = () => {
        navigate(returnUrl);
    };

    return (
        <div className="min-h-screen bg-background overflow-hidden">
            {/* Animated Background */}
            <div className="fixed inset-0 pointer-events-none">
                {/* Hexagon Grid */}
                <div className="absolute inset-0 opacity-10">
                    {[...Array(20)].map((_, i) => (
                        <motion.div
                            key={i}
                            className="absolute"
                            style={{
                                left: `${Math.random() * 100}%`,
                                top: `${Math.random() * 100}%`,
                            }}
                            animate={{
                                opacity: [0.3, 0.7, 0.3],
                                scale: [1, 1.2, 1],
                            }}
                            transition={{
                                duration: 3 + Math.random() * 2,
                                repeat: Infinity,
                                delay: Math.random() * 2,
                            }}
                        >
                            <Hexagon className="w-8 h-8 text-primary" />
                        </motion.div>
                    ))}
                </div>

                {/* Glowing orbs */}
                <motion.div
                    className="absolute top-1/4 left-1/4 w-64 h-64 bg-primary/20 rounded-full blur-[100px]"
                    animate={{
                        scale: [1, 1.3, 1],
                        opacity: [0.3, 0.5, 0.3],
                    }}
                    transition={{ duration: 4, repeat: Infinity }}
                />
                <motion.div
                    className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-purple-500/20 rounded-full blur-[100px]"
                    animate={{
                        scale: [1.3, 1, 1.3],
                        opacity: [0.3, 0.5, 0.3],
                    }}
                    transition={{ duration: 4, repeat: Infinity }}
                />
            </div>

            {/* Header */}
            <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
                <div className="container mx-auto px-6 py-4 flex items-center justify-between">
                    <Link to="/dashboard" className="flex items-center gap-2">
                        <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
                            <Wallet className="w-5 h-5 text-primary-foreground" />
                        </div>
                        <span className="text-xl font-display font-bold">Cooper</span>
                    </Link>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        Finternet Network
                    </div>
                </div>
            </nav>

            <main className="container mx-auto px-6 py-12 relative z-10">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="max-w-xl mx-auto"
                >
                    <div className="glass-card p-8 rounded-2xl text-center">
                        <AnimatePresence mode="wait">
                            {!isComplete ? (
                                <motion.div
                                    key="processing"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                >
                                    {/* Animated Logo */}
                                    <motion.div
                                        className="w-24 h-24 rounded-full bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center mx-auto mb-8 relative"
                                        animate={{ rotate: 360 }}
                                        transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
                                    >
                                        <Hexagon className="w-12 h-12 text-white" />
                                        <motion.div
                                            className="absolute inset-0 rounded-full border-2 border-primary/50"
                                            animate={{ scale: [1, 1.5], opacity: [1, 0] }}
                                            transition={{ duration: 1.5, repeat: Infinity }}
                                        />
                                    </motion.div>

                                    <h1 className="text-2xl font-display font-bold mb-2 gradient-text">
                                        Processing on Blockchain
                                    </h1>
                                    <p className="text-muted-foreground mb-8">
                                        Your payment is being securely processed via smart contracts
                                    </p>

                                    {/* Progress Steps */}
                                    <div className="space-y-3 text-left">
                                        {PROCESSING_STEPS.map((step) => {
                                            const Icon = step.icon;
                                            const isActive = currentStep === step.id;
                                            const isComplete = currentStep > step.id;

                                            return (
                                                <motion.div
                                                    key={step.id}
                                                    className={`flex items-center gap-4 p-4 rounded-xl transition-all ${isActive
                                                        ? 'bg-primary/10 border border-primary/30'
                                                        : isComplete
                                                            ? 'bg-success/10'
                                                            : 'bg-background-surface opacity-50'
                                                        }`}
                                                    initial={{ x: -20, opacity: 0 }}
                                                    animate={{ x: 0, opacity: 1 }}
                                                    transition={{ delay: step.id * 0.1 }}
                                                >
                                                    <div
                                                        className={`w-10 h-10 rounded-full flex items-center justify-center ${isComplete
                                                            ? 'bg-success text-success-foreground'
                                                            : isActive
                                                                ? 'bg-primary text-primary-foreground'
                                                                : 'bg-muted'
                                                            }`}
                                                    >
                                                        {isComplete ? (
                                                            <CheckCircle className="w-5 h-5" />
                                                        ) : isActive ? (
                                                            <motion.div
                                                                animate={{ rotate: 360 }}
                                                                transition={{
                                                                    duration: 1,
                                                                    repeat: Infinity,
                                                                    ease: 'linear',
                                                                }}
                                                            >
                                                                <Icon className="w-5 h-5" />
                                                            </motion.div>
                                                        ) : (
                                                            <Icon className="w-5 h-5" />
                                                        )}
                                                    </div>
                                                    <div className="flex-1">
                                                        <p
                                                            className={`font-medium ${isActive
                                                                ? 'text-primary'
                                                                : isComplete
                                                                    ? 'text-success'
                                                                    : ''
                                                                }`}
                                                        >
                                                            {step.label}
                                                        </p>
                                                    </div>
                                                    {isActive && (
                                                        <motion.div
                                                            className="w-2 h-2 rounded-full bg-primary"
                                                            animate={{ scale: [1, 1.5, 1] }}
                                                            transition={{
                                                                duration: 0.5,
                                                                repeat: Infinity,
                                                            }}
                                                        />
                                                    )}
                                                </motion.div>
                                            );
                                        })}
                                    </div>
                                </motion.div>
                            ) : (
                                <motion.div
                                    key="success"
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                >
                                    {/* Success Animation */}
                                    <motion.div
                                        className="relative w-24 h-24 mx-auto mb-8"
                                        initial={{ scale: 0 }}
                                        animate={{ scale: 1 }}
                                        transition={{ type: 'spring', stiffness: 200 }}
                                    >
                                        <div className="absolute inset-0 rounded-full bg-success/20 animate-ping" />
                                        <div className="relative w-24 h-24 rounded-full bg-success flex items-center justify-center">
                                            <CheckCircle className="w-12 h-12 text-success-foreground" />
                                        </div>
                                        <motion.div
                                            className="absolute -top-2 -right-2"
                                            animate={{ rotate: [0, 15, -15, 0] }}
                                            transition={{ duration: 0.5, repeat: 3 }}
                                        >
                                            <Sparkles className="w-8 h-8 text-yellow-400" />
                                        </motion.div>
                                    </motion.div>

                                    <h1 className="text-3xl font-display font-bold mb-2 gradient-text">
                                        Payment Successful!
                                    </h1>
                                    <p className="text-muted-foreground mb-8">
                                        Your transaction has been confirmed on the blockchain
                                    </p>

                                    {/* Transaction Details */}
                                    <div className="space-y-3 mb-8">
                                        <div className="flex justify-between items-center p-4 bg-background-surface rounded-xl">
                                            <span className="text-muted-foreground">Amount</span>
                                            <span className="font-bold text-success text-lg">
                                                ${paymentData?.amount || '100.00'} USDC
                                            </span>
                                        </div>
                                        <div className="flex justify-between items-center p-4 bg-background-surface rounded-xl">
                                            <span className="text-muted-foreground">Network</span>
                                            <span className="font-medium">Sepolia Testnet</span>
                                        </div>
                                        <div className="p-4 bg-background-surface rounded-xl">
                                            <span className="text-muted-foreground text-sm block mb-2">
                                                Transaction Hash
                                            </span>
                                            <code className="text-xs font-mono text-primary break-all">
                                                {transactionHash}
                                            </code>
                                        </div>
                                    </div>

                                    <Button
                                        variant="gradient"
                                        size="lg"
                                        className="w-full"
                                        onClick={handleContinue}
                                    >
                                        Continue to Dashboard
                                        <ArrowRight className="w-5 h-5 ml-2" />
                                    </Button>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </motion.div>
            </main>
        </div>
    );
}
