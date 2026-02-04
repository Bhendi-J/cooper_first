/**
 * PaymentHistory - Display user's payment history
 */
import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  History, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Loader2,
  ArrowUpRight
} from 'lucide-react';
import { paymentsAPI, LocalPaymentRecord, PaymentStatus } from '@/lib/api';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

interface PaymentHistoryProps {
  limit?: number;
  showHeader?: boolean;
}

const STATUS_ICON: Record<PaymentStatus, React.ComponentType<{ className?: string }>> = {
  INITIATED: Clock,
  REQUIRES_SIGNATURE: Clock,
  PROCESSING: Loader2,
  SUCCEEDED: CheckCircle2,
  SETTLED: CheckCircle2,
  FINAL: CheckCircle2,
  CANCELLED: XCircle,
  FAILED: XCircle,
};

const STATUS_COLOR: Record<PaymentStatus, string> = {
  INITIATED: 'bg-gray-100 text-gray-700',
  REQUIRES_SIGNATURE: 'bg-yellow-100 text-yellow-700',
  PROCESSING: 'bg-blue-100 text-blue-700',
  SUCCEEDED: 'bg-green-100 text-green-700',
  SETTLED: 'bg-green-100 text-green-700',
  FINAL: 'bg-green-100 text-green-700',
  CANCELLED: 'bg-red-100 text-red-700',
  FAILED: 'bg-red-100 text-red-700',
};

export function PaymentHistory({
  limit = 10,
  showHeader = true,
}: PaymentHistoryProps) {
  const [payments, setPayments] = useState<LocalPaymentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHistory();
  }, [limit]);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const response = await paymentsAPI.getHistory(limit);
      setPayments(response.data.payments);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch payment history');
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
          </CardHeader>
        )}
        <CardContent className="space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex items-center justify-between py-2">
              <div className="space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-24" />
              </div>
              <Skeleton className="h-6 w-20" />
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
              <History className="h-5 w-5" />
              Payment History
            </CardTitle>
          </CardHeader>
        )}
        <CardContent className="py-8 text-center text-muted-foreground">
          <History className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>No payment history yet</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      {showHeader && (
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Payment History
          </CardTitle>
          <CardDescription>
            Your recent payment transactions
          </CardDescription>
        </CardHeader>
      )}
      <CardContent>
        <div className="space-y-4">
          {payments.map((payment) => {
            const StatusIcon = STATUS_ICON[payment.status] || Clock;
            const statusColor = STATUS_COLOR[payment.status] || 'bg-gray-100 text-gray-700';
            
            return (
              <div
                key={payment._id}
                className="flex items-center justify-between py-3 border-b last:border-0"
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-full ${statusColor}`}>
                    <StatusIcon className={`h-4 w-4 ${payment.status === 'PROCESSING' ? 'animate-spin' : ''}`} />
                  </div>
                  <div>
                    <div className="font-medium">
                      {payment.amount} {payment.currency}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {dayjs(payment.created_at).fromNow()}
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className={statusColor}>
                    {payment.status}
                  </Badge>
                  {payment.transaction_hash && (
                    <a
                      href={`https://explorer.finternetlab.io/tx/${payment.transaction_hash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-muted-foreground hover:text-foreground transition-colors"
                      title="View on explorer"
                    >
                      <ArrowUpRight className="h-4 w-4" />
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

export default PaymentHistory;
