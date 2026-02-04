import { useEffect, useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, CheckCircle, XCircle, Wallet, Shield, ArrowRight } from 'lucide-react';
import { api } from '@/lib/api';

interface PaymentIntent {
  id: string;
  amount: string;
  currency: string;
  status: string;
  description?: string;
  event_id?: string;
  event_name?: string;
  mock?: boolean;
}

export default function PaymentConfirm() {
  const { intentId } = useParams<{ intentId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const [intent, setIntent] = useState<PaymentIntent | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Get redirect URL from query params
  const redirectUrl = searchParams.get('redirect') || '/dashboard';

  useEffect(() => {
    fetchPaymentIntent();
  }, [intentId]);

  const fetchPaymentIntent = async () => {
    if (!intentId) return;
    
    try {
      setLoading(true);
      const response = await api.get(`/payments/intent/${intentId}`);
      setIntent(response.data.data);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to load payment intent');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmPayment = async () => {
    if (!intentId) return;
    
    try {
      setConfirming(true);
      setError(null);
      
      // Simulate wallet signature (for mock mode)
      const mockSignature = `0x${Array(130).fill(0).map(() => Math.floor(Math.random() * 16).toString(16)).join('')}`;
      const mockAddress = `0x${Array(40).fill(0).map(() => Math.floor(Math.random() * 16).toString(16)).join('')}`;
      
      // Confirm the payment
      await api.post(`/payments/intent/${intentId}/confirm`, {
        signature: mockSignature,
        payer_address: mockAddress
      });
      
      // Also confirm the deposit if there's an associated event
      if (intent?.event_id) {
        try {
          await api.post('/payments/deposit/confirm', {
            intent_id: intentId
          });
        } catch (err) {
          // Deposit confirm might fail if already processed - ignore
          console.log('Deposit confirm:', err);
        }
      }
      
      setSuccess(true);
      
      // Redirect after 2 seconds
      setTimeout(() => {
        navigate(redirectUrl);
      }, 2000);
      
    } catch (err: any) {
      setError(err.response?.data?.error || 'Payment confirmation failed');
    } finally {
      setConfirming(false);
    }
  };

  const handleCancelPayment = async () => {
    if (!intentId) return;
    
    try {
      await api.post(`/payments/intent/${intentId}/cancel`);
      navigate(redirectUrl);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to cancel payment');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading payment details...</p>
        </div>
      </div>
    );
  }

  if (error && !intent) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
        <Card className="max-w-md w-full">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <XCircle className="h-6 w-6" />
              Payment Error
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          </CardContent>
          <CardFooter>
            <Button onClick={() => navigate(redirectUrl)} variant="outline" className="w-full">
              Go Back
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 to-emerald-100 p-4">
        <Card className="max-w-md w-full">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 h-16 w-16 rounded-full bg-green-100 flex items-center justify-center">
              <CheckCircle className="h-10 w-10 text-green-600" />
            </div>
            <CardTitle className="text-green-700">Payment Successful!</CardTitle>
            <CardDescription>
              Your payment of {intent?.amount} {intent?.currency} has been confirmed.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center">
            <p className="text-sm text-muted-foreground">
              Redirecting you back...
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <Card className="max-w-md w-full shadow-xl">
        <CardHeader className="text-center border-b">
          <div className="mx-auto mb-4 h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center">
            <Shield className="h-8 w-8 text-primary" />
          </div>
          <CardTitle>Secure Payment</CardTitle>
          <CardDescription>
            Complete your payment using Finternet
          </CardDescription>
          {intent?.mock && (
            <Badge variant="outline" className="mt-2 text-amber-600 border-amber-300">
              Demo Mode
            </Badge>
          )}
        </CardHeader>
        
        <CardContent className="pt-6 space-y-4">
          {/* Payment Amount */}
          <div className="text-center py-4 bg-slate-50 rounded-lg">
            <p className="text-sm text-muted-foreground mb-1">Amount to Pay</p>
            <p className="text-4xl font-bold text-primary">
              {intent?.amount} <span className="text-xl">{intent?.currency}</span>
            </p>
          </div>
          
          {/* Payment Details */}
          {intent?.description && (
            <div className="bg-slate-50 rounded-lg p-3">
              <p className="text-sm text-muted-foreground">Description</p>
              <p className="font-medium">{intent.description}</p>
            </div>
          )}
          
          {intent?.event_name && (
            <div className="bg-slate-50 rounded-lg p-3">
              <p className="text-sm text-muted-foreground">Event</p>
              <p className="font-medium">{intent.event_name}</p>
            </div>
          )}
          
          {/* Payment ID */}
          <div className="text-center">
            <p className="text-xs text-muted-foreground">
              Payment ID: {intent?.id}
            </p>
          </div>
          
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </CardContent>
        
        <CardFooter className="flex flex-col gap-3 border-t pt-6">
          <Button 
            onClick={handleConfirmPayment} 
            disabled={confirming || intent?.status !== 'INITIATED'}
            className="w-full h-12 text-lg"
          >
            {confirming ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Confirming...
              </>
            ) : (
              <>
                <Wallet className="mr-2 h-5 w-5" />
                Confirm Payment
                <ArrowRight className="ml-2 h-5 w-5" />
              </>
            )}
          </Button>
          
          <Button 
            onClick={handleCancelPayment}
            variant="ghost"
            className="w-full"
            disabled={confirming}
          >
            Cancel
          </Button>
          
          <p className="text-xs text-center text-muted-foreground mt-2">
            🔒 Secured by Finternet Payment Gateway
          </p>
        </CardFooter>
      </Card>
    </div>
  );
}
