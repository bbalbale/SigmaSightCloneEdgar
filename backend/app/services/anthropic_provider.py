"""
Anthropic Provider - Claude Sonnet 4 integration for portfolio analysis.

Provides AI-powered analytical reasoning using Claude Sonnet 4.
"""
import time
from typing import Dict, Any, Optional, List
import anthropic
from anthropic.types import Message, TextBlock

from app.config import settings
from app.core.logging import get_logger
from app.models.ai_insights import InsightType

logger = get_logger(__name__)


class AnthropicProvider:
    """
    Anthropic Claude Sonnet 4 provider for portfolio investigations.

    Handles:
    - Free-form investigation prompts
    - Tool calls for analytical operations
    - Cost and token tracking
    - Error handling and retries
    """

    def __init__(self):
        """Initialize Anthropic client."""
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured in .env file")

        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.ANTHROPIC_MODEL
        self.max_tokens = settings.ANTHROPIC_MAX_TOKENS
        self.temperature = settings.ANTHROPIC_TEMPERATURE
        self.timeout = settings.ANTHROPIC_TIMEOUT_SECONDS

        logger.info(f"AnthropicProvider initialized with model: {self.model}")

    async def investigate(
        self,
        context: Dict[str, Any],
        insight_type: InsightType,
        focus_area: Optional[str] = None,
        user_question: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute AI-powered investigation using Claude Sonnet 4.

        Args:
            context: Portfolio data and metrics for investigation
            insight_type: Type of analysis to perform
            focus_area: Optional specific area to focus on
            user_question: Optional user question for on-demand analysis

        Returns:
            Dict containing:
                - title: Analysis title
                - severity: Severity level
                - summary: Brief summary (2-3 sentences)
                - full_analysis: Detailed markdown analysis
                - key_findings: List of key findings
                - recommendations: List of actionable recommendations
                - data_limitations: Transparency about data quality
                - performance: Cost and token metrics
        """
        start_time = time.time()

        # Build system prompt
        system_prompt = self._build_system_prompt(insight_type, focus_area)

        # Build investigation prompt with context
        investigation_prompt = self._build_investigation_prompt(
            context=context,
            insight_type=insight_type,
            focus_area=focus_area,
            user_question=user_question,
        )

        logger.info(f"Starting Claude investigation: type={insight_type.value}, focus={focus_area}")

        try:
            # Call Claude API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": investigation_prompt,
                    }
                ],
                timeout=self.timeout,
            )

            # Extract response
            response_text = self._extract_response_text(message)

            # Parse structured response
            result = self._parse_investigation_response(
                response_text=response_text,
                insight_type=insight_type,
            )

            # Calculate performance metrics
            generation_time_ms = (time.time() - start_time) * 1000
            result["performance"] = {
                "cost_usd": self._calculate_cost(message),
                "generation_time_ms": generation_time_ms,
                "token_count_input": message.usage.input_tokens,
                "token_count_output": message.usage.output_tokens,
                "tool_calls_count": 0,  # No tools used yet
            }

            logger.info(
                f"Investigation complete: {generation_time_ms:.0f}ms, "
                f"${result['performance']['cost_usd']:.4f}, "
                f"{message.usage.input_tokens + message.usage.output_tokens} tokens"
            )

            return result

        except anthropic.APITimeoutError as e:
            logger.error(f"Anthropic API timeout: {e}")
            raise ValueError(f"Investigation timed out after {self.timeout}s")

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise ValueError(f"Investigation failed: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected error in investigation: {e}")
            raise

    def _build_system_prompt(self, insight_type: InsightType, focus_area: Optional[str]) -> str:
        """
        Build system prompt for Claude based on insight type.

        Returns conversational partner prompt with required structure.
        """
        base_prompt = """You are my trusted portfolio advisor - think of yourself as a sharp, experienced partner who's analyzing my portfolio with me.

YOUR ROLE:
- We're on the same team analyzing this portfolio together
- I trust your expertise, but I want you to explain your thinking
- Be direct, conversational, and clear - like we're talking over coffee
- Use first person: "I noticed...", "Let me show you...", "Here's what I found..."
- Be honest about risks AND opportunities

WRITING STYLE:
✅ DO:
- "I analyzed your portfolio and found three things worth discussing..."
- "Your tech exposure is 42% - here's why that matters..."
- "Let me walk you through what I'm seeing in your options positions..."
- "I'd recommend we look at X, because Y"

❌ DON'T:
- "The portfolio exhibits characteristics consistent with..."
- "It is recommended that consideration be given to..."
- "Analysis indicates that further investigation may be warranted..."
- Passive voice, hedging language, or corporate-speak

HOW TO ANALYZE:
1. Lead with what matters most - don't bury the headline
2. Show me the numbers, but explain what they mean
3. Connect the dots - help me see patterns I might miss
4. Be transparent about data limitations
5. Give me your real take, not hedged analysis

CRITICAL - RESPONSE FORMAT:
You MUST use this exact markdown structure (the headers are required for parsing):

## Title
[Write a clear, conversational title that captures your main finding]

## Summary
[Write 2-3 sentences in first person explaining what you discovered. Be direct and conversational.]

## Key Findings
[Write 3-5 bulleted findings. Each bullet should:
- Start with "I found..." or "I noticed..." or similar first-person language
- Include specific numbers and percentages
- Explain why it matters
Example:
- I found your tech exposure is 42% vs S&P 500's 28% - this creates concentration risk if tech sells off
- I noticed your portfolio delta is +850, meaning you're net long equivalent to $850K of stock exposure]

## Detailed Analysis
[Write multiple conversational paragraphs exploring your findings in depth.
Use first person. Explain your thinking. Connect different metrics.
This is where you can really dig in and show your reasoning.]

## Recommendations
[Write 3-5 bulleted recommendations. Each should:
- Be specific and actionable
- Use conversational language: "I'd recommend..." or "Consider..." or "You might want to..."
- Explain the why, not just the what
Example:
- I'd recommend trimming some of your mega-cap tech exposure - maybe take 5-10% off the table and rotate into defensive sectors
- Consider adding some put protection on your concentrated positions - your AAPL and MSFT positions are 30% combined]

## Data Limitations
[Conversationally explain any data quality issues or gaps you noticed.
Be honest: "I don't have complete data on X, so I can't give you a full picture of Y..."]

IMPORTANT:
- Use the exact header names: ## Title, ## Summary, ## Key Findings, ## Detailed Analysis, ## Recommendations, ## Data Limitations
- Write in conversational, first-person voice WITHIN each section
- Use bullet points (- ) for Key Findings and Recommendations
- Be specific with numbers and percentages
- Always include "as of [date]" for data freshness
"""

        if focus_area:
            base_prompt += f"\n\nFOCUS AREA: {focus_area}\nI want you to dig deep on this specific area and tell me what you're seeing."

        return base_prompt

    def _build_investigation_prompt(
        self,
        context: Dict[str, Any],
        insight_type: InsightType,
        focus_area: Optional[str],
        user_question: Optional[str],
    ) -> str:
        """
        Build investigation prompt with portfolio context.

        Formats context data and investigation instructions.
        """
        prompt_parts = []

        # Investigation type description
        type_descriptions = {
            InsightType.DAILY_SUMMARY: "Conduct comprehensive daily portfolio review",
            InsightType.VOLATILITY_ANALYSIS: "Analyze portfolio volatility patterns and risk factors",
            InsightType.CONCENTRATION_RISK: "Assess concentration risks and diversification",
            InsightType.HEDGE_QUALITY: "Evaluate hedge effectiveness and coverage",
            InsightType.FACTOR_EXPOSURE: "Analyze factor exposures and systematic risks",
            InsightType.STRESS_TEST_REVIEW: "Review stress test results and scenario impacts",
            InsightType.CUSTOM: "Conduct custom analysis based on user question",
        }

        prompt_parts.append(f"INVESTIGATION TYPE: {type_descriptions.get(insight_type, 'Portfolio Analysis')}")

        if user_question:
            prompt_parts.append(f"\nUSER QUESTION: {user_question}")

        # Add portfolio context
        prompt_parts.append("\n\nPORTFOLIO CONTEXT:")
        prompt_parts.append(f"Portfolio ID: {context.get('portfolio_id', 'unknown')}")

        if focus_area:
            prompt_parts.append(f"Focus Area: {focus_area}")

        # Add data sources status
        data_sources = context.get('data_sources', {})
        prompt_parts.append("\n\nDATA SOURCES STATUS:")
        for source, status in data_sources.items():
            prompt_parts.append(f"- {source}: {status}")

        # Add portfolio summary
        portfolio_summary = context.get('portfolio_summary', {})
        if portfolio_summary.get('available'):
            prompt_parts.append("\n\nPORTFOLIO DETAILS:")
            prompt_parts.append(f"Name: {portfolio_summary.get('name')}")
            prompt_parts.append(f"Currency: {portfolio_summary.get('currency')}")
            if portfolio_summary.get('equity_balance'):
                prompt_parts.append(f"Starting Equity (Day 0): ${portfolio_summary.get('equity_balance'):,.2f}")

        # Add latest snapshot data
        snapshot = context.get('snapshot')
        if snapshot:
            prompt_parts.append("\n\nLATEST SNAPSHOT:")
            prompt_parts.append(f"Date: {snapshot.get('date')}")
            if snapshot.get('equity_balance'):
                prompt_parts.append(f"Current Equity Balance: ${snapshot.get('equity_balance'):,.2f} (rolled forward with P&L)")
            if snapshot.get('total_value'):
                prompt_parts.append(f"Total Market Value: ${snapshot.get('total_value'):,.2f}")
            if snapshot.get('cash_value'):
                prompt_parts.append(f"Cash: ${snapshot.get('cash_value'):,.2f}")
            if snapshot.get('long_value'):
                prompt_parts.append(f"Long Positions: ${snapshot.get('long_value'):,.2f}")
            if snapshot.get('short_value'):
                prompt_parts.append(f"Short Positions: ${snapshot.get('short_value'):,.2f}")
            if snapshot.get('gross_exposure'):
                prompt_parts.append(f"Gross Exposure: ${snapshot.get('gross_exposure'):,.2f}")
            if snapshot.get('net_exposure'):
                prompt_parts.append(f"Net Exposure: ${snapshot.get('net_exposure'):,.2f}")
            if snapshot.get('portfolio_delta'):
                prompt_parts.append(f"Portfolio Delta: {snapshot.get('portfolio_delta'):,.2f}")
            if snapshot.get('realized_volatility_21d'):
                prompt_parts.append(f"Realized Volatility (21d): {snapshot.get('realized_volatility_21d'):.2%}")
            if snapshot.get('beta_calculated_90d'):
                prompt_parts.append(f"Market Beta (90d): {snapshot.get('beta_calculated_90d'):.2f}")
            if snapshot.get('daily_pnl'):
                prompt_parts.append(f"Daily P&L: ${snapshot.get('daily_pnl'):,.2f}")
            if snapshot.get('cumulative_pnl'):
                prompt_parts.append(f"Cumulative P&L: ${snapshot.get('cumulative_pnl'):,.2f}")

        # Add positions
        positions = context.get('positions', {})
        if positions.get('available'):
            prompt_parts.append(f"\n\nPOSITIONS ({positions.get('count', 0)} total):")
            for pos in positions.get('items', [])[:20]:  # Limit to first 20
                # Handle None values for last_price (private positions, cash equivalents)
                last_price = pos.get('last_price')
                if last_price is not None:
                    pos_line = f"- {pos.get('symbol')}: {pos.get('quantity')} @ ${last_price:.2f}"
                else:
                    pos_line = f"- {pos.get('symbol')}: {pos.get('quantity')} (no market price)"

                # Add entry price if available
                entry_price = pos.get('entry_price')
                if entry_price is not None:
                    pos_line += f" (entry: ${entry_price:.2f})"

                # Add unrealized P&L if available
                unrealized_pnl = pos.get('unrealized_pnl')
                if unrealized_pnl is not None:
                    pos_line += f" (P&L: ${unrealized_pnl:,.2f})"

                prompt_parts.append(pos_line)
            if positions.get('count', 0) > 20:
                prompt_parts.append(f"... and {positions.get('count') - 20} more positions")

        # Add risk metrics
        risk_metrics = context.get('risk_metrics', {})
        greeks = risk_metrics.get('greeks', {})
        if greeks.get('available'):
            prompt_parts.append("\n\nRISK METRICS (Greeks):")
            prompt_parts.append(f"Total Delta: {greeks.get('total_delta', 0):,.2f}")
            prompt_parts.append(f"Total Gamma: {greeks.get('total_gamma', 0):,.4f}")
            prompt_parts.append(f"Total Theta: ${greeks.get('total_theta', 0):,.2f}")
            prompt_parts.append(f"Total Vega: ${greeks.get('total_vega', 0):,.2f}")

        # Add factor exposure
        factor_exposure = context.get('factor_exposure', {})
        if factor_exposure.get('available'):
            prompt_parts.append("\n\nFACTOR EXPOSURES:")
            for factor, exposure in factor_exposure.get('factors', {}).items():
                prompt_parts.append(f"- {factor}: {exposure:.2f}")

        # Add correlations
        correlations = context.get('correlations', {})
        if correlations.get('available'):
            prompt_parts.append("\n\nCORRELATIONS:")
            if correlations.get('overall_correlation'):
                prompt_parts.append(f"Overall Correlation: {correlations.get('overall_correlation'):.2f}")
            if correlations.get('correlation_concentration_score'):
                prompt_parts.append(f"Concentration Score: {correlations.get('correlation_concentration_score'):.2f}")
            if correlations.get('effective_positions'):
                prompt_parts.append(f"Effective Positions: {correlations.get('effective_positions'):.1f}")
            if correlations.get('data_quality'):
                prompt_parts.append(f"Data Quality: {correlations.get('data_quality')}")

        # Add data quality assessment
        data_quality = context.get('data_quality', {})
        prompt_parts.append("\n\nDATA QUALITY:")
        for metric, quality in data_quality.items():
            prompt_parts.append(f"- {metric}: {quality}")

        prompt_parts.append("\n\nPlease conduct your investigation and provide comprehensive analysis following the response format specified in the system prompt.")

        return "\n".join(prompt_parts)

    def _extract_response_text(self, message: Message) -> str:
        """Extract text content from Claude message."""
        text_blocks = [block for block in message.content if isinstance(block, TextBlock)]
        if not text_blocks:
            raise ValueError("No text content in Claude response")

        return "\n".join([block.text for block in text_blocks])

    def _parse_investigation_response(
        self,
        response_text: str,
        insight_type: InsightType,
    ) -> Dict[str, Any]:
        """
        Parse Claude's investigation response into structured format.

        Extracts title, summary, findings, recommendations, and limitations.
        """
        from app.models.ai_insights import InsightSeverity

        # Simple parsing - extract sections
        # TODO: Enhance with more sophisticated parsing
        lines = response_text.split('\n')

        title = None
        summary = ""
        key_findings = []
        recommendations = []
        data_limitations = ""
        full_analysis = response_text

        current_section = None
        for line in lines:
            line = line.strip()

            if line.startswith('## Title') or (not title and line.startswith('# ')):
                current_section = 'title'
                continue
            elif line.startswith('## Summary'):
                current_section = 'summary'
                continue
            elif line.startswith('## Key Findings'):
                current_section = 'findings'
                continue
            elif line.startswith('## Recommendations'):
                current_section = 'recommendations'
                continue
            elif line.startswith('## Data Limitations'):
                current_section = 'limitations'
                continue
            elif line.startswith('## Detailed Analysis') or line.startswith('##'):
                current_section = 'other'
                continue

            # Collect content
            if current_section == 'title' and line and not title:
                title = line.strip('#').strip()
            elif current_section == 'summary' and line:
                summary += line + " "
            elif current_section == 'findings' and line.startswith(('-', '*', '•')):
                key_findings.append(line.lstrip('-*• ').strip())
            elif current_section == 'recommendations' and line.startswith(('-', '*', '•')):
                recommendations.append(line.lstrip('-*• ').strip())
            elif current_section == 'limitations' and line:
                data_limitations += line + " "

        # Determine severity based on content (simple heuristic)
        severity = InsightSeverity.INFO
        response_lower = response_text.lower()
        if any(word in response_lower for word in ['critical', 'severe', 'urgent', 'danger']):
            severity = InsightSeverity.CRITICAL
        elif any(word in response_lower for word in ['warning', 'concern', 'risk', 'issue']):
            severity = InsightSeverity.WARNING
        elif any(word in response_lower for word in ['elevated', 'moderate', 'notable']):
            severity = InsightSeverity.ELEVATED
        elif any(word in response_lower for word in ['normal', 'stable', 'healthy']):
            severity = InsightSeverity.NORMAL

        return {
            "title": title or f"{insight_type.value.replace('_', ' ').title()} Analysis",
            "severity": severity,
            "summary": summary.strip() or "Analysis complete. See details below.",
            "full_analysis": full_analysis,
            "key_findings": key_findings or ["Analysis completed"],
            "recommendations": recommendations or ["No specific recommendations at this time"],
            "data_limitations": data_limitations.strip() or "All available data used in analysis.",
        }

    def _calculate_cost(self, message: Message) -> float:
        """
        Calculate API cost based on Claude Sonnet 4 pricing.

        Pricing (as of 2024):
        - Input: $3.00 per million tokens
        - Output: $15.00 per million tokens
        """
        input_cost = (message.usage.input_tokens / 1_000_000) * 3.00
        output_cost = (message.usage.output_tokens / 1_000_000) * 15.00
        return input_cost + output_cost


# Singleton instance
anthropic_provider = AnthropicProvider()
