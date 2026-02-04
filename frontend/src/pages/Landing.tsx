import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { 
  Wallet, 
  Users, 
  Shield, 
  TrendingUp, 
  Zap, 
  CheckCircle2,
  ArrowRight,
  Sparkles,
  Lock,
  PieChart
} from 'lucide-react';

const features = [
  {
    icon: Wallet,
    title: 'Shared Wallets',
    description: 'Pool money with your group. Everyone contributes, everyone benefits from transparent tracking.',
  },
  {
    icon: Shield,
    title: 'Rule-Based Spending',
    description: 'Set custom spending rules. Automatic enforcement ensures fair usage for all participants.',
  },
  {
    icon: TrendingUp,
    title: 'Real-Time Tracking',
    description: 'Watch expenses update instantly. Every transaction is visible to all group members.',
  },
  {
    icon: Zap,
    title: 'Auto Settlement',
    description: 'No more awkward conversations. Automatic calculations and instant settlements when events end.',
  },
  {
    icon: Lock,
    title: 'Secure Deposits',
    description: 'Personal security wallets protect your funds. Top up shared wallets only when needed.',
  },
  {
    icon: PieChart,
    title: 'Smart Analytics',
    description: 'Understand your spending patterns with AI-powered insights and categorical breakdowns.',
  },
];

