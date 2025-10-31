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

        Returns conversational partner prompt for natural, engaging analysis.
        """
        base_prompt = """You are my trusted portfolio advisor - think of yourself as a sharp, experienced partner who's analyzing my portfolio with me.

YOUR ROLE:
- We're on the same team analyzing this portfolio together
- I trust your expertise, but I want you to explain your thinking
- Be direct, conversational, and clear - like we're talking over coffee
- Use "I noticed...", "Let me show you...", "Here's what I found..."
- Feel free to say "This caught my attention" or "Here's what concerns me"

HOW TO ANALYZE:
1. Lead with what matters most - don't bury the headline
2. Show me the numbers, but explain what they mean
3. Connect the dots - help me see patterns I might miss
4. Be honest about risks, but also opportunities
5. Give me your real take, not hedged corporate-speak

TONE & STYLE:
✅ DO:
- "I analyzed your portfolio and found three things worth discussing..."
- "Your tech exposure is 42% - here's why that matters..."
- "Let me walk you through what I'm seeing in your options positions..."
- "I'd recommend we look at X, because Y"

❌ DON'T:
- "The portfolio exhibits characteristics consistent with..."
- "It is recommended that consideration be given to..."
- "Analysis indicates that further investigation may be warranted..."
- "Metrics suggest potential for..."

STRUCTURE YOUR RESPONSE LIKE A CONVERSATION:

**Start with the headline** - What's the one thing I need to know?

**Then show me the details:**
- Specific numbers and positions
- Why this matters
- What it means for risk/return
- Comparisons to benchmarks when relevant

**Wrap up with your take:**
- What would you do if this were your portfolio?
- Are there specific positions or metrics we should dig into?
- What's the next question I should be asking?

**Be transparent:**
- If data is incomplete, tell me straight up
- If something is uncertain, say so
- If you need more information to give a full answer, ask for it

PERSONALITY GUIDELINES:

**Show enthusiasm when appropriate:**
- "This is actually pretty interesting..."
- "Here's the cool part..."
- "I was surprised to find..."

**Be direct about concerns:**
- "This caught my attention and we should discuss it..."
- "I'm a bit concerned about..."
- "Here's what worries me..."

**Acknowledge uncertainty:**
- "I don't have complete data on X, but here's what I can tell you..."
- "The numbers suggest Y, but there's some noise in the data..."
- "I'd want to verify Z before making a strong call..."

**Ask questions:**
- "Is this intentional, or did these positions accumulate over time?"
- "What's your thinking on the tech concentration?"
- "Want me to explore this further?"

