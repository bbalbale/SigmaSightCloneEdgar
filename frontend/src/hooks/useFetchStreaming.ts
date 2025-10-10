/**
 * Fetch Streaming Hook
 * Handles streaming with frontend chatService (OpenAI Chat Completions API)
 * Migrated from backend SSE to direct OpenAI integration
 */

import { useCallback, useRef } from 'react';
import { useStreamStore } from '@/stores/streamStore';
import { useChatStore } from '@/stores/chatStore';
import { usePortfolioStore } from '@/stores/portfolioStore';
import { chatService } from '@/services/ai/chatService';

// SSE Event types from Technical Specifications
interface SSEEvent {
  run_id: string;
  seq: number;
  type: 'token' | 'tool_call' | 'tool_result' | 'error' | 'done' | 'heartbeat' | 'message_created' | 'start' | 'response_id' | 'info';
  data: {
    delta?: string;
    tool_name?: string;
    tool_args?: any;
    tool_result?: any;
    error?: string;
    error_type?: string; // broadened to allow backend-specific values like 'api_failure', 'continuation_failed'
    final_text?: string;
    token_counts?: { initial?: number; continuation?: number; [k: string]: any };
    post_tool_first_token_gaps_ms?: number[];
    event_timeline?: Array<{ type: string; t_ms: number }>;
    fallback_used?: boolean;
    // info event fields
    info_type?: string;
    retry_in_ms?: number;
    attempt?: number;
    max_attempts?: number;
    from?: string;
    to?: string;
    // message_created event data
    user_message_id?: string;
    assistant_message_id?: string;
    conversation_id?: string;
  };
  timestamp: number;
}

interface StreamingOptions {
  onToken?: (token: string, runId?: string) => void;
  onToolCall?: (toolName: string, args: any) => void;
  onToolResult?: (toolName: string, result: any) => void;
  onError?: (error: any) => void;
  onDone?: (finalText: string) => void;
  onHeartbeat?: () => void;
  onInfo?: (info: { info_type: string; [k: string]: any }) => void;
  onMessageCreated?: (event: {
    user_message_id: string;
    assistant_message_id: string;
    conversation_id: string;
    run_id: string;
  }) => void;
}

export function useFetchStreaming() {
  const {
    startStreaming,
    stopStreaming,
    addToBuffer,
    sealBuffer,
    setAbortController,
    isConversationLocked,
  } = useStreamStore();

  const activeStreams = useRef<Map<string, AbortController>>(new Map());

  const streamMessage = useCallback(async (
    conversationId: string,
    message: string,
    options: StreamingOptions = {}
  ) => {
    // Check if conversation is locked
    if (isConversationLocked(conversationId)) {
      console.warn('Conversation is locked, queueing message');
      return null;
    }

    // Generate run_id
    const runId = `run_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    // Create abort controller (for future implementation if needed)
    const abortController = new AbortController();
    activeStreams.current.set(runId, abortController);
    setAbortController(abortController);

    // Start streaming state
    startStreaming(conversationId, runId);

    try {
      console.log('[AI Chat] Starting stream with frontend chatService:', { conversationId, message });

      // Get mode and portfolio ID from stores
      const { currentMode } = useChatStore.getState();
      const { portfolioId } = usePortfolioStore.getState();

      // Build message history from chat store
      const { getMessages } = useChatStore.getState();
      const messages = getMessages(conversationId);

      // Convert to OpenAI format (only user and assistant messages, exclude system messages)
      const messageHistory = messages
        .filter(m => m.role !== 'system')
        .map(m => ({
          role: m.role,
          content: m.content
        }));

      console.log('[AI Chat] Using mode:', currentMode, 'portfolioId:', portfolioId, 'history:', messageHistory.length, 'messages');

      // Create message IDs for user and assistant messages
      const userMessageId = `user-${Date.now()}`;
      const assistantMessageId = `assistant-${Date.now()}`;

      console.log('[useFetchStreaming] Created message IDs:', {
        userMessageId,
        assistantMessageId,
        conversationId,
        hasCallback: !!options.onMessageCreated
      });

      // Fire onMessageCreated callback immediately to create UI messages
      if (options.onMessageCreated) {
        console.log('[useFetchStreaming] Firing onMessageCreated callback');
        options.onMessageCreated({
          user_message_id: userMessageId,
          assistant_message_id: assistantMessageId,
          conversation_id: conversationId,
          run_id: runId
        });
        console.log('[useFetchStreaming] onMessageCreated callback fired');
      } else {
        console.warn('[useFetchStreaming] No onMessageCreated callback provided!');
      }

      // Call frontend chatService
      await chatService.streamResponse({
        conversationId,
        message,
        mode: currentMode,
        portfolioId: portfolioId || '',
        messageHistory,

        // Map callbacks to existing interface
        onToken: (token: string) => {
          console.log('[AI Chat] Token received:', token.substring(0, 50));
          addToBuffer(runId, token, 0);
          options.onToken?.(token, runId);
        },

        onToolCall: (toolName: string, args: any) => {
          console.log('[AI Chat] Tool call:', toolName, args);
          options.onToolCall?.(toolName, args);
        },

        onToolResult: (result: any) => {
          console.log('[AI Chat] Tool result received');
          options.onToolResult?.('tool', result);
        },

        onError: (error: Error) => {
          console.error('[AI Chat] Error:', error);

          // Classify error type
          let errorType: SSEEvent['data']['error_type'] = 'SERVER_ERROR';
          if (error.message?.includes('auth') || error.message?.includes('API')) {
            errorType = 'AUTH_EXPIRED';
          } else if (error.message?.includes('rate')) {
            errorType = 'RATE_LIMITED';
          } else if (error.message?.includes('network') || error.message?.includes('fetch')) {
            errorType = 'NETWORK_ERROR';
          }

          options.onError?.({
            message: error.message || 'AI service error',
            error_type: errorType,
            run_id: runId,
          });
        },

        onDone: (finalText: string) => {
          console.log('[AI Chat] Stream complete, final text length:', finalText?.length || 0);
          const bufferedFinal = sealBuffer(runId);
          // Use buffered text if available, otherwise use finalText from service
          const finalOut = bufferedFinal || finalText || 'No response received.';
          options.onDone?.(finalOut);
        },
      });

    } catch (error: any) {
      if (error.name !== 'AbortError') {
        console.error('[AI Chat] Streaming error:', error);

        options.onError?.({
          message: error.message || 'Streaming failed',
          error_type: 'SERVER_ERROR',
          run_id: runId,
        });
      }
    } finally {
      // Clean up
      activeStreams.current.delete(runId);
      stopStreaming();
    }

    return runId;
  }, [startStreaming, stopStreaming, addToBuffer, sealBuffer, setAbortController, isConversationLocked]);

  const abortStream = useCallback((runId?: string) => {
    if (runId) {
      const controller = activeStreams.current.get(runId);
      controller?.abort();
      activeStreams.current.delete(runId);
    } else {
      // Abort all active streams
      activeStreams.current.forEach(controller => controller.abort());
      activeStreams.current.clear();
    }
    stopStreaming();
  }, [stopStreaming]);

  return {
    streamMessage,
    abortStream,
  };
}

// Export types
export type { SSEEvent, StreamingOptions };