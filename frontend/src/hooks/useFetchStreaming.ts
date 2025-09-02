/**
 * Fetch Streaming Hook
 * Handles SSE streaming with fetch() and manual parsing
 * Based on Technical Specifications Section 2
 */

import { useCallback, useRef } from 'react';
import { useStreamStore } from '@/stores/streamStore';
import { chatAuthService } from '@/services/chatAuthService';

// SSE Event types from Technical Specifications
interface SSEEvent {
  run_id: string;
  seq: number;
  type: 'token' | 'tool_call' | 'tool_result' | 'error' | 'done' | 'heartbeat';
  data: {
    delta?: string;
    tool_name?: string;
    tool_args?: any;
    tool_result?: any;
    error?: string;
    error_type?: 'AUTH_EXPIRED' | 'RATE_LIMITED' | 'NETWORK_ERROR' | 'SERVER_ERROR' | 'FATAL_ERROR';
    final_text?: string;
  };
  timestamp: number;
}

interface StreamingOptions {
  onToken?: (token: string) => void;
  onToolCall?: (toolName: string, args: any) => void;
  onToolResult?: (toolName: string, result: any) => void;
  onError?: (error: any) => void;
  onDone?: (finalText: string) => void;
  onHeartbeat?: () => void;
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
      // Message will be queued by the calling component
      return null;
    }

    // Generate run_id
    const runId = `run_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    // Create abort controller
    const abortController = new AbortController();
    activeStreams.current.set(runId, abortController);
    setAbortController(abortController);

    // Start streaming state
    startStreaming(conversationId, runId);

    try {
      // Make authenticated request
      const response = await chatAuthService.authenticatedFetch(
        '/api/proxy/api/v1/chat/send',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          },
          body: JSON.stringify({
            text: message,  // Backend expects 'text' not 'message'
            conversation_id: conversationId,
          }),
          signal: abortController.signal,
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw error;
      }

      // Check for SSE content type
      const contentType = response.headers.get('content-type');
      if (!contentType?.includes('text/event-stream')) {
        throw new Error('Expected SSE response but got: ' + contentType);
      }

      // Parse SSE stream
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      let buffer = '';
      let lastHeartbeat = Date.now();
      const heartbeatInterval = 15000; // 15 seconds

      // Process stream
      while (true) {
        // Check for heartbeat timeout
        if (Date.now() - lastHeartbeat > heartbeatInterval * 2) {
          console.warn('Heartbeat timeout, connection may be stale');
        }

        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // Process complete events
        const lines = buffer.split('\n');
        buffer = lines[lines.length - 1]; // Keep incomplete line in buffer

        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim();

          if (line.startsWith('event:')) {
            const eventType = line.slice(6).trim();
            
            // Get the data line (should be next)
            if (i + 1 < lines.length - 1) {
              const dataLine = lines[i + 1].trim();
              if (dataLine.startsWith('data:')) {
                const dataStr = dataLine.slice(5).trim();
                
                try {
                  const eventData = JSON.parse(dataStr) as SSEEvent;
                  
                  // Process based on event type
                  switch (eventData.type) {
                    case 'token':
                      if (eventData.data.delta) {
                        addToBuffer(runId, eventData.data.delta, eventData.seq);
                        options.onToken?.(eventData.data.delta);
                      }
                      break;
                      
                    case 'tool_call':
                      if (eventData.data.tool_name && eventData.data.tool_args) {
                        options.onToolCall?.(eventData.data.tool_name, eventData.data.tool_args);
                      }
                      break;
                      
                    case 'tool_result':
                      if (eventData.data.tool_name && eventData.data.tool_result) {
                        options.onToolResult?.(eventData.data.tool_name, eventData.data.tool_result);
                      }
                      break;
                      
                    case 'heartbeat':
                      lastHeartbeat = Date.now();
                      options.onHeartbeat?.();
                      break;
                      
                    case 'error':
                      const error = {
                        message: eventData.data.error || 'Unknown error',
                        error_type: eventData.data.error_type,
                        run_id: eventData.run_id,
                      };
                      options.onError?.(error);
                      break;
                      
                    case 'done':
                      const finalText = sealBuffer(runId);
                      options.onDone?.(eventData.data.final_text || finalText);
                      break;
                  }
                } catch (e) {
                  console.error('Failed to parse SSE event:', e, dataStr);
                }
                
                i++; // Skip the data line since we processed it
              }
            }
          } else if (line.startsWith('data:')) {
            // Handle data-only lines (legacy format)
            const dataStr = line.slice(5).trim();
            if (dataStr === '[DONE]') {
              const finalText = sealBuffer(runId);
              options.onDone?.(finalText);
              break;
            }
            
            try {
              const data = JSON.parse(dataStr);
              
              // Handle different data formats
              if (data.delta) {
                // Simple delta format
                addToBuffer(runId, data.delta, data.seq || 0);
                options.onToken?.(data.delta);
              } else if (data.type === 'heartbeat') {
                lastHeartbeat = Date.now();
                options.onHeartbeat?.();
              } else if (data.error_type) {
                options.onError?.(data);
              }
            } catch (e) {
              // Not JSON, might be plain text
              if (dataStr && dataStr !== '[DONE]') {
                addToBuffer(runId, dataStr, 0);
                options.onToken?.(dataStr);
              }
            }
          }
        }
      }

    } catch (error: any) {
      if (error.name !== 'AbortError') {
        console.error('Streaming error:', error);
        
        // Classify error type
        let errorType: SSEEvent['data']['error_type'] = 'SERVER_ERROR';
        if (error.message?.includes('auth')) {
          errorType = 'AUTH_EXPIRED';
        } else if (error.message?.includes('rate')) {
          errorType = 'RATE_LIMITED';
        } else if (error.message?.includes('network')) {
          errorType = 'NETWORK_ERROR';
        }
        
        options.onError?.({
          message: error.message || 'Streaming failed',
          error_type: errorType,
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