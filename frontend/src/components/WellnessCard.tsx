import { useEffect, useState } from 'react';
import { wellnessApi, WellnessSummary, WellnessReminder } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { X, TrendingUp, Heart, Sparkles } from 'lucide-react';

interface WellnessCardProps {
  compact?: boolean;
}

export function WellnessCard({ compact = false }: WellnessCardProps) {
  const [summary, setSummary] = useState<WellnessSummary | null>(null);
  const [reminders, setReminders] = useState<WellnessReminder[]>([]);
  const [loading, setLoading] = useState(true);
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadWellnessData();
  }, []);

  const loadWellnessData = async () => {
    try {
      const [summaryRes, remindersRes] = await Promise.all([
        wellnessApi.getSummary(),
        wellnessApi.getReminders(),
      ]);
      setSummary(summaryRes.data.summary);
      setReminders(remindersRes.data.reminders || []);
    } catch (error) {
      console.error('Failed to load wellness data:', error);
    } finally {
      setLoading(false);
    }
  };

  const dismissReminder = async (reminder: WellnessReminder) => {
    try {
      await wellnessApi.dismissReminder(reminder.type, reminder.event_id);
      setDismissedIds(prev => new Set([...prev, `${reminder.type}-${reminder.event_id}`]));
    } catch (error) {
      console.error('Failed to dismiss reminder:', error);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 85) return 'text-green-500';
    if (score >= 70) return 'text-blue-500';
    if (score >= 50) return 'text-yellow-500';
    return 'text-orange-500';
  };

  const getProgressColor = (score: number) => {
    if (score >= 85) return 'bg-green-500';
    if (score >= 70) return 'bg-blue-500';
    if (score >= 50) return 'bg-yellow-500';
    return 'bg-orange-500';
  };

  if (loading) {
    return (
      <Card className="animate-pulse">
        <CardHeader>
          <div className="h-6 w-32 bg-gray-200 rounded" />
        </CardHeader>
        <CardContent>
          <div className="h-4 w-full bg-gray-200 rounded" />
        </CardContent>
      </Card>
    );
  }

  if (!summary) {
    return null;
  }

  const visibleReminders = reminders.filter(
    r => !dismissedIds.has(`${r.type}-${r.event_id}`)
  );

  if (compact) {
    return (
      <Card className="border-l-4 border-l-blue-500 bg-gradient-to-r from-blue-50 to-white dark:from-blue-950/20 dark:to-transparent">
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{summary.wellness_status.emoji}</span>
              <div>
                <p className="font-medium">{summary.wellness_status.label}</p>
                <p className="text-sm text-muted-foreground">{summary.encouragement}</p>
              </div>
            </div>
            <div className="text-right">
              <span className={`text-2xl font-bold ${getScoreColor(summary.wellness_score)}`}>
                {summary.wellness_score}
              </span>
              <p className="text-xs text-muted-foreground">Wellness Score</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Main Wellness Card */}
      <Card className="overflow-hidden">
        <CardHeader className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Heart className="h-5 w-5 text-pink-500" />
              <CardTitle>Financial Wellness</CardTitle>
            </div>
            <Badge variant="outline" className="text-xs">
              Private to you
            </Badge>
          </div>
          <CardDescription>
            Your supportive financial companion 💙
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6 space-y-6">
          {/* Score Section */}
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center">
                <span className="text-3xl">{summary.wellness_status.emoji}</span>
              </div>
            </div>
            <div className="flex-1">
              <div className="flex items-baseline gap-2">
                <span className={`text-4xl font-bold ${getScoreColor(summary.wellness_score)}`}>
                  {summary.wellness_score}
                </span>
                <span className="text-muted-foreground">/100</span>
              </div>
              <Progress 
                value={summary.wellness_score} 
                className="h-2 mt-2"
              />
              <p className="text-sm mt-2 font-medium">{summary.wellness_status.label}</p>
              <p className="text-xs text-muted-foreground">
                {summary.wellness_status.description}
              </p>
            </div>
          </div>

          {/* Encouragement */}
          <div className="bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-950/20 dark:to-orange-950/20 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <Sparkles className="h-5 w-5 text-yellow-500 shrink-0 mt-0.5" />
              <p className="text-sm">{summary.encouragement}</p>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
              <p className="text-xs text-muted-foreground">Last 30 Days</p>
              <p className="text-xl font-semibold">₹{summary.spending_summary.last_30_days.toLocaleString()}</p>
              <p className="text-xs text-muted-foreground">
                {summary.spending_summary.transaction_count} transactions
              </p>
            </div>
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
              <p className="text-xs text-muted-foreground">Pending</p>
              <p className="text-xl font-semibold">₹{summary.pending_summary.total_pending.toLocaleString()}</p>
              <p className="text-xs text-muted-foreground">
                {summary.pending_summary.pending_count} settlements
              </p>
            </div>
          </div>

          {/* Insights */}
          {summary.insights.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                Insights
              </p>
              {summary.insights.map((insight, index) => (
                <div
                  key={index}
                  className={`flex items-start gap-3 p-3 rounded-lg ${
                    insight.type === 'positive' 
                      ? 'bg-green-50 dark:bg-green-950/20' 
                      : 'bg-gray-50 dark:bg-gray-800/50'
                  }`}
                >
                  <span className="text-lg">{insight.icon}</span>
                  <p className="text-sm">{insight.message}</p>
                </div>
              ))}
            </div>
          )}

          {/* Spending Breakdown */}
          {summary.spending_breakdown.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium">Spending by Category</p>
              <div className="space-y-2">
                {summary.spending_breakdown.slice(0, 4).map((cat, index) => (
                  <div key={index} className="flex items-center gap-3">
                    <span className="text-lg w-8">{cat.emoji}</span>
                    <div className="flex-1">
                      <div className="flex justify-between text-sm">
                        <span className="capitalize">{cat.category}</span>
                        <span className="text-muted-foreground">
                          ₹{cat.amount.toLocaleString()} ({cat.percentage}%)
                        </span>
                      </div>
                      <Progress value={cat.percentage} className="h-1.5 mt-1" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Positive Actions */}
          {summary.positive_actions.payments_count > 0 && (
            <div className="bg-green-50 dark:bg-green-950/20 rounded-lg p-4">
              <div className="flex items-center gap-2">
                <span className="text-xl">🎉</span>
                <div>
                  <p className="font-medium">{summary.positive_actions.message}</p>
                  <p className="text-sm text-muted-foreground">
                    Total: ₹{summary.positive_actions.payments_made.toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Gentle Reminders */}
      {visibleReminders.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Friendly Reminders</CardTitle>
            <CardDescription>No rush - just a gentle nudge!</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {visibleReminders.map((reminder, index) => (
              <div
                key={index}
                className="flex items-start gap-3 p-3 bg-blue-50 dark:bg-blue-950/20 rounded-lg"
              >
                <span className="text-lg">{reminder.icon}</span>
                <div className="flex-1">
                  <p className="text-sm font-medium">{reminder.title}</p>
                  <p className="text-xs text-muted-foreground">{reminder.message}</p>
                </div>
                {reminder.dismissible && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    onClick={() => dismissReminder(reminder)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default WellnessCard;
