import { useEffect, useState, createContext, useContext, ReactNode, useRef } from 'react';
import { wellnessApi, WellnessSummary, WellnessReminder } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { AlertCircle, Heart, X, ExternalLink } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

interface DebtNotificationContextType {
  checkDebts: () => Promise<void>;
  dismissDebtNotification: () => void;
  pendingAmount: number;
  hasChecked: boolean;
}

const DebtNotificationContext = createContext<DebtNotificationContextType | null>(null);

export function useDebtNotification() {
  const context = useContext(DebtNotificationContext);
  if (!context) {
    // Return a dummy context instead of throwing - this allows use on public pages
    return {
      checkDebts: async () => {},
      dismissDebtNotification: () => {},
      pendingAmount: 0,
      hasChecked: false,
    };
  }
  return context;
}

interface DebtNotificationProviderProps {
  children: ReactNode;
}

export function DebtNotificationProvider({ children }: DebtNotificationProviderProps) {
  const { toast } = useToast();
  const location = useLocation();
  const [showDebtModal, setShowDebtModal] = useState(false);
  const [pendingAmount, setPendingAmount] = useState(0);
  const [pendingCount, setPendingCount] = useState(0);
  const [reminders, setReminders] = useState<WellnessReminder[]>([]);
  const [hasChecked, setHasChecked] = useState(false);
  const [wellnessSummary, setWellnessSummary] = useState<WellnessSummary | null>(null);
  const checkedRef = useRef(false);

  // Only check debts on authenticated pages (dashboard, events, etc.)
  // Skip on landing, login, signup
  const publicPaths = ['/', '/login', '/signup'];
  const isPublicPage = publicPaths.includes(location.pathname);

  useEffect(() => {
    // Skip on public pages or if already checked
    if (isPublicPage || checkedRef.current) return;
    
    const token = localStorage.getItem('token');
    if (!token) return; // Not logged in
    
    const sessionKey = 'debtNotificationShown';
    const alreadyShown = sessionStorage.getItem(sessionKey);
    
    if (!alreadyShown) {
      checkedRef.current = true;
      checkDebts();
    }
  }, [location.pathname, isPublicPage]);

  const checkDebts = async () => {
    try {
      const [summaryRes, remindersRes] = await Promise.all([
        wellnessApi.getSummary(),
        wellnessApi.getReminders(),
      ]);

      const summary = summaryRes.data.summary;
      setWellnessSummary(summary);
      setReminders(remindersRes.data.reminders || []);
      setHasChecked(true);

      const pending = summary?.pending_summary?.total_pending || 0;
      const count = summary?.pending_summary?.pending_count || 0;
      
      setPendingAmount(pending);
      setPendingCount(count);

      // Show modal if user has pending debts > 100 (gentle threshold)
      if (pending > 100 && count > 0) {
        const sessionKey = 'debtNotificationShown';
        const alreadyShown = sessionStorage.getItem(sessionKey);
        
        if (!alreadyShown) {
          // Wait a bit so it doesn't feel intrusive
          setTimeout(() => {
            setShowDebtModal(true);
            sessionStorage.setItem(sessionKey, 'true');
          }, 2000);
        }
      }
    } catch (error) {
      console.error('Failed to check debts:', error);
    }
  };

  const dismissDebtNotification = () => {
    setShowDebtModal(false);
  };

  const handleDismissReminder = async (reminder: WellnessReminder) => {
    try {
      await wellnessApi.dismissReminder(reminder.type, reminder.event_id);
      setReminders(prev => prev.filter(r => 
        !(r.type === reminder.type && r.event_id === reminder.event_id)
      ));
    } catch (error) {
      console.error('Failed to dismiss reminder:', error);
    }
  };

  return (
    <DebtNotificationContext.Provider
      value={{
        checkDebts,
        dismissDebtNotification,
        pendingAmount,
        hasChecked,
      }}
    >
      {children}

      {/* Friendly Debt Reminder Modal */}
      <Dialog open={showDebtModal} onOpenChange={setShowDebtModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <Heart className="w-6 h-6 text-blue-500" />
              </div>
              <DialogTitle className="text-xl">Hey there! 👋</DialogTitle>
            </div>
            <DialogDescription className="text-left space-y-3">
              <p>
                Just a friendly heads up - you have{' '}
                <span className="font-semibold text-foreground">
                  ₹{pendingAmount.toLocaleString()}
                </span>{' '}
                in pending settlements across {pendingCount} {pendingCount === 1 ? 'event' : 'events'}.
              </p>
              <p className="text-sm">
                No rush at all! Settle up whenever it's convenient for you. 
                Your friends will appreciate it. 💙
              </p>
            </DialogDescription>
          </DialogHeader>

          {/* Wellness Status */}
          {wellnessSummary && (
            <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950/20 dark:to-purple-950/20 rounded-lg p-4 my-4">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{wellnessSummary.wellness_status.emoji}</span>
                <div>
                  <p className="font-medium">{wellnessSummary.wellness_status.label}</p>
                  <p className="text-xs text-muted-foreground">
                    {wellnessSummary.wellness_status.description}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Settlement Reminders */}
          {reminders.length > 0 && (
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {reminders.slice(0, 3).map((reminder, index) => (
                <div
                  key={index}
                  className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-sm"
                >
                  <span>{reminder.icon}</span>
                  <div className="flex-1">
                    <p className="font-medium">{reminder.title}</p>
                    <p className="text-xs text-muted-foreground">{reminder.message}</p>
                  </div>
                  {reminder.dismissible && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={() => handleDismissReminder(reminder)}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}

          <DialogFooter className="flex-col sm:flex-row gap-2 mt-4">
            <Button variant="outline" onClick={dismissDebtNotification} className="flex-1">
              Remind me later
            </Button>
            <Link to="/dashboard" className="flex-1">
              <Button className="w-full" onClick={dismissDebtNotification}>
                <ExternalLink className="w-4 h-4 mr-2" />
                View Events
              </Button>
            </Link>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </DebtNotificationContext.Provider>
  );
}

export default DebtNotificationProvider;
