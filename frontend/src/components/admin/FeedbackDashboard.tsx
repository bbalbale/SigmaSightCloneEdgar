'use client';

/**
 * FeedbackDashboard - Admin component for feedback analysis
 *
 * Phase 3.5 of PRD4: Admin visibility into feedback learning system.
 *
 * Features:
 * - Feedback statistics overview
 * - Negative feedback review queue
 * - Learned preferences display
 * - Manual learning job triggers
 *
 * Created: December 18, 2025
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  ThumbsUp,
  ThumbsDown,
  RefreshCw,
  Brain,
  AlertCircle,
  CheckCircle2,
  Clock,
  Edit,
  Play
} from 'lucide-react';
import { apiClient } from '@/services/apiClient';

interface FeedbackStats {
  total_feedback: number;
  positive_feedback: number;
  negative_feedback: number;
  positive_ratio: number;
  feedback_with_edits: number;
  recent_feedback_7d: number;
  generated_at: string;
}

interface NegativeFeedbackItem {
  feedback_id: string;
  message_id: string;
  user_id: string | null;
  rating: string;
  original_text: string | null;
  edited_text: string | null;
  comment: string | null;
  created_at: string;
}

interface LearnedPreference {
  memory_id: string;
  user_id: string;
  content: string;
  category: string | null;
  source: string | null;
  confidence: number | null;
  created_at: string;
}

export function FeedbackDashboard() {
  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [negativeFeedback, setNegativeFeedback] = useState<NegativeFeedbackItem[]>([]);
  const [learnedPreferences, setLearnedPreferences] = useState<LearnedPreference[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runningJob, setRunningJob] = useState(false);
  const [jobResult, setJobResult] = useState<string | null>(null);

  // Fetch all data on mount
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Fetch stats
      const statsResponse = await apiClient.get<FeedbackStats>('/api/v1/admin/feedback/stats');
      setStats(statsResponse);

      // Fetch negative feedback
      const negativeResponse = await apiClient.get<{ items: NegativeFeedbackItem[] }>(
        '/api/v1/admin/feedback/negative?limit=10&with_edits_only=true'
      );
      setNegativeFeedback(negativeResponse.items || []);

      // Fetch learned preferences
      const prefsResponse = await apiClient.get<{ preferences: LearnedPreference[] }>(
        '/api/v1/admin/feedback/learned-preferences?limit=20'
      );
      setLearnedPreferences(prefsResponse.preferences || []);

    } catch (err) {
      console.error('Failed to fetch feedback data:', err);
      setError('Failed to load feedback data. Make sure you have admin access.');
    } finally {
      setLoading(false);
    }
  };

  const runLearningJob = async () => {
    setRunningJob(true);
    setJobResult(null);

    try {
      const result = await apiClient.post<{
        status: string;
        users_processed: number;
        total_rules_created: number;
      }>('/api/v1/admin/feedback/run-learning', {});

      setJobResult(
        `Learning job completed: processed ${result.users_processed} users, ` +
        `created ${result.total_rules_created} rules`
      );

      // Refresh data
      await fetchData();
    } catch (err) {
      console.error('Learning job failed:', err);
      setJobResult('Learning job failed. Check server logs.');
    } finally {
      setRunningJob(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
        <span className="ml-2">Loading feedback data...</span>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Brain className="h-6 w-6" />
            Feedback Learning Dashboard
          </h2>
          <p className="text-muted-foreground">
            Monitor feedback patterns and AI learning progress
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchData}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={runLearningJob} disabled={runningJob}>
            {runningJob ? (
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-2" />
            )}
            Run Learning Job
          </Button>
        </div>
      </div>

      {/* Job Result Alert */}
      {jobResult && (
        <Alert className={jobResult.includes('failed') ? 'border-red-500' : 'border-green-500'}>
          {jobResult.includes('failed') ? (
            <AlertCircle className="h-4 w-4 text-red-600" />
          ) : (
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          )}
          <AlertDescription>{jobResult}</AlertDescription>
        </Alert>
      )}

      {/* Stats Overview */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">{stats.total_feedback}</div>
              <p className="text-xs text-muted-foreground">Total Feedback</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2">
                <ThumbsUp className="h-5 w-5 text-green-500" />
                <span className="text-2xl font-bold">{stats.positive_feedback}</span>
                <span className="text-sm text-muted-foreground">
                  ({(stats.positive_ratio * 100).toFixed(0)}%)
                </span>
              </div>
              <p className="text-xs text-muted-foreground">Positive Feedback</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2">
                <ThumbsDown className="h-5 w-5 text-red-500" />
                <span className="text-2xl font-bold">{stats.negative_feedback}</span>
              </div>
              <p className="text-xs text-muted-foreground">Negative Feedback</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2">
                <Edit className="h-5 w-5 text-blue-500" />
                <span className="text-2xl font-bold">{stats.feedback_with_edits}</span>
              </div>
              <p className="text-xs text-muted-foreground">With Edits</p>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Learned Preferences */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Brain className="h-5 w-5 text-purple-500" />
              Learned Preferences
            </CardTitle>
            <CardDescription>
              Rules automatically created from feedback patterns
            </CardDescription>
          </CardHeader>
          <CardContent>
            {learnedPreferences.length === 0 ? (
              <p className="text-muted-foreground text-sm">No learned preferences yet</p>
            ) : (
              <div className="space-y-3 max-h-[400px] overflow-y-auto">
                {learnedPreferences.map((pref) => (
                  <div
                    key={pref.memory_id}
                    className="p-3 rounded-lg border bg-muted/30"
                  >
                    <p className="text-sm">{pref.content}</p>
                    <div className="flex gap-2 mt-2">
                      <Badge variant="outline" className="text-xs">
                        {pref.source || 'feedback'}
                      </Badge>
                      {pref.confidence && (
                        <Badge variant="secondary" className="text-xs">
                          {(pref.confidence * 100).toFixed(0)}% confidence
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {new Date(pref.created_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Negative Feedback Queue */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <ThumbsDown className="h-5 w-5 text-red-500" />
              Negative Feedback Queue
            </CardTitle>
            <CardDescription>
              Recent negative feedback with user corrections
            </CardDescription>
          </CardHeader>
          <CardContent>
            {negativeFeedback.length === 0 ? (
              <p className="text-muted-foreground text-sm">No negative feedback with edits</p>
            ) : (
              <div className="space-y-3 max-h-[400px] overflow-y-auto">
                {negativeFeedback.map((item) => (
                  <div
                    key={item.feedback_id}
                    className="p-3 rounded-lg border border-red-200 dark:border-red-900/30"
                  >
                    {item.comment && (
                      <p className="text-sm font-medium mb-2">
                        Comment: &quot;{item.comment}&quot;
                      </p>
                    )}

                    {item.original_text && (
                      <div className="mb-2">
                        <p className="text-xs text-muted-foreground">Original:</p>
                        <p className="text-sm line-clamp-2">{item.original_text}</p>
                      </div>
                    )}

                    {item.edited_text && (
                      <div>
                        <p className="text-xs text-muted-foreground">User Edit:</p>
                        <p className="text-sm text-green-700 dark:text-green-400 line-clamp-2">
                          {item.edited_text}
                        </p>
                      </div>
                    )}

                    <div className="flex items-center gap-2 mt-2">
                      <Clock className="h-3 w-3 text-muted-foreground" />
                      <span className="text-xs text-muted-foreground">
                        {new Date(item.created_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Info Footer */}
      <div className="rounded-md bg-muted/50 p-4">
        <p className="text-sm text-muted-foreground">
          <strong>How it works:</strong> Positive feedback stores responses as RAG examples
          for few-shot learning. Negative feedback with edits triggers LLM analysis to extract
          user preferences as memory rules. The learning job runs daily at 8 PM ET or can be
          triggered manually above.
        </p>
      </div>
    </div>
  );
}

export default FeedbackDashboard;
