"""
Configuration settings for SigmaSight Backend
"""
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Application settings
    APP_NAME: str = "SigmaSight Backend"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database settings
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    
    # Market data API keys
    POLYGON_API_KEY: str = Field(..., env="POLYGON_API_KEY")
    POLYGON_PLAN: str = Field(default="free", env="POLYGON_PLAN")  # free, starter, developer, advanced
    FRED_API_KEY: str = Field(default="", env="FRED_API_KEY")  # Optional for Treasury data
    
    # New market data providers (Section 1.4.9)
    FMP_API_KEY: str = Field(default="", env="FMP_API_KEY")  # Financial Modeling Prep
    TRADEFEEDS_API_KEY: str = Field(default="", env="TRADEFEEDS_API_KEY")  # TradeFeeds backup

    # YFinance settings (no API key required)
    USE_YFINANCE: bool = Field(default=True, env="USE_YFINANCE")  # Primary provider for stocks
    YFINANCE_RATE_LIMIT: float = Field(default=1.0, env="YFINANCE_RATE_LIMIT")  # Seconds between requests
    YFINANCE_TIMEOUT_SECONDS: int = Field(default=30, env="YFINANCE_TIMEOUT_SECONDS")
    YFINANCE_MAX_RETRIES: int = Field(default=3, env="YFINANCE_MAX_RETRIES")

    # Provider selection flags
    USE_FMP_FOR_STOCKS: bool = Field(default=False, env="USE_FMP_FOR_STOCKS")  # Now secondary to yfinance
    USE_FMP_FOR_FUNDS: bool = Field(default=True, env="USE_FMP_FOR_FUNDS")
    USE_POLYGON_FOR_OPTIONS: bool = Field(default=True, env="USE_POLYGON_FOR_OPTIONS")  # Always true
    
    # Provider-specific settings
    FMP_TIMEOUT_SECONDS: int = Field(default=30, env="FMP_TIMEOUT_SECONDS")
    FMP_MAX_RETRIES: int = Field(default=3, env="FMP_MAX_RETRIES")
    TRADEFEEDS_TIMEOUT_SECONDS: int = Field(default=30, env="TRADEFEEDS_TIMEOUT_SECONDS")
    TRADEFEEDS_MAX_RETRIES: int = Field(default=3, env="TRADEFEEDS_MAX_RETRIES")
    TRADEFEEDS_RATE_LIMIT: int = Field(default=30, env="TRADEFEEDS_RATE_LIMIT")  # calls per minute
    
    
    # OpenAI Agent settings
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    OPENAI_ORG_ID: str = Field(default="", env="OPENAI_ORG_ID")  # Optional
    # GPT-5 models confirmed to exist - see https://platform.openai.com/docs/models/gpt-5-mini
    MODEL_DEFAULT: str = Field(default="gpt-5-mini-2025-08-07", env="MODEL_DEFAULT")
    MODEL_FALLBACK: str = Field(default="gpt-5-nano-2025-08-07", env="MODEL_FALLBACK")
    AGENT_CACHE_TTL: int = Field(default=600, env="AGENT_CACHE_TTL")
    SSE_HEARTBEAT_INTERVAL_MS: int = Field(default=15000, env="SSE_HEARTBEAT_INTERVAL_MS")
    # SSE streaming retry/fallback settings
    SSE_MAX_STREAM_RETRIES: int = Field(default=2, env="SSE_MAX_STREAM_RETRIES")
    SSE_RETRY_BACKOFF_BASE_MS: int = Field(default=500, env="SSE_RETRY_BACKOFF_BASE_MS")
    SSE_RETRY_BACKOFF_MULTIPLIER: float = Field(default=2.0, env="SSE_RETRY_BACKOFF_MULTIPLIER")
    SSE_RETRY_BACKOFF_MAX_MS: int = Field(default=5000, env="SSE_RETRY_BACKOFF_MAX_MS")
    SSE_RETRY_JITTER_MS: int = Field(default=250, env="SSE_RETRY_JITTER_MS")
    SSE_USE_MODEL_FALLBACK: bool = Field(default=True, env="SSE_USE_MODEL_FALLBACK")
    
    # OpenAI Responses API configuration (formerly Chat configuration)
    # Renamed to be API-agnostic as per Phase 5.8.4
    OPENAI_MAX_COMPLETION_TOKENS: int = Field(default=4000, env="OPENAI_MAX_COMPLETION_TOKENS", 
                                              description="Max completion tokens for OpenAI Responses API")
    OPENAI_TIMEOUT_SECONDS: int = Field(default=60, env="OPENAI_TIMEOUT_SECONDS",
                                        description="Timeout for OpenAI API requests")
    OPENAI_MAX_TOOLS: int = Field(default=10, env="OPENAI_MAX_TOOLS",
                                  description="Maximum number of tools per Responses API call")
    OPENAI_RATE_LIMIT_PER_MINUTE: int = Field(default=10, env="OPENAI_RATE_LIMIT_PER_MINUTE",
                                              description="Rate limit for OpenAI API calls")
    
    # Tool response truncation limits
    TOOL_RESPONSE_MAX_CHARS: int = Field(default=10000, env="TOOL_RESPONSE_MAX_CHARS",
                                         description="Maximum characters for tool responses sent to LLM (default: 10000 supports ~50 positions)")
    TOOL_RESPONSE_PORTFOLIO_MAX_CHARS: int = Field(default=15000, env="TOOL_RESPONSE_PORTFOLIO_MAX_CHARS",
                                                   description="Maximum characters for portfolio-specific tools (default: 15000 for complex portfolios)")
    TOOL_RESPONSE_TRUNCATE_ENABLED: bool = Field(default=True, env="TOOL_RESPONSE_TRUNCATE_ENABLED",
                                                 description="Enable tool response truncation (set False to disable all truncation)")
    
    # Legacy configuration for backward compatibility (Phase 5.8.4 transition)
    CHAT_MAX_TOKENS: int = Field(default=4000, env="CHAT_MAX_TOKENS", 
                                 description="LEGACY: Use OPENAI_MAX_COMPLETION_TOKENS instead")
    CHAT_TIMEOUT_SECONDS: int = Field(default=300, env="CHAT_TIMEOUT_SECONDS",
                                      description="LEGACY: Use OPENAI_TIMEOUT_SECONDS instead") 
    CHAT_RATE_LIMIT_PER_MINUTE: int = Field(default=10, env="CHAT_RATE_LIMIT_PER_MINUTE",
                                            description="LEGACY: Use OPENAI_RATE_LIMIT_PER_MINUTE instead")
    
    # Agent feature flags
    SSE_EMIT_MESSAGE_CREATED: bool = Field(default=True, env="SSE_EMIT_MESSAGE_CREATED")
    API_MESSAGES_ENABLED: bool = Field(default=False, env="API_MESSAGES_ENABLED")

    # Anthropic settings for Analytical Reasoning Layer
    ANTHROPIC_API_KEY: str = Field(default="", env="ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL: str = Field(default="claude-sonnet-4-20250514", env="ANTHROPIC_MODEL")  # Latest Claude Sonnet 4
    ANTHROPIC_MAX_TOKENS: int = Field(default=8000, env="ANTHROPIC_MAX_TOKENS")
    ANTHROPIC_TEMPERATURE: float = Field(default=0.7, env="ANTHROPIC_TEMPERATURE")
    ANTHROPIC_TIMEOUT_SECONDS: int = Field(default=120, env="ANTHROPIC_TIMEOUT_SECONDS")
    
    # JWT settings
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",  # React dev server
        "http://localhost:3005",  # Next.js dev server
        "http://localhost:5173",  # Vite dev server
        "https://sigmasight-frontend.vercel.app",  # Production frontend
    ]
    
    # Batch processing settings
    BATCH_PROCESSING_ENABLED: bool = True
    MARKET_DATA_UPDATE_INTERVAL: int = 3600  # 1 hour in seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