CRITICAL:
- Use first person ("I found", "I analyzed", "I recommend")
- Active voice only - never passive
- Write like you're explaining this to a smart friend who trusts your judgment
- No jargon without explanation
- No hedging language ("may", "could possibly", "might potentially")
- Be specific with numbers and percentages
- Always include "as of" timestamps for data freshness
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
        Parse Claude's conversational response into structured format.

        NEW APPROACH: Don't force rigid structure.
        Let Claude write naturally, extract what we can.
        """
        from app.models.ai_insights import InsightSeverity

        lines = response_text.split('\n')

        # Extract title - look for first bold line, H1, or use first sentence
        title = None
        for line in lines[:10]:  # Check first 10 lines
            line_stripped = line.strip()
            # Check for bold text (markdown **text**)
            if line_stripped.startswith('**') and line_stripped.endswith('**'):
                title = line_stripped.strip('*').strip()
                break
            # Check for H1 or H2
            elif line_stripped.startswith('# '):
                title = line_stripped.lstrip('# ').strip()
                break
            elif line_stripped.startswith('## ') and not title:
                title = line_stripped.lstrip('# ').strip()
                break

        if not title:
            # Generate from first sentence
            sentences = response_text.split('.')
            if sentences:
                first_sentence = sentences[0].strip()
                title = first_sentence[:80] + ('...' if len(first_sentence) > 80 else '')
            else:
                title = f"{insight_type.value.replace('_', ' ').title()} Analysis"

        # Extract key findings - look for bulleted lists
        key_findings = []
        in_bullets = False
        for line in lines:
            line_stripped = line.strip()
            # Check for bullet points
            if line_stripped.startswith(('- ', '• ', '* ')):
                finding = line_stripped.lstrip('-•* ').strip()
                # Only add substantial findings (more than 10 chars)
                if finding and len(finding) > 10:
                    key_findings.append(finding)
                    in_bullets = True
            elif in_bullets and not line_stripped:
                # Empty line ends bullet section
                in_bullets = False
            # Also check for numbered lists
            elif line_stripped and len(line_stripped) > 2:
                # Check if starts with number followed by period or parenthesis
                if line_stripped[0].isdigit() and line_stripped[1] in '.):':
                    finding = line_stripped.lstrip('0123456789.): ').strip()
                    if finding and len(finding) > 10:
                        key_findings.append(finding)

        # Extract recommendations - look for recommendation-related sections
        recommendations = []
        recommendation_section = False
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            # Detect recommendation section
            if any(keyword in line_lower for keyword in [
                'recommend', "here's what", 'next steps', 'what to do',
                'my take', 'you should', "i'd suggest", 'consider'
            ]):
                recommendation_section = True

            # Extract recommendations from bullets or numbered lists
            if recommendation_section and line_stripped.startswith(('- ', '• ', '* ')):
                rec = line_stripped.lstrip('-•* ').strip()
                if rec and len(rec) > 10:
                    recommendations.append(rec)
            elif recommendation_section and line_stripped and len(line_stripped) > 2:
                if line_stripped[0].isdigit() and line_stripped[1] in '.):':
                    rec = line_stripped.lstrip('0123456789.): ').strip()
                    if rec and len(rec) > 10:
                        recommendations.append(rec)

            # Stop at next major section
            if recommendation_section and line_stripped.startswith('##') and i > 0:
                if not any(keyword in line_lower for keyword in ['recommend', 'next', 'action']):
                    recommendation_section = False

        # Create natural summary - use first paragraph
        paragraphs = [p.strip() for p in response_text.split('\n\n') if len(p.strip()) > 50]
        summary = paragraphs[0] if paragraphs else "Analysis complete."

        # Limit summary length
        if len(summary) > 500:
            summary = summary[:497] + "..."

        # Auto-detect severity from conversational tone
        severity = self._detect_severity_from_tone(response_text)

        return {
            "title": title,
            "severity": severity,
            "summary": summary,
            "full_analysis": response_text,  # Keep the full conversational response
            "key_findings": key_findings[:5] if key_findings else ["Analysis completed"],
            "recommendations": recommendations[:5] if recommendations else ["No specific recommendations at this time"],
            "data_limitations": "",  # Claude will mention data quality naturally in the response
        }

    def _detect_severity_from_tone(self, text: str) -> 'InsightSeverity':
        """
        Detect severity from conversational language and tone.

        Analyzes the text for conversational indicators of severity level.
        """
        from app.models.ai_insights import InsightSeverity

        text_lower = text.lower()

        # Critical indicators - urgent, serious language
        critical_phrases = [
            'urgent', 'critical', 'serious risk', 'major concern',
            'significantly exposed', 'immediate attention', 'alarming',
            'dangerous', 'very concerned', 'red flag'
        ]
        if any(phrase in text_lower for phrase in critical_phrases):
            return InsightSeverity.CRITICAL

        # Warning indicators - concern and risk language
        warning_phrases = [
            'concerned', 'worth discussing', 'should talk about',
            'higher than', 'overweight', 'concentration risk',
            'worries me', 'caught my attention', 'be careful',
            'risk here', 'exposure is high', 'watch out for'
        ]
        if any(phrase in text_lower for phrase in warning_phrases):
            return InsightSeverity.WARNING

        # Elevated indicators - notable but not urgent
        elevated_phrases = [
            'notable', 'worth noting', 'keep an eye on',
            'slightly elevated', 'moderately', 'interesting',
            'something to consider', 'might want to'
        ]
        if any(phrase in text_lower for phrase in elevated_phrases):
            return InsightSeverity.ELEVATED

        # Positive/normal indicators - healthy portfolio language
        normal_phrases = [
            'looking good', 'well-positioned', 'balanced',
            'healthy', 'solid', 'reasonable', 'appropriate',
            'in line with', 'on track'
        ]
        if any(phrase in text_lower for phrase in normal_phrases):
            return InsightSeverity.NORMAL

        # Default to INFO if no strong signals
        return InsightSeverity.INFO

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
