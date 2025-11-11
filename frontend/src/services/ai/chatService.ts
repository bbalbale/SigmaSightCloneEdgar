/**
 * AI Chat Service
 *
 * Handles OpenAI streaming and tool execution.
 * Uses existing frontend services via tools.ts
 */

import OpenAI from 'openai';
import { toolDefinitions, executeTool } from './tools';
import { promptManager } from '@/lib/ai/promptManager';

interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

interface StreamOptions {
  conversationId: string;
  message: string;
  mode: string;
  portfolioId: string;
  messageHistory: ChatMessage[];
  onToken?: (token: string) => void;
  onToolCall?: (toolName: string, args: any) => void;
  onToolResult?: (result: any) => void;
  onError?: (error: Error) => void;
  onDone?: (finalText: string) => void;
}

export class ChatService {
  private client: OpenAI | null = null;

  private getClient(): OpenAI {
    if (this.client) {
      return this.client;
    }

    // Only initialize in browser (not during SSR)
    if (typeof window === 'undefined') {
      throw new Error('ChatService can only be used in browser');
    }

    // Get OpenAI API key from environment
    const apiKey = process.env.NEXT_PUBLIC_OPENAI_API_KEY;

    if (!apiKey) {
      throw new Error('OPENAI_API_KEY not found in environment variables');
    }

    this.client = new OpenAI({
      apiKey: apiKey,
      baseURL: `${window.location.origin}/api/openai-proxy`,  // Use absolute URL for proxy
      dangerouslyAllowBrowser: true
    });

    return this.client;
  }

  async streamResponse(options: StreamOptions): Promise<void> {
    const {
      message,
      mode,
      portfolioId,
      messageHistory,
      onToken,
      onToolCall,
      onToolResult,
      onError,
      onDone
    } = options;

    try {
      console.log('[AI Chat] Starting stream response', { mode, portfolioId });

      // Load system prompt
      const systemPrompt = await promptManager.getSystemPrompt(mode, {
        portfolio_id: portfolioId
      });

      // Build messages
      const messages: any[] = [
        { role: 'system', content: systemPrompt },
        ...messageHistory,
        { role: 'user', content: message }
      ];

      console.log('[AI Chat] Calling OpenAI with', messages.length, 'messages');

      // Call OpenAI with streaming
      const stream = await this.getClient().chat.completions.create({
        model: 'gpt-4-turbo-preview',
        messages: messages,
        tools: toolDefinitions as any,
        stream: true
      });

      let currentContent = '';
      const toolCalls: any[] = [];
      const toolCallsAccumulator: Map<string, any> = new Map();

      // Stream tokens
      for await (const chunk of stream) {
        const delta = chunk.choices[0]?.delta;

        // Handle text tokens
        if (delta?.content) {
          currentContent += delta.content;
          onToken?.(delta.content);
        }

        // Handle tool calls (accumulate deltas)
        if (delta?.tool_calls) {
          for (const toolCallDelta of delta.tool_calls) {
            const index = toolCallDelta.index;

            if (!toolCallsAccumulator.has(index.toString())) {
              toolCallsAccumulator.set(index.toString(), {
                id: toolCallDelta.id || '',
                type: 'function',
                function: {
                  name: toolCallDelta.function?.name || '',
                  arguments: ''
                }
              });
            }

            const accumulated = toolCallsAccumulator.get(index.toString());

            if (toolCallDelta.id) {
              accumulated.id = toolCallDelta.id;
            }

            if (toolCallDelta.function?.name) {
              accumulated.function.name = toolCallDelta.function.name;
            }

            if (toolCallDelta.function?.arguments) {
              accumulated.function.arguments += toolCallDelta.function.arguments;
            }
          }
        }
      }

      // Process accumulated tool calls
      if (toolCallsAccumulator.size > 0) {
        console.log('[AI Chat] Processing', toolCallsAccumulator.size, 'tool calls');

        for (const toolCall of toolCallsAccumulator.values()) {
          const toolName = toolCall.function.name;
          let toolArgs: any = {};

          try {
            toolArgs = JSON.parse(toolCall.function.arguments);
          } catch (e) {
            console.error('[AI Chat] Failed to parse tool arguments:', e);
            toolArgs = {};
          }

          onToolCall?.(toolName, toolArgs);

          // Execute tool using existing services
          const result = await executeTool(toolName, toolArgs);

          onToolResult?.(result);

          toolCalls.push({
            id: toolCall.id,
            name: toolName,
            result: result
          });
        }

        // Continue conversation with tool results
        await this.continueWithToolResults(
          messages,
          toolCalls,
          onToken,
          onDone
        );
      } else {
        onDone?.(currentContent);
      }

    } catch (error) {
      console.error('[AI Chat] Error:', error);
      onError?.(error as Error);
    }
  }

  private async continueWithToolResults(
    messages: any[],
    toolCalls: any[],
    onToken?: (token: string) => void,
    onDone?: (text: string) => void
  ) {
    console.log('[AI Chat] Continuing with tool results');

    // Build continuation message with tool results
    const toolSummary = toolCalls
      .map(tc => {
        const resultStr = JSON.stringify(tc.result, null, 2);
        // Truncate if too large (>5000 chars)
        const truncated = resultStr.length > 5000
          ? resultStr.substring(0, 5000) + '\n... (truncated)'
          : resultStr;
        return `Tool '${tc.name}' returned:\n${truncated}`;
      })
      .join('\n\n');

    messages.push({
      role: 'user',
      content: `Based on the tool results below, please provide a comprehensive analysis:\n\n${toolSummary}`
    });

    // Get final response
    const stream = await this.getClient().chat.completions.create({
      model: 'gpt-4-turbo-preview',
      messages: messages,
      stream: true
    });

    let finalContent = '';
    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta;
      if (delta?.content) {
        finalContent += delta.content;
        onToken?.(delta.content);
      }
    }

    onDone?.(finalContent);
  }
}

// Export singleton instance
export const chatService = new ChatService();
