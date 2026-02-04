import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Wallet, Mail, Lock, User, ArrowRight, Loader2, CheckCircle2 } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { authAPI } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

const benefits = [
  'Create unlimited shared wallets',
  'Real-time expense tracking',
  'Automatic settlements',
  'Secure personal deposits',
];

export default function Signup() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await authAPI.register({ name, email, password });
      const { access_token, user } = response.data;
      // Map backend user format to frontend format
      login(
        { id: user._id, name: user.name, email: user.email },
        access_token
      );
      toast({
        title: 'Account created!',
        description: 'Welcome to Cooper. Let\'s create your first event.',
      });
      navigate('/dashboard');
    } catch (error: any) {
      toast({
        title: 'Signup failed',
        description: error.response?.data?.error || 'Something went wrong',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Demo signup for testing without backend
  const handleDemoSignup = () => {
    login(
      { id: 'demo-user', name: name || 'Demo User', email: email || 'demo@cooper.app' },
      'demo-token'
    );
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* Left Side - Visual */}
      <div className="hidden lg:flex flex-1 bg-background-secondary relative items-center justify-center p-12">
        <div className="absolute inset-0 bg-dots opacity-20" />
        <div className="absolute bottom-1/3 right-1/3 w-80 h-80 bg-primary/20 rounded-full blur-[120px]" />
        <div className="absolute top-1/3 left-1/3 w-80 h-80 bg-secondary/20 rounded-full blur-[120px]" />
        
        <motion.div
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="relative z-10 max-w-lg"
        >
          <h2 className="text-4xl font-display font-bold mb-6">
            Join thousands managing{' '}
            <span className="gradient-text">group expenses</span>
          </h2>
          
          <ul className="space-y-4">
            {benefits.map((benefit, index) => (
              <motion.li
                key={benefit}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: 0.4 + index * 0.1 }}
                className="flex items-center gap-3"
              >
                <div className="w-6 h-6 rounded-full gradient-primary flex items-center justify-center">
                  <CheckCircle2 className="w-4 h-4 text-primary-foreground" />
                </div>
                <span className="text-lg">{benefit}</span>
              </motion.li>
            ))}
          </ul>
          
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.8 }}
            className="mt-10 glass-card p-6 rounded-xl"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-lg font-bold text-primary-foreground">
                P
              </div>
              <div>
                <p className="font-medium">"Cooper saved us hours of calculations"</p>
                <p className="text-sm text-muted-foreground">Priya S., Group Trip Organizer</p>
              </div>
            </div>
          </motion.div>
        </motion.div>
      </div>

      {/* Right Side - Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md"
        >
          <Link to="/" className="flex items-center gap-2 mb-8">
            <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
              <Wallet className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-display font-bold">Cooper</span>
          </Link>

          <h1 className="text-3xl font-display font-bold mb-2">Create your account</h1>
          <p className="text-muted-foreground mb-8">
            Get started for free. No credit card required.
          </p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="name">Full Name</Label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <Input
                  id="name"
                  type="text"
                  placeholder="John Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="pl-11 h-12 bg-background-surface border-border focus:border-primary input-glow"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-11 h-12 bg-background-surface border-border focus:border-primary input-glow"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-11 h-12 bg-background-surface border-border focus:border-primary input-glow"
                  required
                  minLength={8}
                />
              </div>
              <p className="text-xs text-muted-foreground">Minimum 8 characters</p>
            </div>

            <Button type="submit" variant="gradient" size="lg" className="w-full" disabled={isLoading}>
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  Create Account
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </Button>
          </form>

          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">Or</span>
              </div>
            </div>

            <Button
              type="button"
              variant="outline"
              size="lg"
              className="w-full mt-6"
              onClick={handleDemoSignup}
            >
              Try Demo (No Backend Required)
            </Button>
          </div>

          <p className="text-center text-xs text-muted-foreground mt-6">
            By signing up, you agree to our{' '}
            <Link to="/terms" className="text-primary hover:underline">Terms of Service</Link>
            {' '}and{' '}
            <Link to="/privacy" className="text-primary hover:underline">Privacy Policy</Link>
          </p>

          <p className="text-center text-sm text-muted-foreground mt-6">
            Already have an account?{' '}
            <Link to="/login" className="text-primary hover:underline font-medium">
              Log in
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
