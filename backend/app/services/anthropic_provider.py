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

        Returns comprehensive instructions for analytical reasoning.
        """
        base_prompt = """You are a senior portfolio analyst conducting comprehensive risk analysis.

INVESTIGATION APPROACH:
1. SCAN all provided metrics - identify anything noteworthy or unusual
2. FORM HYPOTHESES about root causes of patterns or anomalies
3. TEST HYPOTHESES by connecting related data points
4. COMPARE to common portfolio characteristics and strategies
5. CONNECT disparate metrics to reveal hidden risks or opportunities
6. SYNTHESIZE into clear, actionable insights

DATA QUALITY:
- Some calculations may be incomplete or unreliable (marked in context)
- Focus analysis on reliable data
- Be transparent about data limitations
- Distinguish between proven findings and areas needing more data

OUTPUT REQUIREMENTS:
- Think like an analyst doing due diligence, not a chatbot
- Be specific with numbers and percentages
- Provide actionable recommendations
- Use clear, professional language
- Structure your analysis logically

RESPONSE FORMAT:
Provide your analysis in the following structure:

## Title
[Concise title for the analysis]

## Summary
[2-3 sentence executive summary]

## Key Findings
[Bulleted list of 3-5 key findings with specific numbers]

## Detailed Analysis
[Comprehensive analysis with multiple paragraphs exploring the findings]

## Recommendations
[Bulleted list of 3-5 specific, actionable recommendations]

## Data Limitations
[Transparent discussion of any data quality issues or gaps]
"""

        if focus_area:
            base_prompt += f"\n\nFOCUS AREA: {focus_area}\nProvide extra depth on this specific area."

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
                prompt_parts.append(f"Equity Balance: ${portfolio_summary.get('equity_balance'):,.2f}")

        # Add latest snapshot data
        snapshot = context.get('snapshot')
        if snapshot:
            prompt_parts.append("\n\nLATEST SNAPSHOT:")
            prompt_parts.append(f"Date: {snapshot.get('date')}")
            if snapshot.get('total_value'):
                prompt_parts.append(f"Total Value: ${snapshot.get('total_value'):,.2f}")
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

        # Add positions
        positions = context.get('positions', {})
        if positions.get('available'):
            prompt_parts.append(f"\n\nPOSITIONS ({positions.get('count', 0)} total):")
            for pos in positions.get('items', [])[:20]:  # Limit to first 20
                pos_line = f"- {pos.get('symbol')}: {pos.get('quantity')} @ ${pos.get('last_price', 0):.2f}"
                if pos.get('entry_price'):
                    pos_line += f" (entry: ${pos.get('entry_price'):.2f})"
                if pos.get('unrealized_pnl'):
                    pos_line += f" (P&L: ${pos.get('unrealized_pnl'):,.2f})"
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
