import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { WellnessCard } from '@/components/WellnessCard';
import { ReceiptScanner } from '@/components/ReceiptScanner';
import { 
  Wallet, 
  ArrowLeft, 
  Heart,
  Receipt,
  ChevronRight,
} from 'lucide-react';

export default function Wellness() {
  const [showScanner, setShowScanner] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      {/* Top Navigation */}
      <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/dashboard">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Heart className="w-5 h-5 text-pink-500" />
              <span className="text-xl font-display font-bold">Financial Wellness</span>
            </div>
          </div>
          <Link to="/wallet">
            <Button variant="outline" size="sm">
              <Wallet className="w-4 h-4 mr-2" />
              My Wallet
            </Button>
          </Link>
        </div>
      </nav>

      <main className="container mx-auto px-6 py-8 max-w-4xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-display font-bold mb-2">
              Your Financial <span className="gradient-text">Wellness</span>
            </h1>
            <p className="text-muted-foreground">
              A supportive companion for your financial journey. Private to you. 💙
            </p>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <button
              onClick={() => setShowScanner(!showScanner)}
              className="glass-card p-6 rounded-xl hover:ring-2 ring-primary/50 transition-all text-left group"
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                  <Receipt className="w-6 h-6 text-blue-500" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold group-hover:text-primary transition-colors">
                    Scan Receipt
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Upload a receipt to auto-fill expense details
                  </p>
                </div>
                <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-primary" />
              </div>
            </button>

            <Link to="/wallet" className="glass-card p-6 rounded-xl hover:ring-2 ring-primary/50 transition-all group">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                  <Wallet className="w-6 h-6 text-green-500" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold group-hover:text-primary transition-colors">
                    View Wallet
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Check balance and transactions
                  </p>
                </div>
                <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-primary" />
              </div>
            </Link>
          </div>

          {/* Receipt Scanner (collapsible) */}
          {showScanner && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
            >
              <ReceiptScanner 
                onScanComplete={(result) => {
                  console.log('Receipt scanned:', result);
                  setShowScanner(false);
                  // Could navigate to expense add with pre-filled data
                }}
                onCancel={() => setShowScanner(false)}
              />
            </motion.div>
          )}

          {/* Wellness Card */}
          <WellnessCard />

          {/* Privacy Note */}
          <div className="text-center text-sm text-muted-foreground bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
            <p>
              🔒 This information is private to you and never shared with others or used to restrict your access.
            </p>
          </div>
        </motion.div>
      </main>
    </div>
  );
}
