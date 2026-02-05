import { useState, useEffect, useCallback } from 'react';
import { settlementsAPI, UserDebt, DebtRestrictions, ReliabilityScore } from '@/lib/api';

interface UseDebtsReturn {
  debts: UserDebt[];
  restrictions: DebtRestrictions | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  hasRestrictions: boolean;
  totalOutstanding: number;
}

export function useDebts(): UseDebtsReturn {
  const [debts, setDebts] = useState<UserDebt[]>([]);
  const [restrictions, setRestrictions] = useState<DebtRestrictions | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDebts = useCallback(async () => {
    try {
      const response = await settlementsAPI.getMyDebts();
      setDebts(response.data.debts);
      setRestrictions(response.data.restrictions);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to fetch debts');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDebts();
  }, [fetchDebts]);

  const hasRestrictions = restrictions?.has_restrictions ?? false;
  const totalOutstanding = debts.reduce(
    (sum, d) => sum + (d.remaining_amount || d.amount),
    0
  );

  return {
    debts,
    restrictions,
    isLoading,
    error,
    refresh: fetchDebts,
    hasRestrictions,
    totalOutstanding,
  };
}

interface UseReliabilityReturn {
  score: ReliabilityScore | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  tier: string;
  hasRestrictions: boolean;
}

export function useReliability(): UseReliabilityReturn {
  const [score, setScore] = useState<ReliabilityScore | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchScore = useCallback(async () => {
    try {
      const response = await settlementsAPI.getReliabilityScore();
      setScore(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to fetch reliability score');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchScore();
  }, [fetchScore]);

  const tier = score?.tier ?? 'good';
  const hasRestrictions = score?.restrictions?.can_join_events === false ||
    (score?.restrictions?.force_approval ?? false);

  return {
    score,
    isLoading,
    error,
    refresh: fetchScore,
    tier,
    hasRestrictions,
  };
}
