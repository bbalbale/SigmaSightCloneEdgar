/**
 * Stream Store - Runtime streaming state management
 * Handles SSE streaming, message buffering, and queue management
 * Based on Technical Specifications Section 1-3
 */

import { create } from 'zustand';

// Types from Technical Specifications
interface StreamBuffer {
  text: string;        // Accumulated message text
  lastSeq: number;     // Last processed sequence number
  startTime: number;   // Timestamp for timeout detection
}

interface MessageQueueItem {
  conversationId: string;
  message: string;
  timestamp: number;
}

interface StreamStore {
  // Stream buffers by run_id
  streamBuffers: Map<string, StreamBuffer>;
  activeRuns: Set<string>;
  processing: boolean;
  
  // Message queue
  messageQueue: MessageQueueItem | null;
  conversationLocks: Map<string, boolean>;
  
  // Current streaming state
  isStreaming: boolean;
  currentRunId: string | null;
  currentConversationId: string | null;
  currentAssistantMessageId: string | null; // Backend-provided ID
  abortController: AbortController | null;
  
  // Actions
  startStreaming: (conversationId: string, runId: string) => void;
  stopStreaming: () => void;
  addToBuffer: (runId: string, text: string, seq: number) => void;
  sealBuffer: (runId: string) => string;
  queueMessage: (conversationId: string, message: string) => void;
  processQueue: () => MessageQueueItem | null;
  cancelConversation: (conversationId: string) => void;
  setAbortController: (controller: AbortController) => void;
  clearBuffer: (runId: string) => void;
  isConversationLocked: (conversationId: string) => boolean;
  setAssistantMessageId: (messageId: string) => void;
  reset: () => void;
}

export const useStreamStore = create<StreamStore>((set, get) => ({
  // Initial state
  streamBuffers: new Map(),
  activeRuns: new Set(),
  processing: false,
  messageQueue: null,
  conversationLocks: new Map(),
  isStreaming: false,
  currentRunId: null,
  currentConversationId: null,
  currentAssistantMessageId: null,
  abortController: null,

  // Start streaming for a conversation
  startStreaming: (conversationId: string, runId: string) => {
    const state = get();
    
    // Lock conversation
    const locks = new Map(state.conversationLocks);
    locks.set(conversationId, true);
    
    // Initialize buffer for this run
    const buffers = new Map(state.streamBuffers);
    buffers.set(runId, {
      text: '',
      lastSeq: 0,
      startTime: Date.now(),
    });
    
    // Add to active runs
    const runs = new Set(state.activeRuns);
    runs.add(runId);
    
    set({
      isStreaming: true,
      currentRunId: runId,
      currentConversationId: conversationId,
      processing: true,
      streamBuffers: buffers,
      activeRuns: runs,
      conversationLocks: locks,
    });
  },

  // Stop streaming
  stopStreaming: () => {
    const state = get();
    
    // Unlock conversation
    if (state.currentConversationId) {
      const locks = new Map(state.conversationLocks);
      locks.set(state.currentConversationId, false);
      set({ conversationLocks: locks });
    }
    
    // Remove from active runs
    if (state.currentRunId) {
      const runs = new Set(state.activeRuns);
      runs.delete(state.currentRunId);
      set({ activeRuns: runs });
    }
    
    set({
      isStreaming: false,
      currentRunId: null,
      currentConversationId: null,
      currentAssistantMessageId: null,
      processing: false,
      abortController: null,
    });
  },

  // Add text to buffer with sequence validation
  addToBuffer: (runId: string, text: string, seq: number) => {
    const state = get();
    const buffers = new Map(state.streamBuffers);
    const buffer = buffers.get(runId);
    
    if (buffer) {
      // Check sequence number for deduplication
      if (seq > buffer.lastSeq) {
        // Create new buffer object instead of mutating
        buffers.set(runId, {
          text: buffer.text + text,
          lastSeq: seq,
          startTime: buffer.startTime,
        });
        set({ streamBuffers: buffers });
      }
      // Ignore out-of-order or duplicate sequences
    } else {
      // Create new buffer if doesn't exist
      buffers.set(runId, {
        text: text,
        lastSeq: seq,
        startTime: Date.now(),
      });
      set({ streamBuffers: buffers });
    }
  },

  // Seal buffer and return final text
  sealBuffer: (runId: string): string => {
    const state = get();
    const buffer = state.streamBuffers.get(runId);
    
    if (buffer) {
      const finalText = buffer.text;
      
      // Remove from active runs
      const runs = new Set(state.activeRuns);
      runs.delete(runId);
      
      // Keep buffer for potential replay but mark as sealed
      set({ activeRuns: runs });
      
      return finalText;
    }
    
    return '';
  },

  // Queue a message (last-write-wins policy)
  queueMessage: (conversationId: string, message: string) => {
    const state = get();
    
    if (state.processing && state.currentConversationId === conversationId) {
      // Replace any existing queued message (last-write-wins)
      set({
        messageQueue: {
          conversationId,
          message,
          timestamp: Date.now(),
        },
      });
    } else if (!state.processing) {
      // If not processing, this becomes the current message
      // (Will be handled by the chat service)
    }
  },

  // Process queued message
  processQueue: (): MessageQueueItem | null => {
    const state = get();
    const queued = state.messageQueue;
    
    if (queued && !state.processing) {
      // Clear queue and return message
      set({ messageQueue: null });
      return queued;
    }
    
    return null;
  },

  // Cancel all operations for a conversation
  cancelConversation: (conversationId: string) => {
    const state = get();
    
    // Abort if this is the current conversation
    if (state.currentConversationId === conversationId) {
      state.abortController?.abort();
      
      // Clear current streaming state
      state.stopStreaming();
    }
    
    // Clear any queued messages for this conversation
    if (state.messageQueue?.conversationId === conversationId) {
      set({ messageQueue: null });
    }
    
    // Unlock conversation
    const locks = new Map(state.conversationLocks);
    locks.set(conversationId, false);
    set({ conversationLocks: locks });
  },

  // Set abort controller for current stream
  setAbortController: (controller: AbortController) => {
    set({ abortController: controller });
  },

  // Clear a specific buffer
  clearBuffer: (runId: string) => {
    const state = get();
    const buffers = new Map(state.streamBuffers);
    buffers.delete(runId);
    
    const runs = new Set(state.activeRuns);
    runs.delete(runId);
    
    set({ 
      streamBuffers: buffers,
      activeRuns: runs,
    });
  },

  // Check if conversation is locked
  isConversationLocked: (conversationId: string): boolean => {
    const state = get();
    return state.conversationLocks.get(conversationId) || false;
  },

  // Set the current assistant message ID from backend
  setAssistantMessageId: (messageId: string) => {
    set({ currentAssistantMessageId: messageId });
  },

  // Reset entire store
  reset: () => {
    const state = get();
    
    // Abort any active streams
    state.abortController?.abort();
    
    set({
      streamBuffers: new Map(),
      activeRuns: new Set(),
      processing: false,
      messageQueue: null,
      conversationLocks: new Map(),
      isStreaming: false,
      currentRunId: null,
      currentConversationId: null,
      currentAssistantMessageId: null,
      abortController: null,
    });
  },
}));

// Export types
export type { StreamBuffer, MessageQueueItem };