const steps = [
  {
    number: '01',
    title: 'Create Your Event',
    description: 'Set up a trip, party, or group activity. Define the budget and invite friends.',
  },
  {
    number: '02',
    title: 'Pool Your Funds',
    description: 'Everyone deposits into the shared wallet. Track contributions in real-time.',
  },
  {
    number: '03',
    title: 'Spend Together',
    description: 'Make expenses from the shared pool. Split equally or customize per person.',
  },
  {
    number: '04',
    title: 'Settle Instantly',
    description: 'When the event ends, automatic settlements refund remaining balances.',
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-background overflow-hidden">
      {/* Navigation */}
      <motion.nav 
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border"
      >
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
              <Wallet className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-display font-bold">Cooper</span>
          </Link>
          
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-muted-foreground hover:text-foreground transition-colors">Features</a>
            <a href="#how-it-works" className="text-muted-foreground hover:text-foreground transition-colors">How it Works</a>
          </div>
          
          <div className="flex items-center gap-3">
            <Link to="/login">
              <Button variant="ghost" size="sm">Log in</Button>
            </Link>
            <Link to="/signup">
              <Button variant="gradient" size="sm">Get Started</Button>
            </Link>
          </div>
        </div>
      </motion.nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 md:pt-40 md:pb-32">
        {/* Background Effects */}
        <div className="absolute inset-0 bg-grid opacity-30" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-secondary/20 rounded-full blur-[120px]" />
        
        <div className="container mx-auto px-6 relative z-10">
          <div className="max-w-4xl mx-auto text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-card border border-border mb-8"
            >
              <Sparkles className="w-4 h-4 text-primary" />
              <span className="text-sm text-muted-foreground">Introducing Rule-Based Shared Wallets</span>
            </motion.div>
            
            <motion.h1
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="text-4xl md:text-6xl lg:text-7xl font-display font-bold leading-tight mb-6"
            >
              Split expenses,{' '}
              <span className="gradient-text">not friendships</span>
            </motion.h1>
            
            <motion.p
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10"
            >
              Create shared wallets for trips, events, and group activities. 
              Set rules, track spending in real-time, and settle automatically. 
              No more spreadsheets, no more awkward money talks.
            </motion.p>
            
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="flex flex-col sm:flex-row items-center justify-center gap-4"
            >
              <Link to="/signup">
                <Button variant="gradient" size="xl" className="group">
                  Start for Free
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Button>
              </Link>
              <Link to="#how-it-works">
                <Button variant="outline" size="xl">
                  See How It Works
                </Button>
              </Link>
            </motion.div>
          </div>
          
          {/* Hero Visual */}
          <motion.div
            initial={{ opacity: 0, y: 60 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="mt-16 md:mt-24 max-w-5xl mx-auto"
          >
            <div className="glass-card-glow p-6 md:p-8 rounded-2xl">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Wallet Card */}
                <div className="glass-card p-6 rounded-xl hover-lift">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 rounded-xl gradient-primary flex items-center justify-center">
                      <Wallet className="w-6 h-6 text-primary-foreground" />
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Shared Wallet</p>
                      <p className="text-2xl font-bold">₹24,500</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-success">
                    <TrendingUp className="w-4 h-4" />
                    <span>Active • 4 members</span>
                  </div>
                </div>
                
                {/* Recent Activity */}
                <div className="glass-card p-6 rounded-xl hover-lift">
                  <p className="text-sm text-muted-foreground mb-4">Recent Activity</p>
                  <div className="space-y-3">
                    {[
                      { name: 'Dinner at Olive', amount: '-₹2,400', type: 'expense' },
                      { name: 'Rahul deposited', amount: '+₹5,000', type: 'deposit' },
                      { name: 'Hotel booking', amount: '-₹8,000', type: 'expense' },
                    ].map((item, i) => (
                      <div key={i} className="flex items-center justify-between">
                        <span className="text-sm">{item.name}</span>
                        <span className={`text-sm font-medium ${item.type === 'deposit' ? 'text-success' : 'text-destructive'}`}>
                          {item.amount}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
                
                {/* Your Balance */}
                <div className="glass-card p-6 rounded-xl hover-lift">
                  <p className="text-sm text-muted-foreground mb-2">Your Balance</p>
                  <p className="text-3xl font-bold mb-4">₹6,125</p>
                  <div className="w-full h-2 bg-background rounded-full overflow-hidden">
                    <div className="h-full gradient-primary rounded-full" style={{ width: '65%' }} />
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">65% of your share remaining</p>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 md:py-32 bg-background-secondary relative">
        <div className="absolute inset-0 bg-dots opacity-30" />
        
        <div className="container mx-auto px-6 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl md:text-5xl font-display font-bold mb-4">
              Everything you need to{' '}
              <span className="gradient-text">manage group money</span>
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Built for modern groups who want transparency, fairness, and simplicity in shared finances.
            </p>
          </motion.div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="glass-card p-8 rounded-xl hover-lift group"
              >
                <div className="w-14 h-14 rounded-xl gradient-primary-subtle flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <feature.icon className="w-7 h-7 text-primary" />
                </div>
                <h3 className="text-xl font-display font-semibold mb-3">{feature.title}</h3>
                <p className="text-muted-foreground">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-20 md:py-32 relative">
        <div className="absolute top-1/2 left-0 w-96 h-96 bg-primary/10 rounded-full blur-[150px]" />
        
        <div className="container mx-auto px-6 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl md:text-5xl font-display font-bold mb-4">
              How it <span className="gradient-text">works</span>
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              From event creation to final settlement, everything is seamless and automatic.
            </p>
          </motion.div>
          
          <div className="max-w-4xl mx-auto">
            <div className="relative">
              {/* Connecting Line */}
              <div className="absolute left-8 top-0 bottom-0 w-px bg-gradient-to-b from-primary via-secondary to-primary hidden md:block" />
              
              <div className="space-y-12">
                {steps.map((step, index) => (
                  <motion.div
                    key={step.number}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: index * 0.15 }}
                    className="flex gap-8 items-start"
                  >
                    <div className="relative">
                      <div className="w-16 h-16 rounded-2xl gradient-primary flex items-center justify-center font-display font-bold text-xl text-primary-foreground shadow-lg shadow-primary/30">
                        {step.number}
                      </div>
                    </div>
                    <div className="flex-1 pt-2">
                      <h3 className="text-2xl font-display font-semibold mb-2">{step.title}</h3>
                      <p className="text-muted-foreground text-lg">{step.description}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 md:py-32 relative">
        <div className="container mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="glass-card-glow p-12 md:p-16 rounded-3xl text-center relative overflow-hidden"
          >
            <div className="absolute inset-0 gradient-primary opacity-5" />
            
            <div className="relative z-10">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 mb-6">
                <CheckCircle2 className="w-4 h-4 text-primary" />
                <span className="text-sm text-primary">Free to get started</span>
              </div>
              
              <h2 className="text-3xl md:text-5xl font-display font-bold mb-6">
                Ready to simplify{' '}
                <span className="gradient-text">group expenses?</span>
              </h2>
              
              <p className="text-lg text-muted-foreground max-w-xl mx-auto mb-8">
                Join thousands of groups who trust Cooper for transparent, 
                hassle-free expense sharing.
              </p>
              
              <Link to="/signup">
                <Button variant="gradient" size="xl" className="group">
                  Create Your First Event
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Button>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center">
                <Wallet className="w-4 h-4 text-primary-foreground" />
              </div>
              <span className="font-display font-bold">Cooper</span>
            </div>
            
            <p className="text-sm text-muted-foreground">
              © 2024 Cooper. Built for Finternet Hackathon.
            </p>
            
            <div className="flex items-center gap-6">
              <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Privacy</a>
              <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Terms</a>
              <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Contact</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
