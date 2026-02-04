/**
 * PendingPayments - List of payments the user needs to complete
 */
import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  Wallet, 
  ArrowRight, 
  Calendar,
  DollarSign
} from 'lucide-react';
import { paymentsAPI, PendingPayment } from '@/lib/api';
import { PaymentButton } from './PaymentButton';
import dayjs from 'dayjs';

interface PendingPaymentsProps {
  limit?: number;
  showHeader?: boolean;
  onPaymentInitiated?: (expenseId: string, intentId: string) => void;
}

export function PendingPayments({
  limit = 10,
  showHeader = true,
  onPaymentInitiated,
}: PendingPaymentsProps) {
  const [payments, setPayments] = useState<PendingPayment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPending();
  }, []);

  const fetchPending = async () => {
    try {
      setLoading(true);
      const response = await paymentsAPI.getPending();
      setPayments(response.data.pending_payments.slice(0, limit));
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch pending payments');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card>
        {showHeader && (
          <CardHeader>
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-4 w-60 mt-2" />
          </CardHeader>
        )}
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center justify-between">
              <Skeleton className="h-12 w-48" />
              <Skeleton className="h-10 w-24" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-6 text-center text-destructive">
          {error}
        </CardContent>
      </Card>
    );
  }

  if (payments.length === 0) {
    return (
      <Card>
        {showHeader && (
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wallet className="h-5 w-5" />
              Pending Payments
            </CardTitle>
          </CardHeader>
        )}
        <CardContent className="py-8 text-center text-muted-foreground">
          <DollarSign className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>No pending payments</p>
          <p className="text-sm mt-1">All your expenses are settled!</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      {showHeader && (
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wallet className="h-5 w-5" />
            Pending Payments
          </CardTitle>
          <CardDescription>
            {payments.length} payment{payments.length !== 1 ? 's' : ''} awaiting completion
          </CardDescription>
        </CardHeader>
      )}
      <CardContent className="space-y-4">
        {payments.map((payment) => (
          <div
            key={payment._id}
            className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
          >
            <div className="space-y-1">
              <div className="font-medium">
                {payment.expense_description || 'Expense'}
              </div>
              <div className="text-sm text-muted-foreground flex items-center gap-2">
                <span>{payment.event_name}</span>
                {payment.expense_amount && (
                  <>
                    <span>•</span>
                    <span>Total: ${payment.expense_amount.toFixed(2)}</span>
                  </>
                )}
              </div>
              <Badge variant="outline" className="text-xs">
                Your share: ${payment.amount.toFixed(2)}
              </Badge>
            </div>
            
            <PaymentButton
              amount={payment.amount.toFixed(2)}
              description={payment.expense_description}
              expenseId={payment.expense_id}
              onSuccess={(intentId) => {
                onPaymentInitiated?.(payment.expense_id, intentId);
              }}
            />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default PendingPayments;
