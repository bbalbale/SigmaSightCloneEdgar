/**
 * Prompt Manager
 *
 * Loads mode-specific prompts and injects variables
 */

export class PromptManager {
  private prompts: Map<string, string> = new Map();

  async loadPrompt(mode: string): Promise<string> {
    // Check cache first
    if (this.prompts.has(mode)) {
      return this.prompts.get(mode)!;
    }

    try {
      // Load prompt file dynamically
      // Note: These are TypeScript files (converted from markdown) from backend
      const promptModule = await import(`./prompts/${mode}_v001`);

      // The prompt content is in the default export as a string
      const prompt = promptModule.default;

      this.prompts.set(mode, prompt);
      return prompt;
    } catch (error) {
      console.error(`Failed to load prompt for mode: ${mode}`, error);
      // Fallback to generic prompt
      return this.getGenericPrompt();
    }
  }

  async getSystemPrompt(
    mode: string,
    context: { portfolio_id: string }
  ): Promise<string> {
    try {
      // Load common instructions from TypeScript file
      const commonModule = await import('./prompts/common_instructions');
      const commonInstructions = commonModule.default;

      // Load mode-specific prompt
      const modePrompt = await this.loadPrompt(mode);

      // Combine prompts
      let fullPrompt = `${commonInstructions}\n\n---\n\n${modePrompt}`;

      // Inject portfolio_id variable
      fullPrompt = fullPrompt.replace(/{portfolio_id}/g, context.portfolio_id);

      return fullPrompt;
    } catch (error) {
      console.error('Failed to build system prompt:', error);
      // Return fallback prompt
      return this.getFallbackPrompt(context.portfolio_id);
    }
  }

  private getGenericPrompt(): string {
    return `You are a financial analyst AI assistant helping users understand their portfolio.

Be clear, accurate, and helpful. Use tools to fetch real data when needed.`;
  }

  private getFallbackPrompt(portfolioId: string): string {
    return `You are SigmaSight Agent, a portfolio analysis assistant.

## Your Role
Help users understand and analyze their portfolio investments.

## Available Tools
You have access to tools that can fetch:
- Portfolio data and positions
- Factor exposures
- Correlation matrices
- Stress test results

## Guidelines
1. Always use tools to fetch real data - never make up numbers
2. Be specific and cite actual data from tool results
3. Explain financial concepts clearly
4. Include "as of" timestamps in responses

## User Portfolio
Portfolio ID: ${portfolioId}

When users ask questions about their portfolio, use the appropriate tools to fetch current data.`;
  }
}

// Export singleton instance
export const promptManager = new PromptManager();
