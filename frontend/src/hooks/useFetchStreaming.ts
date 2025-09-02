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
  type: 'token' | 'tool_call' | 'tool_result' | 'error' | 'done' | 'heartbeat' | 'message_created';
  data: {
    delta?: string;
    tool_name?: string;
    tool_args?: any;
    tool_result?: any;
    error?: string;
    error_type?: 'AUTH_EXPIRED' | 'RATE_LIMITED' | 'NETWORK_ERROR' | 'SERVER_ERROR' | 'FATAL_ERROR';
    final_text?: string;
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
      console.log('Starting chat stream request:', { conversationId, message });
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
      
      console.log('Response received:', {
        ok: response.ok,
        status: response.status,
        contentType: response.headers.get('content-type'),
        headers: Object.fromEntries(response.headers.entries())
      });

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

        // Process complete SSE events (separated by double newlines)
        const events = buffer.split('\n\n');
        buffer = events.pop() || ''; // Keep incomplete event in buffer

        for (const event of events) {
          if (!event.trim()) continue;
          
          const lines = event.split('\n').map(line => line.trim()).filter(line => line);
          let eventType = '';
          let dataStr = '';
          
          console.log('Processing SSE event:', { event, lines });
          
          // Parse event/data pairs
          for (const line of lines) {
            if (line.startsWith('event:')) {
              eventType = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
              dataStr = line.slice(5).trim();
            }
          }
          
          console.log('Parsed event:', { eventType, dataStr });
          
          // Handle message_created event specially (different format)
          if (eventType === 'message_created' && dataStr) {
            try {
              const messageData = JSON.parse(dataStr);
              console.log('Processing message_created event:', messageData);
              
              // Update the runId with the one from message_created event
              if (messageData.run_id) {
                // Store the backend-provided runId for future reference
                const backendRunId = messageData.run_id;
                // We may need to update our local runId mapping here
              }
              
              options.onMessageCreated?.(messageData);
              continue; // Skip to next event
            } catch (e) {
              console.error('Failed to parse message_created event:', e, dataStr);
            }
          }
          
          // Process the event if we have both type and data
          if (eventType && dataStr) {
            try {
              const eventData = JSON.parse(dataStr) as SSEEvent;
              
              // Process based on event type
              switch (eventData.type) {
                case 'token':
                  if (eventData.data.delta) {
                    console.log('Adding token to buffer:', { runId, delta: eventData.data.delta, seq: eventData.seq });
                    addToBuffer(runId, eventData.data.delta, eventData.seq);
                    console.log('Calling onToken callback with:', eventData.data.delta, 'runId:', runId);
                    options.onToken?.(eventData.data.delta, runId);
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
          } else if (dataStr && !eventType) {
            // Handle data-only lines (legacy format)
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
                options.onToken?.(data.delta, runId);
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
                options.onToken?.(dataStr, runId);
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