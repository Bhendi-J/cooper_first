/**
 * Payment API service for Finternet integration
 */

const API_BASE = 'http://localhost:5000/api/v1/payments';

interface PaymentIntent {
  id: string;
  status: 'INITIATED' | 'PROCESSING' | 'SUCCEEDED' | 'SETTLED' | 'FINAL' | 'CANCELLED';
  paymentUrl?: string;
  amount: string;
  currency: string;
  settlementStatus?: string;
  transactionHash?: string;
  phases?: Array<{ phase: string; status: string }>;
}

interface CreatePaymentIntentRequest {
  amount: string;
  currency?: string;
  description?: string;
}

/**
 * Get auth headers with JWT token
 */
function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    'Authorization': token ? `Bearer ${token}` : '',
  };
}

/**
 * Create a new payment intent
 */
export async function createPaymentIntent(
  request: CreatePaymentIntentRequest
): Promise<PaymentIntent> {
  const response = await fetch(`${API_BASE}/intent`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to create payment intent');
  }

  return response.json();
}

/**
 * Get payment intent status
 */
export async function getPaymentStatus(intentId: string): Promise<PaymentIntent> {
  const response = await fetch(`${API_BASE}/intent/${intentId}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to get payment status');
  }

  return response.json();
}

/**
 * Confirm a payment after user signs transaction
 */
export async function confirmPayment(
  intentId: string,
  signature: string,
  payerAddress: string
): Promise<PaymentIntent> {
  const response = await fetch(`${API_BASE}/intent/${intentId}/confirm`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ signature, payerAddress }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to confirm payment');
  }

  return response.json();
}

/**
 * Cancel a pending payment intent
 */
export async function cancelPayment(intentId: string): Promise<PaymentIntent> {
  const response = await fetch(`${API_BASE}/intent/${intentId}/cancel`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to cancel payment');
  }

  return response.json();
}

/**
 * [DEMO] Simulate a successful payment for hackathon demo
 */
export async function simulatePaymentSuccess(intentId: string): Promise<PaymentIntent> {
  const response = await fetch(`${API_BASE}/mock/simulate-success/${intentId}`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to simulate payment');
  }

  return response.json();
}

/**
 * Calculate split amounts for participants
 */
export async function calculateSplit(
  total: number,
  participants: number,
  weights?: Record<string, number>
): Promise<{
  total: number;
  num_participants: number;
  per_person: number;
  splits: Record<string, number>;
  currency: string;
}> {
  const response = await fetch(`${API_BASE}/split/calculate`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ total, participants, weights }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to calculate split');
  }

  return response.json();
}
