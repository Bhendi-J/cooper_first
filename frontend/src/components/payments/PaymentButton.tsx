/**
 * PaymentButton - Initiates Finternet payment flow
 * 
 * This component handles:
 * 1. Creating a payment intent via backend API
 * 2. Redirecting to Finternet payment page for wallet signature
 * 3. Handling the return and confirming the payment
 */
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Loader2, CreditCard, ExternalLink } from 'lucide-react';
import { paymentsAPI, CreatePaymentIntentData, PaymentType } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

interface PaymentButtonProps {
  amount: string;
  currency?: string;
  description?: string;
  eventId?: string;
  expenseId?: string;
  paymentType?: PaymentType;
  onSuccess?: (intentId: string, paymentUrl: string) => void;
  onError?: (error: string) => void;
  className?: string;
  children?: React.ReactNode;
}

export function PaymentButton({
  amount,
  currency = 'USDC',
  description,
  eventId,
  expenseId,
  paymentType = 'CONDITIONAL',
  onSuccess,
  onError,
  className,
  children,
}: PaymentButtonProps) {
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const handlePayment = async () => {
    setLoading(true);
    try {
      const data: CreatePaymentIntentData = {
        amount,
        currency,
        description,
        event_id: eventId,
        expense_id: expenseId,
        type: paymentType,
        settlement_method: 'OFF_RAMP_MOCK', // Use mock for testing
      };

      const response = await paymentsAPI.createIntent(data);
      const { intent, payment_url, local_id } = response.data;

      toast({
        title: 'Payment Initiated',
        description: 'Redirecting to payment page...',
      });

      onSuccess?.(local_id, payment_url);

      // Open Finternet payment page in new tab
      if (payment_url) {
        window.open(payment_url, '_blank', 'noopener,noreferrer');
      }
    } catch (error: unknown) {
      const errorMessage = 
        error instanceof Error 
          ? error.message 
          : 'Failed to create payment intent';
      
      toast({
        title: 'Payment Error',
        description: errorMessage,
        variant: 'destructive',
      });

      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button 
      onClick={handlePayment} 
      disabled={loading}
      className={className}
    >
      {loading ? (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Creating Payment...
        </>
      ) : (
        children ?? (
          <>
            <CreditCard className="mr-2 h-4 w-4" />
            Pay {amount} {currency}
            <ExternalLink className="ml-2 h-3 w-3" />
          </>
        )
      )}
    </Button>
  );
}

export default PaymentButton;
