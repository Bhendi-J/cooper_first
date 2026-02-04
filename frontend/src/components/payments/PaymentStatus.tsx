/**
 * PaymentStatus - Display and track payment status
 * 
 * This component:
 * 1. Polls the payment intent status
 * 2. Shows visual status indicators
 * 3. Handles status transitions
 */
import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Loader2, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  AlertCircle,
  RefreshCw,
  ArrowRight
} from 'lucide-react';
import { paymentsAPI, PaymentStatus as PaymentStatusType, GetPaymentIntentResponse } from '@/lib/api';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

interface PaymentStatusProps {
  intentId: string;
  onStatusChange?: (status: PaymentStatusType) => void;
  pollInterval?: number; // in milliseconds
  autoRefresh?: boolean;
}

const STATUS_CONFIG: Record<PaymentStatusType, {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  variant: 'default' | 'secondary' | 'destructive' | 'outline';
  color: string;
}> = {
  INITIATED: {
    label: 'Initiated',
    icon: Clock,
    variant: 'secondary',
    color: 'text-gray-500',
  },
  REQUIRES_SIGNATURE: {
    label: 'Awaiting Signature',
    icon: AlertCircle,
    variant: 'outline',
    color: 'text-yellow-500',
  },
  PROCESSING: {
    label: 'Processing',
    icon: Loader2,
    variant: 'secondary',
    color: 'text-blue-500',
  },
  SUCCEEDED: {
    label: 'Succeeded',
    icon: CheckCircle2,
    variant: 'default',
    color: 'text-green-500',
  },
  SETTLED: {
    label: 'Settled',
    icon: CheckCircle2,
    variant: 'default',
    color: 'text-green-600',
  },
  FINAL: {
    label: 'Complete',
    icon: CheckCircle2,
    variant: 'default',
    color: 'text-green-700',
  },
  CANCELLED: {
    label: 'Cancelled',
    icon: XCircle,
    variant: 'destructive',
    color: 'text-red-500',
  },
  FAILED: {
    label: 'Failed',
    icon: XCircle,
    variant: 'destructive',
    color: 'text-red-600',
  },
};

export function PaymentStatusCard({
  intentId,
  onStatusChange,
  pollInterval = 5000,
  autoRefresh = true,
}: PaymentStatusProps) {
  const [payment, setPayment] = useState<GetPaymentIntentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const fetchStatus = useCallback(async () => {
    try {
      const response = await paymentsAPI.getIntent(intentId);
      setPayment(response.data);
      setError(null);
      setLastUpdated(new Date());

      const status = response.data.intent?.status || response.data.local?.status;
      if (status) {
        onStatusChange?.(status);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch payment status');
    } finally {
      setLoading(false);
    }
  }, [intentId, onStatusChange]);

  useEffect(() => {
    fetchStatus();

    // Only poll if payment is not in a terminal state
    if (autoRefresh) {
      const interval = setInterval(() => {
        const status = payment?.intent?.status || payment?.local?.status;
        const terminalStates: PaymentStatusType[] = ['SUCCEEDED', 'SETTLED', 'FINAL', 'CANCELLED', 'FAILED'];
        
        if (!status || !terminalStates.includes(status)) {
          fetchStatus();
        }
      }, pollInterval);

      return () => clearInterval(interval);
    }
  }, [fetchStatus, pollInterval, autoRefresh, payment]);

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-destructive">
              <XCircle className="h-5 w-5" />
              <span>{error}</span>
            </div>
            <Button variant="outline" size="sm" onClick={fetchStatus}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const intent = payment?.intent;
  const local = payment?.local;
  const status = (intent?.status || local?.status || 'INITIATED') as PaymentStatusType;
  const config = STATUS_CONFIG[status];
  const StatusIcon = config.icon;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Payment Status</CardTitle>
          <Badge variant={config.variant}>
            <StatusIcon className={`h-3 w-3 mr-1 ${status === 'PROCESSING' ? 'animate-spin' : ''}`} />
            {config.label}
          </Badge>
        </div>
        <CardDescription>
          ID: {intentId}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Amount */}
        <div className="flex justify-between items-center">
          <span className="text-muted-foreground">Amount</span>
          <span className="font-semibold">
            {intent?.amount || local?.amount} {intent?.currency || local?.currency}
          </span>
        </div>

        {/* Status Timeline */}
        <div className="flex items-center gap-2 text-sm">
          <Clock className="h-4 w-4 text-muted-foreground" />
          <span className="text-muted-foreground">
            Last updated {dayjs(lastUpdated).fromNow()}
          </span>
          <Button variant="ghost" size="sm" onClick={fetchStatus} className="ml-auto">
            <RefreshCw className="h-3 w-3" />
          </Button>
        </div>

        {/* Transaction Hash */}
        {(intent?.data?.transactionHash || local?.transaction_hash) && (
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">Transaction</span>
            <code className="text-xs bg-muted px-2 py-1 rounded">
              {(intent?.data?.transactionHash || local?.transaction_hash)?.slice(0, 10)}...
            </code>
          </div>
        )}

        {/* Payment URL for pending */}
        {intent?.data?.paymentUrl && status === 'INITIATED' && (
          <Button 
            variant="outline" 
            className="w-full"
            onClick={() => window.open(intent.data?.paymentUrl, '_blank')}
          >
            Complete Payment
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

export default PaymentStatusCard;
