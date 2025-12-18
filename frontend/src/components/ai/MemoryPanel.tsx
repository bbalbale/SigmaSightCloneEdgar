'use client';

/**
 * MemoryPanel - User AI Memory Management Component
 *
 * Displays and manages AI memories (preferences, context, corrections)
 * that personalize the AI assistant's responses.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Trash2, Brain, RefreshCw, AlertCircle, Plus } from 'lucide-react';
import memoryApi, { Memory, MemoryCountResponse } from '@/services/memoryApi';

interface MemoryPanelProps {
  portfolioId?: string;
  onMemoryChange?: () => void;
}

export function MemoryPanel({ portfolioId, onMemoryChange }: MemoryPanelProps) {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [memoryCount, setMemoryCount] = useState<MemoryCountResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [newMemory, setNewMemory] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  // Fetch memories
  const fetchMemories = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [listResponse, countResponse] = await Promise.all([
        memoryApi.listMemories(undefined, portfolioId),
        memoryApi.getMemoryCount(),
      ]);
      setMemories(listResponse.memories);
      setMemoryCount(countResponse);
    } catch (err) {
      console.error('Failed to fetch memories:', err);
      setError('Failed to load memories');
    } finally {
      setLoading(false);
    }
  }, [portfolioId]);

  // Initial fetch
  useEffect(() => {
    fetchMemories();
  }, [fetchMemories]);

  // Delete a memory
  const handleDelete = async (memoryId: string) => {
    setDeletingId(memoryId);
    try {
      await memoryApi.deleteMemory(memoryId);
      setMemories((prev) => prev.filter((m) => m.id !== memoryId));
      if (memoryCount) {
        setMemoryCount({ ...memoryCount, count: memoryCount.count - 1 });
      }
      onMemoryChange?.();
    } catch (err) {
      console.error('Failed to delete memory:', err);
      setError('Failed to delete memory');
    } finally {
      setDeletingId(null);
    }
  };

  // Delete all memories
  const handleDeleteAll = async () => {
    if (!confirm('Are you sure you want to delete all memories? This cannot be undone.')) {
      return;
    }
    setLoading(true);
    try {
      await memoryApi.deleteAllMemories();
      setMemories([]);
      if (memoryCount) {
        setMemoryCount({ ...memoryCount, count: 0 });
      }
      onMemoryChange?.();
    } catch (err) {
      console.error('Failed to delete all memories:', err);
      setError('Failed to delete memories');
    } finally {
      setLoading(false);
    }
  };

  // Add a new memory manually
  const handleAddMemory = async () => {
    if (!newMemory.trim()) return;

    setIsAdding(true);
    try {
      const created = await memoryApi.createMemory({
        content: newMemory.trim(),
        scope: portfolioId ? 'portfolio' : 'user',
        portfolio_id: portfolioId,
      });
      setMemories((prev) => [created, ...prev]);
      if (memoryCount) {
        setMemoryCount({ ...memoryCount, count: memoryCount.count + 1 });
      }
      setNewMemory('');
      onMemoryChange?.();
    } catch (err) {
      console.error('Failed to add memory:', err);
      setError('Failed to add memory');
    } finally {
      setIsAdding(false);
    }
  };

  // Format date
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Unknown date';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  // Get scope badge color
  const getScopeBadgeClass = (scope: string) => {
    return scope === 'portfolio'
      ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200';
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-purple-500" />
            <CardTitle className="text-lg">AI Memories</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={fetchMemories}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
            {memories.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleDeleteAll}
                className="text-red-500 hover:text-red-700"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
        <CardDescription>
          Things the AI remembers about you to personalize responses.
          {memoryCount && (
            <span className="ml-1">
              ({memoryCount.count}/{memoryCount.max_allowed} stored)
            </span>
          )}
        </CardDescription>
      </CardHeader>

      <CardContent>
        {/* Add new memory */}
        <div className="mb-4 flex gap-2">
          <input
            type="text"
            value={newMemory}
            onChange={(e) => setNewMemory(e.target.value)}
            placeholder="Add a preference or note..."
            className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
            maxLength={500}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleAddMemory();
              }
            }}
          />
          <Button
            size="sm"
            onClick={handleAddMemory}
            disabled={isAdding || !newMemory.trim()}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        {/* Error state */}
        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-md bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}

        {/* Loading state */}
        {loading && memories.length === 0 && (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
            Loading memories...
          </div>
        )}

        {/* Empty state */}
        {!loading && memories.length === 0 && (
          <div className="py-8 text-center text-muted-foreground">
            <Brain className="mx-auto mb-2 h-8 w-8 opacity-50" />
            <p>No memories yet</p>
            <p className="text-xs mt-1">
              The AI will automatically remember important preferences as you chat.
            </p>
          </div>
        )}

        {/* Memory list */}
        {memories.length > 0 && (
          <div className="space-y-2">
            {memories.map((memory) => (
              <div
                key={memory.id}
                className="flex items-start justify-between gap-2 rounded-md border p-3 hover:bg-accent/50 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm">{memory.content}</p>
                  <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                    <span className={`px-1.5 py-0.5 rounded ${getScopeBadgeClass(memory.scope)}`}>
                      {memory.scope}
                    </span>
                    <span>{formatDate(memory.created_at)}</span>
                    {memory.tags?.source === 'auto_extraction' && (
                      <span className="text-purple-500">auto-detected</span>
                    )}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDelete(memory.id)}
                  disabled={deletingId === memory.id}
                  className="text-muted-foreground hover:text-red-500"
                >
                  {deletingId === memory.id ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <Trash2 className="h-4 w-4" />
                  )}
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default MemoryPanel;
