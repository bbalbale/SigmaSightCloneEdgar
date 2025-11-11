--
-- PostgreSQL database dump
--

\restrict ymBVC8A5dfCfYbx5LNywuXgxN1dB0wkzU4yfoHIKX4rPHvtaEPFildHI6NBRiTB

-- Dumped from database version 15.14 (Debian 15.14-1.pgdg13+1)
-- Dumped by pg_dump version 15.14 (Debian 15.14-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: alertpriority; Type: TYPE; Schema: public; Owner: sigmasight
--

CREATE TYPE public.alertpriority AS ENUM (
    'LOW',
    'MEDIUM',
    'HIGH',
    'CRITICAL'
);


ALTER TYPE public.alertpriority OWNER TO sigmasight;

--
-- Name: alertstatus; Type: TYPE; Schema: public; Owner: sigmasight
--

CREATE TYPE public.alertstatus AS ENUM (
    'ACTIVE',
    'DISMISSED',
    'RESOLVED'
);


ALTER TYPE public.alertstatus OWNER TO sigmasight;

--
-- Name: alerttype; Type: TYPE; Schema: public; Owner: sigmasight
--

CREATE TYPE public.alerttype AS ENUM (
    'EXPIRATION_RISK',
    'CONCENTRATION',
    'RISK_LIMIT',
    'POSITION_CHANGE',
    'MARKET_MOVE',
    'CORRELATION'
);


ALTER TYPE public.alerttype OWNER TO sigmasight;

--
-- Name: insight_severity; Type: TYPE; Schema: public; Owner: sigmasight
--

CREATE TYPE public.insight_severity AS ENUM (
    'info',
    'normal',
    'elevated',
    'warning',
    'critical'
);


ALTER TYPE public.insight_severity OWNER TO sigmasight;

--
-- Name: insight_type; Type: TYPE; Schema: public; Owner: sigmasight
--

CREATE TYPE public.insight_type AS ENUM (
    'daily_summary',
    'volatility_analysis',
    'concentration_risk',
    'hedge_quality',
    'factor_exposure',
    'stress_test_review',
    'custom'
);


ALTER TYPE public.insight_type OWNER TO sigmasight;

--
-- Name: positiontype; Type: TYPE; Schema: public; Owner: sigmasight
--

CREATE TYPE public.positiontype AS ENUM (
    'LC',
    'LP',
    'SC',
    'SP',
    'LONG',
    'SHORT'
);


ALTER TYPE public.positiontype OWNER TO sigmasight;

--
-- Name: tagtype; Type: TYPE; Schema: public; Owner: sigmasight
--

CREATE TYPE public.tagtype AS ENUM (
    'REGULAR',
    'STRATEGY'
);


ALTER TYPE public.tagtype OWNER TO sigmasight;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agent_conversations; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.agent_conversations (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    mode character varying(50) NOT NULL,
    provider character varying(32) NOT NULL,
    provider_thread_id character varying(255),
    provider_run_id character varying(255),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    metadata jsonb NOT NULL
);


ALTER TABLE public.agent_conversations OWNER TO sigmasight;

--
-- Name: agent_messages; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.agent_messages (
    id uuid NOT NULL,
    conversation_id uuid NOT NULL,
    role character varying(50) NOT NULL,
    content text,
    tool_calls jsonb NOT NULL,
    first_token_ms integer,
    latency_ms integer,
    prompt_tokens integer,
    completion_tokens integer,
    total_tokens integer,
    provider_message_id character varying(255),
    created_at timestamp with time zone NOT NULL,
    error jsonb
);


ALTER TABLE public.agent_messages OWNER TO sigmasight;

--
-- Name: agent_user_preferences; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.agent_user_preferences (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    default_mode character varying(50) NOT NULL,
    preferred_model character varying(100),
    code_interpreter_enabled boolean NOT NULL,
    tool_calls_enabled boolean NOT NULL,
    streaming_enabled boolean NOT NULL,
    user_context character varying(2000),
    settings jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.agent_user_preferences OWNER TO sigmasight;

--
-- Name: ai_insight_templates; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.ai_insight_templates (
    id uuid NOT NULL,
    insight_type public.insight_type NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    version character varying(20) NOT NULL,
    system_prompt text NOT NULL,
    investigation_prompt text NOT NULL,
    model_preference character varying(50),
    max_tokens numeric(6,0),
    temperature numeric(3,2),
    required_tools json,
    optional_tools json,
    active boolean NOT NULL,
    avg_quality_score numeric(3,2),
    usage_count numeric(10,0),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    deprecated_at timestamp without time zone
);


ALTER TABLE public.ai_insight_templates OWNER TO sigmasight;

--
-- Name: ai_insights; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.ai_insights (
    id uuid NOT NULL,
    portfolio_id uuid NOT NULL,
    insight_type public.insight_type NOT NULL,
    title character varying(200) NOT NULL,
    severity public.insight_severity NOT NULL,
    summary text NOT NULL,
    full_analysis text,
    key_findings json,
    recommendations json,
    data_limitations text,
    context_data json,
    data_quality json,
    focus_area character varying(100),
    user_question text,
    model_used character varying(50) NOT NULL,
    provider character varying(20) NOT NULL,
    prompt_version character varying(20),
    cost_usd numeric(10,6),
    generation_time_ms numeric(10,2),
    token_count_input numeric(10,0),
    token_count_output numeric(10,0),
    tool_calls_count numeric(3,0),
    cache_hit boolean,
    cache_source_id uuid,
    cache_key character varying(64),
    user_rating numeric(2,1),
    user_feedback text,
    viewed boolean,
    dismissed boolean,
    created_at timestamp without time zone NOT NULL,
    expires_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.ai_insights OWNER TO sigmasight;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO sigmasight;

--
-- Name: batch_job_schedules; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.batch_job_schedules (
    id uuid NOT NULL,
    job_name character varying(100) NOT NULL,
    job_type character varying(50) NOT NULL,
    cron_expression character varying(100) NOT NULL,
    is_active boolean NOT NULL,
    description character varying(500),
    timeout_seconds integer NOT NULL,
    retry_count integer NOT NULL,
    retry_delay_seconds integer NOT NULL,
    last_run_at timestamp with time zone,
    next_run_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.batch_job_schedules OWNER TO sigmasight;

--
-- Name: batch_jobs; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.batch_jobs (
    id uuid NOT NULL,
    job_name character varying(100) NOT NULL,
    job_type character varying(50) NOT NULL,
    status character varying(20) NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    duration_seconds integer,
    records_processed integer,
    error_message character varying(1000),
    job_metadata json,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.batch_jobs OWNER TO sigmasight;

--
-- Name: batch_run_tracking; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.batch_run_tracking (
    id uuid NOT NULL,
    run_date date NOT NULL,
    phase_1_status character varying(20),
    phase_2_status character varying(20),
    phase_3_status character varying(20),
    phase_1_duration_seconds integer,
    phase_2_duration_seconds integer,
    phase_3_duration_seconds integer,
    portfolios_processed integer,
    symbols_fetched integer,
    data_coverage_pct numeric(5,2),
    error_message text,
    completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.batch_run_tracking OWNER TO sigmasight;

--
-- Name: benchmarks_sector_weights; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.benchmarks_sector_weights (
    id uuid NOT NULL,
    benchmark_code character varying(32) NOT NULL,
    asof_date date NOT NULL,
    sector character varying(64) NOT NULL,
    weight numeric(12,6) NOT NULL,
    market_cap numeric(20,2),
    num_constituents integer,
    data_source character varying(32) DEFAULT 'FMP'::character varying NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.benchmarks_sector_weights OWNER TO sigmasight;

--
-- Name: company_profiles; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.company_profiles (
    symbol character varying(20) NOT NULL,
    company_name character varying(200),
    sector character varying(100),
    industry character varying(100),
    exchange character varying(50),
    country character varying(50),
    market_cap numeric(18,2),
    description character varying(1000),
    is_etf boolean,
    is_fund boolean,
    ceo character varying(100),
    employees integer,
    website character varying(200),
    pe_ratio numeric(10,2),
    forward_pe numeric(10,2),
    dividend_yield numeric(8,6),
    beta numeric(8,4),
    week_52_high numeric(12,4),
    week_52_low numeric(12,4),
    target_mean_price numeric(12,4),
    target_high_price numeric(12,4),
    target_low_price numeric(12,4),
    number_of_analyst_opinions integer,
    recommendation_mean numeric(3,2),
    recommendation_key character varying(20),
    forward_eps numeric(12,4),
    earnings_growth numeric(8,6),
    revenue_growth numeric(8,6),
    earnings_quarterly_growth numeric(8,6),
    profit_margins numeric(8,6),
    operating_margins numeric(8,6),
    gross_margins numeric(8,6),
    return_on_assets numeric(8,6),
    return_on_equity numeric(8,6),
    total_revenue numeric(18,2),
    current_year_revenue_avg numeric(18,2),
    current_year_revenue_low numeric(18,2),
    current_year_revenue_high numeric(18,2),
    current_year_revenue_growth numeric(8,6),
    current_year_earnings_avg numeric(12,4),
    current_year_earnings_low numeric(12,4),
    current_year_earnings_high numeric(12,4),
    current_year_end_date date,
    next_year_revenue_avg numeric(18,2),
    next_year_revenue_low numeric(18,2),
    next_year_revenue_high numeric(18,2),
    next_year_revenue_growth numeric(8,6),
    next_year_earnings_avg numeric(12,4),
    next_year_earnings_low numeric(12,4),
    next_year_earnings_high numeric(12,4),
    next_year_end_date date,
    data_source character varying(50) NOT NULL,
    last_updated timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.company_profiles OWNER TO sigmasight;

--
-- Name: correlation_calculations; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.correlation_calculations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    portfolio_id uuid NOT NULL,
    duration_days integer NOT NULL,
    calculation_date timestamp with time zone NOT NULL,
    overall_correlation numeric(8,6) NOT NULL,
    correlation_concentration_score numeric(8,6) NOT NULL,
    effective_positions numeric(8,2) NOT NULL,
    data_quality character varying(20) NOT NULL,
    min_position_value numeric(18,4),
    min_portfolio_weight numeric(8,6),
    filter_mode character varying(20),
    correlation_threshold numeric(8,6),
    positions_included integer NOT NULL,
    positions_excluded integer NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.correlation_calculations OWNER TO sigmasight;

--
-- Name: correlation_cluster_positions; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.correlation_cluster_positions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    cluster_id uuid NOT NULL,
    position_id uuid NOT NULL,
    symbol character varying(20) NOT NULL,
    value numeric(18,4) NOT NULL,
    portfolio_percentage numeric(8,6) NOT NULL,
    correlation_to_cluster numeric(8,6) NOT NULL
);


ALTER TABLE public.correlation_cluster_positions OWNER TO sigmasight;

--
-- Name: correlation_clusters; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.correlation_clusters (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    correlation_calculation_id uuid NOT NULL,
    cluster_number integer NOT NULL,
    nickname character varying(100) NOT NULL,
    avg_correlation numeric(8,6) NOT NULL,
    total_value numeric(18,4) NOT NULL,
    portfolio_percentage numeric(8,6) NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.correlation_clusters OWNER TO sigmasight;

--
-- Name: export_history; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.export_history (
    id uuid NOT NULL,
    user_id uuid,
    export_type character varying(50) NOT NULL,
    export_format character varying(10) NOT NULL,
    file_name character varying(255) NOT NULL,
    file_size_bytes integer,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_export_history_export_format_check CHECK (((export_format)::text = ANY ((ARRAY['csv'::character varying, 'json'::character varying, 'fix'::character varying])::text[]))),
    CONSTRAINT ck_export_history_export_type_check CHECK (((export_type)::text = ANY ((ARRAY['portfolio'::character varying, 'trades'::character varying, 'modeling_session'::character varying])::text[])))
);


ALTER TABLE public.export_history OWNER TO sigmasight;

--
-- Name: COLUMN export_history.export_type; Type: COMMENT; Schema: public; Owner: sigmasight
--

COMMENT ON COLUMN public.export_history.export_type IS 'Type of export: portfolio, trades, modeling_session';


--
-- Name: COLUMN export_history.export_format; Type: COMMENT; Schema: public; Owner: sigmasight
--

COMMENT ON COLUMN public.export_history.export_format IS 'Format: csv, json, fix';


--
-- Name: factor_correlations; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.factor_correlations (
    id uuid NOT NULL,
    factor_1_id uuid NOT NULL,
    factor_2_id uuid NOT NULL,
    correlation numeric(8,6) NOT NULL,
    calculation_date date NOT NULL,
    lookback_days integer NOT NULL,
    decay_factor numeric(4,3) NOT NULL,
    data_points integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.factor_correlations OWNER TO sigmasight;

--
-- Name: factor_definitions; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.factor_definitions (
    id uuid NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(500),
    factor_type character varying(20) NOT NULL,
    calculation_method character varying(50),
    etf_proxy character varying(10),
    display_order integer NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.factor_definitions OWNER TO sigmasight;

--
-- Name: factor_exposures; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.factor_exposures (
    id uuid NOT NULL,
    portfolio_id uuid NOT NULL,
    factor_id uuid NOT NULL,
    calculation_date date NOT NULL,
    exposure_value numeric(12,6) NOT NULL,
    exposure_dollar numeric(16,2),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.factor_exposures OWNER TO sigmasight;

--
-- Name: fund_holdings; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.fund_holdings (
    id uuid NOT NULL,
    fund_symbol character varying(20) NOT NULL,
    holding_symbol character varying(20) NOT NULL,
    holding_name character varying(200),
    weight numeric(8,6) NOT NULL,
    shares integer,
    market_value numeric(16,2),
    data_source character varying(50) NOT NULL,
    last_updated date NOT NULL,
    data_quality character varying(20) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.fund_holdings OWNER TO sigmasight;

--
-- Name: market_data_cache; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.market_data_cache (
    id uuid NOT NULL,
    symbol character varying(20) NOT NULL,
    date date NOT NULL,
    open numeric(12,4),
    high numeric(12,4),
    low numeric(12,4),
    close numeric(12,4) NOT NULL,
    volume integer,
    sector character varying(100),
    industry character varying(100),
    exchange character varying(20),
    country character varying(10),
    market_cap numeric(18,2),
    data_source character varying(50) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.market_data_cache OWNER TO sigmasight;

--
-- Name: market_risk_scenarios; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.market_risk_scenarios (
    id uuid NOT NULL,
    portfolio_id uuid NOT NULL,
    scenario_type character varying(50) NOT NULL,
    scenario_value numeric(8,6) NOT NULL,
    predicted_pnl numeric(16,2) NOT NULL,
    calculation_date date NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.market_risk_scenarios OWNER TO sigmasight;

--
-- Name: modeling_session_snapshots; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.modeling_session_snapshots (
    id uuid NOT NULL,
    session_id character varying(50) NOT NULL,
    user_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    status character varying(20) NOT NULL,
    base_portfolio_snapshot json NOT NULL,
    modified_portfolio_snapshot json,
    changes json,
    impact_summary json,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone,
    CONSTRAINT ck_modeling_session_snapshots_modeling_session_status_check CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'completed'::character varying, 'cancelled'::character varying])::text[])))
);


ALTER TABLE public.modeling_session_snapshots OWNER TO sigmasight;

--
-- Name: COLUMN modeling_session_snapshots.base_portfolio_snapshot; Type: COMMENT; Schema: public; Owner: sigmasight
--

COMMENT ON COLUMN public.modeling_session_snapshots.base_portfolio_snapshot IS 'Original portfolio state before modifications';


--
-- Name: COLUMN modeling_session_snapshots.modified_portfolio_snapshot; Type: COMMENT; Schema: public; Owner: sigmasight
--

COMMENT ON COLUMN public.modeling_session_snapshots.modified_portfolio_snapshot IS 'Portfolio state after applying changes';


--
-- Name: COLUMN modeling_session_snapshots.changes; Type: COMMENT; Schema: public; Owner: sigmasight
--

COMMENT ON COLUMN public.modeling_session_snapshots.changes IS 'Array of position changes (add/remove/modify)';


--
-- Name: COLUMN modeling_session_snapshots.impact_summary; Type: COMMENT; Schema: public; Owner: sigmasight
--

COMMENT ON COLUMN public.modeling_session_snapshots.impact_summary IS 'Summary of impacts on risk, exposure, P&L';


--
-- Name: pairwise_correlations; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.pairwise_correlations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    correlation_calculation_id uuid NOT NULL,
    symbol_1 character varying(20) NOT NULL,
    symbol_2 character varying(20) NOT NULL,
    correlation_value numeric(8,6) NOT NULL,
    data_points integer NOT NULL,
    statistical_significance numeric(8,6)
);


ALTER TABLE public.pairwise_correlations OWNER TO sigmasight;

--
-- Name: portfolio_snapshots; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.portfolio_snapshots (
    id uuid NOT NULL,
    portfolio_id uuid NOT NULL,
    snapshot_date date NOT NULL,
    total_value numeric(16,2) NOT NULL,
    cash_value numeric(16,2) NOT NULL,
    long_value numeric(16,2) NOT NULL,
    short_value numeric(16,2) NOT NULL,
    gross_exposure numeric(16,2) NOT NULL,
    net_exposure numeric(16,2) NOT NULL,
    daily_pnl numeric(16,2),
    daily_return numeric(8,6),
    cumulative_pnl numeric(16,2),
    portfolio_delta numeric(12,2),
    portfolio_gamma numeric(12,2),
    portfolio_theta numeric(12,2),
    portfolio_vega numeric(12,2),
    num_positions integer NOT NULL,
    num_long_positions integer NOT NULL,
    num_short_positions integer NOT NULL,
    equity_balance numeric(16,2),
    realized_volatility_21d numeric(10,4),
    realized_volatility_63d numeric(10,4),
    expected_volatility_21d numeric(10,4),
    volatility_trend character varying(20),
    volatility_percentile numeric(10,4),
    beta_calculated_90d numeric(10,4),
    beta_calculated_90d_r_squared numeric(10,4),
    beta_calculated_90d_observations integer,
    beta_provider_1y numeric(10,4),
    beta_portfolio_regression numeric(10,4),
    sector_exposure json,
    hhi numeric(10,4),
    effective_num_positions numeric(10,2),
    top_3_concentration numeric(10,4),
    top_10_concentration numeric(10,4),
    target_price_return_eoy numeric(8,4),
    target_price_return_next_year numeric(8,4),
    target_price_downside_return numeric(8,4),
    target_price_upside_eoy_dollars numeric(16,2),
    target_price_upside_next_year_dollars numeric(16,2),
    target_price_downside_dollars numeric(16,2),
    target_price_coverage_pct numeric(8,4),
    target_price_positions_count integer,
    target_price_total_positions integer,
    target_price_last_updated timestamp with time zone,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.portfolio_snapshots OWNER TO sigmasight;

--
-- Name: portfolio_target_prices; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.portfolio_target_prices (
    id uuid NOT NULL,
    portfolio_id uuid NOT NULL,
    position_id uuid,
    symbol character varying(20) NOT NULL,
    position_type character varying(10),
    target_price_eoy numeric(12,4),
    target_price_next_year numeric(12,4),
    downside_target_price numeric(12,4),
    current_price numeric(12,4) NOT NULL,
    current_implied_vol numeric(8,4),
    expected_return_eoy numeric(8,4),
    expected_return_next_year numeric(8,4),
    downside_return numeric(8,4),
    target_upside_eoy_value numeric(16,2),
    target_upside_next_year_value numeric(16,2),
    target_downside_value numeric(16,2),
    position_weight numeric(8,4),
    contribution_to_portfolio_return numeric(8,4),
    contribution_to_portfolio_risk numeric(8,4),
    price_updated_at timestamp with time zone,
    analyst_notes text,
    data_source character varying(50),
    created_by uuid,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.portfolio_target_prices OWNER TO sigmasight;

--
-- Name: portfolios; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.portfolios (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description character varying(1000),
    currency character varying(3) NOT NULL,
    equity_balance numeric(16,2),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone
);


ALTER TABLE public.portfolios OWNER TO sigmasight;

--
-- Name: position_factor_exposures; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.position_factor_exposures (
    id uuid NOT NULL,
    position_id uuid NOT NULL,
    factor_id uuid NOT NULL,
    calculation_date date NOT NULL,
    exposure_value numeric(12,6) NOT NULL,
    quality_flag character varying(20),
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.position_factor_exposures OWNER TO sigmasight;

--
-- Name: position_greeks; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.position_greeks (
    id uuid NOT NULL,
    position_id uuid NOT NULL,
    calculation_date date NOT NULL,
    delta numeric(12,6),
    gamma numeric(12,6),
    theta numeric(12,4),
    vega numeric(12,4),
    rho numeric(12,4),
    delta_dollars numeric(16,2),
    gamma_dollars numeric(16,2),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.position_greeks OWNER TO sigmasight;

--
-- Name: position_interest_rate_betas; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.position_interest_rate_betas (
    id uuid NOT NULL,
    portfolio_id uuid NOT NULL,
    position_id uuid NOT NULL,
    ir_beta numeric(8,6) NOT NULL,
    r_squared numeric(6,4),
    calculation_date date NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.position_interest_rate_betas OWNER TO sigmasight;

--
-- Name: position_market_betas; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.position_market_betas (
    id uuid NOT NULL,
    portfolio_id uuid NOT NULL,
    position_id uuid NOT NULL,
    calc_date date NOT NULL,
    beta numeric(12,6) NOT NULL,
    alpha numeric(12,6),
    r_squared numeric(12,6),
    std_error numeric(12,6),
    p_value numeric(12,6),
    observations integer NOT NULL,
    window_days integer DEFAULT 90 NOT NULL,
    method character varying(32) DEFAULT 'OLS_SIMPLE'::character varying NOT NULL,
    market_index character varying(16) DEFAULT 'SPY'::character varying NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.position_market_betas OWNER TO sigmasight;

--
-- Name: position_tags; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.position_tags (
    id uuid NOT NULL,
    position_id uuid NOT NULL,
    tag_id uuid NOT NULL,
    assigned_at timestamp with time zone DEFAULT now() NOT NULL,
    assigned_by uuid
);


ALTER TABLE public.position_tags OWNER TO sigmasight;

--
-- Name: position_volatility; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.position_volatility (
    id uuid NOT NULL,
    position_id uuid NOT NULL,
    calculation_date date NOT NULL,
    realized_vol_21d numeric(10,4),
    realized_vol_63d numeric(10,4),
    vol_daily numeric(10,4),
    vol_weekly numeric(10,4),
    vol_monthly numeric(10,4),
    expected_vol_21d numeric(10,4),
    vol_trend character varying(20),
    vol_trend_strength numeric(10,4),
    vol_percentile numeric(10,4),
    observations integer,
    model_r_squared numeric(10,4),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.position_volatility OWNER TO sigmasight;

--
-- Name: positions; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.positions (
    id uuid NOT NULL,
    portfolio_id uuid NOT NULL,
    symbol character varying(20) NOT NULL,
    position_type public.positiontype NOT NULL,
    quantity numeric(16,4) NOT NULL,
    entry_price numeric(12,4) NOT NULL,
    entry_date date NOT NULL,
    exit_price numeric(12,4),
    exit_date date,
    underlying_symbol character varying(10),
    strike_price numeric(12,4),
    expiration_date date,
    investment_class character varying(20),
    investment_subtype character varying(30),
    last_price numeric(12,4),
    market_value numeric(16,2),
    unrealized_pnl numeric(16,2),
    realized_pnl numeric(16,2),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone
);


ALTER TABLE public.positions OWNER TO sigmasight;

--
-- Name: stress_test_results; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.stress_test_results (
    id uuid NOT NULL,
    portfolio_id uuid NOT NULL,
    scenario_id uuid NOT NULL,
    calculation_date date NOT NULL,
    direct_pnl numeric(16,2) NOT NULL,
    correlated_pnl numeric(16,2) NOT NULL,
    correlation_effect numeric(16,2) NOT NULL,
    factor_impacts jsonb,
    calculation_metadata jsonb,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.stress_test_results OWNER TO sigmasight;

--
-- Name: stress_test_scenarios; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.stress_test_scenarios (
    id uuid NOT NULL,
    scenario_id character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    description character varying(1000),
    category character varying(50) NOT NULL,
    severity character varying(20) NOT NULL,
    shock_config jsonb NOT NULL,
    active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.stress_test_scenarios OWNER TO sigmasight;

--
-- Name: tags; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.tags (
    id uuid NOT NULL
);


ALTER TABLE public.tags OWNER TO sigmasight;

--
-- Name: tags_v2; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.tags_v2 (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    name character varying(50) NOT NULL,
    color character varying(7),
    description text,
    display_order integer NOT NULL,
    usage_count integer NOT NULL,
    is_archived boolean NOT NULL,
    archived_at timestamp with time zone,
    archived_by uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_tags_v2_valid_hex_color CHECK (((color)::text ~ '^#[0-9A-Fa-f]{6}$'::text))
);


ALTER TABLE public.tags_v2 OWNER TO sigmasight;

--
-- Name: users; Type: TABLE; Schema: public; Owner: sigmasight
--

CREATE TABLE public.users (
    id uuid NOT NULL,
    email character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    full_name character varying(255) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.users OWNER TO sigmasight;

--
-- Data for Name: agent_conversations; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.agent_conversations (id, user_id, mode, provider, provider_thread_id, provider_run_id, created_at, updated_at, metadata) FROM stdin;
ad0c8200-da60-43b3-bcba-9bd8ccbe8cf9	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-10-30 09:53:33.980412+00	2025-10-30 09:53:33.980412+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
c518d11c-7de6-40ba-8bcf-e137ac73e2f7	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-10-30 17:16:23.890977+00	2025-10-30 17:16:23.890977+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
4bdc2653-9816-4afb-82f8-4d0468cca65a	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-10-30 18:14:45.645841+00	2025-10-30 18:14:45.645841+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
522e02be-c969-4e70-ab7b-674d8073e03d	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-10-30 19:20:46.442613+00	2025-10-30 19:20:46.442613+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
5de1f122-3ea2-4606-8df9-d7dfd5154d15	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-10-30 19:52:24.605535+00	2025-10-30 19:52:24.605535+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
b7fae6cd-ede9-4325-81b6-18ed0ca7bd7a	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-10-30 19:56:39.055855+00	2025-10-30 19:56:39.055855+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
27c63a92-4c48-4f28-be67-d6288c50e989	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-10-31 21:33:46.541445+00	2025-10-31 21:33:46.541445+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
0d6d3664-8d4f-4f0f-b95b-d37967d83645	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-10-31 22:05:05.980793+00	2025-10-31 22:05:05.980793+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
2c13ed7f-d9e4-4686-9361-9c6f81113fd9	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-11-01 01:02:12.006681+00	2025-11-01 01:02:12.006681+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
dcf9ff46-5883-4a9a-bb83-f7fef6af9315	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-11-01 01:55:06.074413+00	2025-11-01 01:55:06.074413+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
8a47b625-d334-4251-baee-c302c984e224	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-11-01 01:56:09.831889+00	2025-11-01 01:56:09.831889+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
2d0b39b4-1e3a-48bb-bfa5-a5e5a81f1959	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-11-01 02:16:05.35966+00	2025-11-01 02:16:05.35966+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
b339d1d4-2fc3-486e-a3ca-46c65757af53	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-11-01 03:15:13.820098+00	2025-11-01 03:15:13.820098+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
900bb6c0-92f0-41d9-9d65-15e002becaad	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-11-01 03:31:20.455514+00	2025-11-01 03:31:20.455514+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
7699672d-fb1a-4b96-80b2-01cecb947d8f	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-11-01 05:52:30.908186+00	2025-11-01 05:52:30.908186+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
04967cbb-517e-42a3-ad97-fb7ab13467f2	9dacfb0f-2123-7a94-debc-0f982b90d845	claude-insights	anthropic	\N	\N	2025-11-01 06:05:26.321665+00	2025-11-01 06:05:26.321665+00	{"model": "claude-sonnet-4", "portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4", "tools_enabled": true}
b7f53a1d-8da4-484c-a07e-9b67e2cc8bef	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-11-01 08:27:01.138111+00	2025-11-01 08:27:01.138111+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
dfc52ada-88eb-48dd-a2d3-3d961b896cf1	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-11-01 08:28:10.723326+00	2025-11-01 08:28:10.723326+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
ce6271e3-5b0e-4976-bc13-8f9405e5e83e	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-11-01 08:29:19.946503+00	2025-11-01 08:29:19.946503+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
c4fb0d8f-765e-4cd6-b28d-d14cb1264c27	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-11-01 08:30:30.614323+00	2025-11-01 08:30:30.614323+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
3c6d8844-d51c-4136-ae8f-11d2e66f17dc	fd5f083c-6ffc-df32-89ca-a4044b5723f5	green	openai	\N	\N	2025-11-01 08:30:45.555382+00	2025-11-01 08:30:45.555382+00	{"portfolio_id": "1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe"}
06b62c11-c815-4d17-bd3b-257ad78a9525	9dacfb0f-2123-7a94-debc-0f982b90d845	green	openai	\N	\N	2025-11-01 17:26:01.317201+00	2025-11-01 17:26:01.317201+00	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4"}
\.


--
-- Data for Name: agent_messages; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.agent_messages (id, conversation_id, role, content, tool_calls, first_token_ms, latency_ms, prompt_tokens, completion_tokens, total_tokens, provider_message_id, created_at, error) FROM stdin;
3c60c67b-db5a-48dd-aaf9-8a1d974cc72e	04967cbb-517e-42a3-ad97-fb7ab13467f2	user	What are the main risks in my portfolio?	[]	\N	\N	\N	\N	\N	\N	2025-11-01 06:05:26.355233+00	\N
64d49676-56fe-4e5a-81c1-d84a8f78a898	04967cbb-517e-42a3-ad97-fb7ab13467f2	assistant	## Major Risks Hidden in Your Portfolio Structure\n\n## Summary\n\nI found some concerning risk concentrations in your portfolio that could hurt you in a market downturn. Your biggest issue isn't what you own, but what you don't know you own - there's a massive data classification problem that's masking your true exposures, plus you're carrying significant downside risk from your ETF-heavy structure.\n\n## Key Findings\n\n- I discovered 97% of your portfolio ($64.9M out of $66.9M total) is classified as "Unclassified" - this is a huge red flag because I can't properly assess your sector concentrations or correlations\n- I found your portfolio would lose $1.15M (-58.5%) in a severe market crash scenario, which is much worse than a typical diversified portfolio\n- I noticed extremely high correlations between your major ETF holdings (QQQ-SPY at 95.4%, QQQ-VTI at 93.9%) - you're not getting the diversification you think you are\n- I identified that you have moderate growth factor exposure (47.3% beta) but negative momentum exposure (-8.6%), meaning you could get hit during growth selloffs without momentum protection\n- I found your portfolio is only 69.7% invested with 30.3% in cash, but your stress test losses suggest the equity portion is highly concentrated in risky assets\n\n## Detailed Analysis\n\nThe most alarming thing I found is that nearly your entire portfolio is showing up as "Unclassified" in the sector analysis. This tells me there's a serious data quality issue - either you have positions in instruments that aren't properly categorized, or there are complex derivatives/structured products that the system can't classify. This is dangerous because you can't manage risks you can't see.\n\nLooking at your stress test results, I'm seeing some really concerning downside scenarios. In a severe market crash (similar to March 2020), you'd lose 58.5% of your portfolio value. That's much worse than a typical diversified portfolio would experience. The liquidity crisis scenario shows a 45% loss, which suggests you might be holding illiquid or complex positions that would be hard to exit during stress.\n\nYour correlation matrix reveals another major issue - your ETF holdings are essentially the same trade. QQQ and SPY have a 95.4% correlation, meaning they move together almost perfectly. You're not getting meaningful diversification between these positions. When tech sells off, both will get hammered simultaneously.\n\nI also noticed your factor exposures show some contradictory signals. You have strong growth exposure (47.3% beta) but negative momentum (-8.6%). This is problematic because growth stocks often rely on momentum to sustain their valuations. Without momentum support, growth positions can fall harder during rotations.\n\nYour market beta of 64% suggests you should be less volatile than the market, but your stress test results contradict this. This disconnect tells me you might have leverage, derivatives, or concentrated positions that aren't showing up properly in the beta calculation.\n\n## Recommendations\n\n- I'd strongly recommend conducting an immediate position-by-position audit to identify what's causing the "Unclassified" issue - you need to know exactly what you own before you can manage risk properly\n- Consider reducing the overlap between QQQ and SPY - these are essentially the same bet, so pick one and diversify the other allocation into truly uncorrelated assets\n- You should add some downside protection given those severe stress test results - consider protective puts on your largest ETF positions or allocating 5-10% to defensive assets\n- I'd recommend stress testing your actual individual positions rather than relying on portfolio-level analysis until you resolve the classification issues\n- Consider reducing your growth factor exposure or adding momentum exposure to balance out the factor profile - the current combination leaves you vulnerable during growth-to-value rotations\n\n## Data Limitations\n\nI'm working with incomplete information due to the massive "Unclassified" portion of your portfolio. This means I can't give you accurate sector exposure analysis, and the correlation matrix only covers 17 symbols out of what appears to be a much larger portfolio. The stress test results might not reflect your true risk profile if there are complex instruments I can't see. I'd strongly recommend getting this data classification issue resolved before making any major portfolio changes.	[{"count": 5}]	\N	39357	12291	1298	13589	\N	2025-11-01 06:06:09.682795+00	\N
\.


--
-- Data for Name: agent_user_preferences; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.agent_user_preferences (id, user_id, default_mode, preferred_model, code_interpreter_enabled, tool_calls_enabled, streaming_enabled, user_context, settings, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: ai_insight_templates; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.ai_insight_templates (id, insight_type, name, description, version, system_prompt, investigation_prompt, model_preference, max_tokens, temperature, required_tools, optional_tools, active, avg_quality_score, usage_count, created_at, updated_at, deprecated_at) FROM stdin;
\.


--
-- Data for Name: ai_insights; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.ai_insights (id, portfolio_id, insight_type, title, severity, summary, full_analysis, key_findings, recommendations, data_limitations, context_data, data_quality, focus_area, user_question, model_used, provider, prompt_version, cost_usd, generation_time_ms, token_count_input, token_count_output, tool_calls_count, cache_hit, cache_source_id, cache_key, user_rating, user_feedback, viewed, dismissed, created_at, expires_at, updated_at) FROM stdin;
9d98d374-012d-4aee-8a3f-a198d613a667	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	daily_summary	Daily Summary Analysis	warning	I ran into authentication issues accessing your portfolio's risk analytics, but I can still give you a meaningful review based on your positions. Looking at your 16-position portfolio worth ~$485K, I see a well-diversified mix that's heavily tilted toward large-cap tech with some solid diversification through mutual funds and ETFs.	## Portfolio Analytics Currently Unavailable - Position-Level Review\n\n## Summary\n\nI ran into authentication issues accessing your portfolio's risk analytics, but I can still give you a meaningful review based on your positions. Looking at your 16-position portfolio worth ~$485K, I see a well-diversified mix that's heavily tilted toward large-cap tech with some solid diversification through mutual funds and ETFs.\n\n## Key Findings\n\n- I found you have significant concentration in mega-cap tech stocks - AAPL, MSFT, AMZN, GOOGL, TSLA, and NVDA represent roughly 60% of your individual stock positions\n- I noticed you're well-diversified across asset classes with mutual funds (FXNAX, FCNTX, FMAGX), international exposure (VTIAX), broad market (VTI), bonds (BND), and REITs (VNQ)\n- I can see you have quality positions in defensive sectors with JNJ (healthcare), JPM (financials), and V (payments) providing some balance\n- I found your entry prices suggest you've been building positions over time - some at attractive levels like GOOGL at $160 and AMZN at $170\n\n## Detailed Analysis\n\nYour portfolio shows the hallmarks of a growth-oriented individual investor who understands diversification. The tech concentration isn't necessarily bad - these are quality companies - but it does create meaningful sector risk. When I look at your entries, you've got some solid positioning: GOOGL at $160 and AMZN at $170 look particularly attractive given where these stocks have traded.\n\nThe mutual fund allocation is smart - you're getting professional management and broader diversification through FXNAX (likely a large-cap fund), FCNTX (probably focused on growth), and FMAGX (appears to be a sector-specific fund). Your VTIAX position gives you international exposure, which many individual investors skip entirely.\n\nYour bond allocation through BND and REIT exposure through VNQ show you're thinking about total portfolio construction, not just chasing growth. This suggests you understand that different asset classes perform differently in various market environments.\n\nWithout current market prices, I can't calculate your exact gains/losses, but based on your entry points, you're likely sitting on some nice gains in several positions, particularly if you bought NVDA anywhere near $700 when it was climbing.\n\n## Recommendations\n\n- I'd recommend monitoring your tech concentration closely - consider taking some profits if these positions have run up significantly since your entries\n- Consider adding some defensive sectors like utilities or consumer staples to balance the growth tilt, especially if we're heading into a more volatile period\n- You might want to review the overlap between your individual tech stocks and what's inside your mutual funds - you could have more tech exposure than you realize\n- I'd suggest setting some position size limits - maybe cap any single stock at 8-10% of total portfolio value to manage concentration risk\n- Consider adding some international developed market exposure if VTIAX is primarily emerging markets\n\n## Data Limitations\n\nI don't have access to current market prices, so I can't give you precise portfolio values, gains/losses, or current sector weightings as of November 1st. The analytics system is also temporarily unavailable, which means I can't provide the detailed risk metrics, correlations, or stress test results that would normally be part of a comprehensive daily review. Once the data access is restored, we should revisit this analysis with full risk analytics, factor exposures, and current market valuations.	["I found you have significant concentration in mega-cap tech stocks - AAPL, MSFT, AMZN, GOOGL, TSLA, and NVDA represent roughly 60% of your individual stock positions", "I noticed you're well-diversified across asset classes with mutual funds (FXNAX, FCNTX, FMAGX), international exposure (VTIAX), broad market (VTI), bonds (BND), and REITs (VNQ)", "I can see you have quality positions in defensive sectors with JNJ (healthcare), JPM (financials), and V (payments) providing some balance", "I found your entry prices suggest you've been building positions over time - some at attractive levels like GOOGL at $160 and AMZN at $170"]	["I'd recommend monitoring your tech concentration closely - consider taking some profits if these positions have run up significantly since your entries", "Consider adding some defensive sectors like utilities or consumer staples to balance the growth tilt, especially if we're heading into a more volatile period", "You might want to review the overlap between your individual tech stocks and what's inside your mutual funds - you could have more tech exposure than you realize", "I'd suggest setting some position size limits - maybe cap any single stock at 8-10% of total portfolio value to manage concentration risk", "Consider adding some international developed market exposure if VTIAX is primarily emerging markets"]	I don't have access to current market prices, so I can't give you precise portfolio values, gains/losses, or current sector weightings as of November 1st. The analytics system is also temporarily unavailable, which means I can't provide the detailed risk metrics, correlations, or stress test results that would normally be part of a comprehensive daily review. Once the data access is restored, we should revisit this analysis with full risk analytics, factor exposures, and current market valuations.	{"portfolio_id": "1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe", "focus_area": null, "build_timestamp": "2025-11-01T04:42:39.933101", "portfolio_summary": {"available": true, "name": "Demo Individual Investor Portfolio", "currency": "USD", "equity_balance": 485000.0, "description": "Individual investor with 401k, IRA, and taxable accounts. Core holdings with growth tilt, heavy mutual fund allocation."}, "snapshot": {"date": "2025-11-01", "equity_balance": null, "total_value": null, "cash_value": null, "long_value": null, "short_value": null, "gross_exposure": null, "net_exposure": null, "portfolio_delta": null, "realized_volatility_21d": null, "beta_calculated_90d": null, "daily_pnl": null, "cumulative_pnl": null, "num_positions": 16, "target_price_return_eoy": 13.323, "target_price_return_next_year": null, "target_price_downside_return": null, "target_price_upside_eoy_dollars": 64616.54, "target_price_upside_next_year_dollars": null, "target_price_downside_dollars": null, "target_price_coverage_pct": 56.25, "target_price_positions_count": 9, "target_price_total_positions": 16, "target_price_last_updated": "2025-11-01T08:32:28.682929+00:00"}, "positions": {"available": true, "count": 16, "items": [{"symbol": "AAPL", "position_type": "LONG", "quantity": 85.0, "entry_price": 225.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "MSFT", "position_type": "LONG", "quantity": 45.0, "entry_price": 420.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "AMZN", "position_type": "LONG", "quantity": 110.0, "entry_price": 170.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "GOOGL", "position_type": "LONG", "quantity": 115.0, "entry_price": 160.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "TSLA", "position_type": "LONG", "quantity": 70.0, "entry_price": 255.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "NVDA", "position_type": "LONG", "quantity": 25.0, "entry_price": 700.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "JNJ", "position_type": "LONG", "quantity": 105.0, "entry_price": 160.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "JPM", "position_type": "LONG", "quantity": 85.0, "entry_price": 170.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "V", "position_type": "LONG", "quantity": 50.0, "entry_price": 268.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "FXNAX", "position_type": "LONG", "quantity": 4365.0, "entry_price": 20.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "FCNTX", "position_type": "LONG", "quantity": 4850.0, "entry_price": 15.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "FMAGX", "position_type": "LONG", "quantity": 3880.0, "entry_price": 15.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "VTIAX", "position_type": "LONG", "quantity": 970.0, "entry_price": 30.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "VTI", "position_type": "LONG", "quantity": 155.0, "entry_price": 250.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "BND", "position_type": "LONG", "quantity": 315.0, "entry_price": 77.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "VNQ", "position_type": "LONG", "quantity": 204.0, "entry_price": 95.0, "last_price": null, "market_value": null, "unrealized_pnl": null}]}, "risk_metrics": {"greeks": {"available": false}, "volatility": {"available": false}}, "factor_exposure": {"available": false}, "correlations": {"available": false}, "volatility_analytics": {"available": true, "portfolio_level": {"realized_volatility_21d": null, "realized_volatility_63d": null, "expected_volatility_21d": null, "volatility_trend": null, "volatility_percentile": null}}, "spread_factors": {"available": false}, "data_quality": {"portfolio_info": "complete", "snapshot": "incomplete", "positions": "complete", "greeks": "incomplete", "factor_exposure": "incomplete", "correlations": "incomplete", "volatility_analytics": "complete", "spread_factors": "incomplete", "overall": "partial"}, "summary_stats": {"position_count": 16, "total_value": null, "gross_exposure": null, "net_exposure": null, "portfolio_delta": null, "realized_volatility_21d": null, "beta_calculated_90d": null, "daily_pnl": null, "data_completeness": "partial"}}	{"portfolio_info": "complete", "snapshot": "incomplete", "positions": "complete", "greeks": "incomplete", "factor_exposure": "incomplete", "correlations": "incomplete", "volatility_analytics": "complete", "spread_factors": "incomplete", "overall": "partial"}	\N	\N	claude-sonnet-4	anthropic	1.0.0	0.036372	30204.15	6374	1150	5	t	\N	9b836adbeff36c5f0cf31e377dea284d4b973a4d25b9940fe1c9d2ea7223ea35	\N	\N	f	f	2025-11-01 04:43:10.166282	\N	2025-11-01 04:43:10.954208
bee67ca6-ec9d-44ee-a92d-9ac77af4c296	e23ab931-a033-edfe-ed4f-9d02474780b4	daily_summary	Daily Summary Analysis	warning	I'm unable to access the full analytics suite due to system authentication issues, but I can still provide valuable insights based on your portfolio holdings. Looking at your $2.85M portfolio, I see significant concentration in mega-cap tech and some interesting alternative investments that warrant discussion.	## Portfolio Analysis Temporarily Unavailable - Manual Review Based on Holdings\n\n## Summary\nI'm unable to access the full analytics suite due to system authentication issues, but I can still provide valuable insights based on your portfolio holdings. Looking at your $2.85M portfolio, I see significant concentration in mega-cap tech and some interesting alternative investments that warrant discussion.\n\n## Key Findings\n- I found heavy concentration in mega-cap tech stocks - AAPL, MSFT, AMZN, GOOGL, NVDA, and META represent roughly $400K+ in combined exposure at entry prices\n- I noticed you have substantial ETF overlap with SPY, QQQ, and VTI totaling about $373K at entry - this creates redundant broad market exposure\n- I identified two large alternative investments (Starwood REIT and Two Sigma Fund) at $142.5K each, representing about 10% of your total portfolio\n- I see defensive positioning with consumer staples (PG, JNJ) and commodities (GLD, DJP), but these appear to be smaller allocations\n- I found your financial sector exposure through JPM and BRK-B provides some diversification from the tech-heavy allocation\n\n## Detailed Analysis\n\nLet me walk you through what I'm seeing in your portfolio structure. You've built what looks like a core-satellite approach, but there are some concentration risks I want to highlight.\n\nYour tech exposure is substantial when I add up the individual names plus the QQQ position. At entry prices, you're looking at roughly 35-40% tech exposure, which is well above the S&P 500's typical 25-30% weighting. This isn't necessarily bad - tech has been a great performer - but it does create meaningful concentration risk if the sector rotates.\n\nThe ETF overlap is something I'd want us to address. Your SPY, QQQ, and VTI positions are all giving you broad market exposure, but with different tilts. VTI includes small and mid-caps, QQQ is pure tech/growth, and SPY is large-cap blend. This creates some redundancy that we could streamline.\n\nI'm intrigued by your alternative allocations. The Starwood REIT and Two Sigma Fund positions suggest you're thinking beyond traditional equity/bond allocations, which is smart for a portfolio of this size. These provide diversification benefits that public markets can't offer.\n\nYour commodity exposure through GLD and DJP shows you're thinking about inflation protection, though the allocations appear relatively modest. Given the current macro environment, this positioning makes sense as a portfolio hedge.\n\n## Recommendations\n- I'd recommend consolidating your ETF positions - consider keeping VTI for broad exposure and reducing or eliminating the SPY/QQQ overlap to free up capital for other opportunities\n- Consider trimming your individual tech positions by 10-15% to reduce concentration risk - you're already getting tech exposure through your ETFs\n- I'd suggest increasing your defensive allocation given the portfolio's growth tilt - maybe add more healthcare, utilities, or consumer staples\n- Consider adding some international exposure - I don't see any developed or emerging market positions, which limits your diversification\n- You might want to review the alternative investments' liquidity terms to ensure they align with your overall portfolio liquidity needs\n\n## Data Limitations\nI don't have access to current market prices, so I'm working with your entry prices which may not reflect current valuations. I also can't provide risk metrics like beta, Sharpe ratio, or correlation analysis due to system access issues. Without current pricing, I can't calculate your actual sector weightings or performance attribution. For a complete picture, we'll need to resolve the data access issues to get real-time analytics, stress testing results, and factor exposures.	["I found heavy concentration in mega-cap tech stocks - AAPL, MSFT, AMZN, GOOGL, NVDA, and META represent roughly $400K+ in combined exposure at entry prices", "I noticed you have substantial ETF overlap with SPY, QQQ, and VTI totaling about $373K at entry - this creates redundant broad market exposure", "I identified two large alternative investments (Starwood REIT and Two Sigma Fund) at $142.5K each, representing about 10% of your total portfolio", "I see defensive positioning with consumer staples (PG, JNJ) and commodities (GLD, DJP), but these appear to be smaller allocations", "I found your financial sector exposure through JPM and BRK-B provides some diversification from the tech-heavy allocation"]	["I'd recommend consolidating your ETF positions - consider keeping VTI for broad exposure and reducing or eliminating the SPY/QQQ overlap to free up capital for other opportunities", "Consider trimming your individual tech positions by 10-15% to reduce concentration risk - you're already getting tech exposure through your ETFs", "I'd suggest increasing your defensive allocation given the portfolio's growth tilt - maybe add more healthcare, utilities, or consumer staples", "Consider adding some international exposure - I don't see any developed or emerging market positions, which limits your diversification", "You might want to review the alternative investments' liquidity terms to ensure they align with your overall portfolio liquidity needs"]	I don't have access to current market prices, so I'm working with your entry prices which may not reflect current valuations. I also can't provide risk metrics like beta, Sharpe ratio, or correlation analysis due to system access issues. Without current pricing, I can't calculate your actual sector weightings or performance attribution. For a complete picture, we'll need to resolve the data access issues to get real-time analytics, stress testing results, and factor exposures.	{"portfolio_id": "e23ab931-a033-edfe-ed4f-9d02474780b4", "focus_area": null, "build_timestamp": "2025-11-01T04:05:08.707927", "portfolio_summary": {"available": true, "name": "Demo High Net Worth Investor Portfolio", "currency": "USD", "equity_balance": 2850000.0, "description": "High net worth individual with access to private investments. Diversified across public markets with alternative investments."}, "snapshot": {"date": "2025-11-01", "equity_balance": null, "total_value": null, "cash_value": null, "long_value": null, "short_value": null, "gross_exposure": null, "net_exposure": null, "portfolio_delta": null, "realized_volatility_21d": null, "beta_calculated_90d": null, "daily_pnl": null, "cumulative_pnl": null, "num_positions": 29, "target_price_return_eoy": 8.7616, "target_price_return_next_year": null, "target_price_downside_return": null, "target_price_upside_eoy_dollars": 249705.09, "target_price_upside_next_year_dollars": null, "target_price_downside_dollars": null, "target_price_coverage_pct": 44.8276, "target_price_positions_count": 13, "target_price_total_positions": 29, "target_price_last_updated": "2025-11-01T08:04:24.460273+00:00"}, "positions": {"available": true, "count": 29, "items": [{"symbol": "SPY", "position_type": "LONG", "quantity": 400.0, "entry_price": 530.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "QQQ", "position_type": "LONG", "quantity": 450.0, "entry_price": 420.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "VTI", "position_type": "LONG", "quantity": 800.0, "entry_price": 230.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "AAPL", "position_type": "LONG", "quantity": 400.0, "entry_price": 225.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "MSFT", "position_type": "LONG", "quantity": 200.0, "entry_price": 420.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "AMZN", "position_type": "LONG", "quantity": 480.0, "entry_price": 170.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "GOOGL", "position_type": "LONG", "quantity": 500.0, "entry_price": 160.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "BRK-B", "position_type": "LONG", "quantity": 180.0, "entry_price": 440.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "JPM", "position_type": "LONG", "quantity": 350.0, "entry_price": 170.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "JNJ", "position_type": "LONG", "quantity": 310.0, "entry_price": 160.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "NVDA", "position_type": "LONG", "quantity": 70.0, "entry_price": 700.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "META", "position_type": "LONG", "quantity": 90.0, "entry_price": 530.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "UNH", "position_type": "LONG", "quantity": 85.0, "entry_price": 545.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "V", "position_type": "LONG", "quantity": 170.0, "entry_price": 268.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "HD", "position_type": "LONG", "quantity": 125.0, "entry_price": 350.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "PG", "position_type": "LONG", "quantity": 250.0, "entry_price": 165.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "GLD", "position_type": "LONG", "quantity": 325.0, "entry_price": 219.23, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "DJP", "position_type": "LONG", "quantity": 1900.0, "entry_price": 30.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "STARWOOD_REIT", "position_type": "LONG", "quantity": 1.0, "entry_price": 142500.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "TWO_SIGMA_FUND", "position_type": "LONG", "quantity": 1.0, "entry_price": 142500.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "HOME_EQUITY", "position_type": "LONG", "quantity": 1.0, "entry_price": 285000.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "RENTAL_SFH", "position_type": "LONG", "quantity": 1.0, "entry_price": 142500.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "MONEY_MARKET", "position_type": "LONG", "quantity": 1.0, "entry_price": 57000.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "TREASURY_BILLS", "position_type": "LONG", "quantity": 1.0, "entry_price": 28500.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "CRYPTO_BTC_ETH", "position_type": "LONG", "quantity": 1.0, "entry_price": 42750.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "A16Z_VC_FUND", "position_type": "LONG", "quantity": 1.0, "entry_price": 142500.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "ART_COLLECTIBLES", "position_type": "LONG", "quantity": 1.0, "entry_price": 28500.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "BX_PRIVATE_EQUITY", "position_type": "LONG", "quantity": 1.0, "entry_price": 285000.0, "last_price": null, "market_value": null, "unrealized_pnl": null}, {"symbol": "RENTAL_CONDO", "position_type": "LONG", "quantity": 1.0, "entry_price": 142500.0, "last_price": null, "market_value": null, "unrealized_pnl": null}]}, "risk_metrics": {"greeks": {"available": false}, "volatility": {"available": false}}, "factor_exposure": {"available": false}, "correlations": {"available": false}, "volatility_analytics": {"available": true, "portfolio_level": {"realized_volatility_21d": null, "realized_volatility_63d": null, "expected_volatility_21d": null, "volatility_trend": null, "volatility_percentile": null}}, "spread_factors": {"available": false}, "data_quality": {"portfolio_info": "complete", "snapshot": "incomplete", "positions": "complete", "greeks": "incomplete", "factor_exposure": "incomplete", "correlations": "incomplete", "volatility_analytics": "complete", "spread_factors": "incomplete", "overall": "partial"}, "summary_stats": {"position_count": 29, "total_value": null, "gross_exposure": null, "net_exposure": null, "portfolio_delta": null, "realized_volatility_21d": null, "beta_calculated_90d": null, "daily_pnl": null, "data_completeness": "partial"}}	{"portfolio_info": "complete", "snapshot": "incomplete", "positions": "complete", "greeks": "incomplete", "factor_exposure": "incomplete", "correlations": "incomplete", "volatility_analytics": "complete", "spread_factors": "incomplete", "overall": "partial"}	\N	\N	claude-sonnet-4	anthropic	1.0.0	0.037485	31919.81	6545	1190	5	t	\N	cbaf6a6620847f64395a570af79f81dae9c39a1f791c1c37dc6d9a1f681b1ff4	\N	\N	f	t	2025-11-01 04:05:40.66505	\N	2025-11-01 04:29:42.796877
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.alembic_version (version_num) FROM stdin;
ca2a68ee0c2c
\.


--
-- Data for Name: batch_job_schedules; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.batch_job_schedules (id, job_name, job_type, cron_expression, is_active, description, timeout_seconds, retry_count, retry_delay_seconds, last_run_at, next_run_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: batch_jobs; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.batch_jobs (id, job_name, job_type, status, started_at, completed_at, duration_seconds, records_processed, error_message, job_metadata, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: batch_run_tracking; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.batch_run_tracking (id, run_date, phase_1_status, phase_2_status, phase_3_status, phase_1_duration_seconds, phase_2_duration_seconds, phase_3_duration_seconds, portfolios_processed, symbols_fetched, data_coverage_pct, error_message, completed_at, created_at) FROM stdin;
e8d723e5-c8c3-4916-9a32-a451d6dfa7e5	2025-07-01	success	success	success	73	2	4	3	46	85.19	\N	2025-10-30 01:18:08.410247+00	2025-10-30 01:18:08.414737+00
860bf77c-9878-45d2-9cc3-6274f9c2c6ea	2025-07-02	success	success	success	74	1	4	3	46	85.19	\N	2025-10-30 01:19:30.110233+00	2025-10-30 01:19:30.112617+00
2a864015-844b-41d2-8ff5-71c13ab0034b	2025-07-03	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 01:21:06.058487+00	2025-10-30 01:21:06.062491+00
4ff84f96-0dcd-44f8-80e6-40412e710b77	2025-07-07	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 01:22:41.946355+00	2025-10-30 01:22:41.950337+00
2ecb4c79-9cbd-43bd-b5d8-2e2e07359196	2025-07-08	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 01:24:18.055781+00	2025-10-30 01:24:18.05806+00
cf3d9bf4-3ee0-4461-a377-370fdaa7df06	2025-07-09	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 01:25:53.98829+00	2025-10-30 01:25:53.991277+00
1597c7a2-5387-445e-b262-f6e9c18884e9	2025-07-10	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 01:27:29.895963+00	2025-10-30 01:27:29.898196+00
426d2691-86c4-410a-b78e-7b8aae8bb5cd	2025-07-11	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 01:29:06.010633+00	2025-10-30 01:29:06.014055+00
46326276-3e7b-4ab5-a5ad-c7a075143220	2025-07-14	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 01:30:41.931165+00	2025-10-30 01:30:41.934841+00
793e52b3-b218-43ed-9fde-ba357b354270	2025-07-15	success	success	success	89	2	8	3	46	85.19	\N	2025-10-30 01:32:22.230424+00	2025-10-30 01:32:22.233648+00
b4b14a12-1beb-43b0-b8f7-51a868b61420	2025-07-16	success	success	success	85	1	5	3	46	85.19	\N	2025-10-30 01:33:54.387061+00	2025-10-30 01:33:54.39075+00
50c4f62b-08de-4482-bb40-77ccd6ac48eb	2025-07-17	success	success	success	88	2	5	3	46	85.19	\N	2025-10-30 01:35:30.771325+00	2025-10-30 01:35:30.774012+00
ef8700ea-c337-4971-9bdc-55f9365dcdd6	2025-07-18	success	success	success	88	1	4	3	46	85.19	\N	2025-10-30 01:37:06.226972+00	2025-10-30 01:37:06.230896+00
dbe168f5-88b8-485f-9cc7-c49fea711358	2025-07-21	success	success	success	88	1	4	3	46	85.19	\N	2025-10-30 01:38:42.077914+00	2025-10-30 01:38:42.081949+00
33cbf210-c0d0-4c7d-acbb-1c8442ad92a5	2025-07-22	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 01:40:18.236838+00	2025-10-30 01:40:18.240251+00
4bf10b0d-e0fc-433e-8043-baafddd6d7f3	2025-07-23	success	success	success	89	1	5	3	46	85.19	\N	2025-10-30 01:41:54.774891+00	2025-10-30 01:41:54.778552+00
8c2df68e-4e91-49e4-9002-0b795ec47624	2025-07-24	success	success	success	88	1	5	3	46	85.19	\N	2025-10-30 01:43:30.459314+00	2025-10-30 01:43:30.462542+00
b53c65a0-9517-43ba-8b24-8f5520fd3a5e	2025-07-25	success	success	success	88	2	6	3	46	85.19	\N	2025-10-30 01:45:09.104564+00	2025-10-30 01:45:09.10882+00
76a27425-04a7-4f63-a8a5-57d3d0b7758a	2025-07-28	success	success	success	88	1	4	3	46	85.19	\N	2025-10-30 01:46:44.674523+00	2025-10-30 01:46:44.676692+00
978aaa0a-b822-48d1-939e-ffac7e850234	2025-07-29	success	success	success	87	1	5	3	46	85.19	\N	2025-10-30 01:48:19.008004+00	2025-10-30 01:48:19.011187+00
2a80767e-6b25-43aa-9164-d10f8089cb7c	2025-07-30	success	success	success	88	1	4	3	46	85.19	\N	2025-10-30 01:49:54.510374+00	2025-10-30 01:49:54.513552+00
23ac2434-fb84-4643-adaa-98509f7744f3	2025-07-31	success	success	success	88	1	4	3	46	85.19	\N	2025-10-30 01:51:30.12655+00	2025-10-30 01:51:30.128397+00
6a94a9f0-e9a0-484f-ada7-23efd2b6792c	2025-08-01	success	success	success	94	1	5	3	46	85.19	\N	2025-10-30 01:53:12.046913+00	2025-10-30 01:53:12.049745+00
2b97ae5d-445a-4cfa-a36d-ec4d0ed93804	2025-08-04	success	success	success	83	1	5	3	46	85.19	\N	2025-10-30 01:54:42.583405+00	2025-10-30 01:54:42.586594+00
ef53515d-17b1-449b-91ba-99a7a625086d	2025-08-05	success	success	success	88	1	4	3	46	85.19	\N	2025-10-30 01:56:18.19225+00	2025-10-30 01:56:18.194546+00
fc0d7ee5-6aaf-4057-9e98-f78c0e97634f	2025-08-06	success	success	success	89	1	5	3	46	85.19	\N	2025-10-30 01:57:54.266057+00	2025-10-30 01:57:54.268399+00
ccf8026a-9a88-433b-b76c-adac53fe80f3	2025-08-07	success	success	success	88	1	4	3	46	85.19	\N	2025-10-30 01:59:30.018595+00	2025-10-30 01:59:30.021423+00
be6ca75f-74fc-4201-8122-fe8668485f96	2025-08-08	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 02:01:06.097747+00	2025-10-30 02:01:06.101821+00
66352dbe-9641-4b61-82b5-c696207cb08e	2025-08-11	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 02:02:42.108276+00	2025-10-30 02:02:42.111257+00
ec34edd5-cea2-4bb5-9014-150e6fa31e27	2025-08-12	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 02:04:18.069613+00	2025-10-30 02:04:18.072318+00
0f656d93-da45-4c88-ba01-d71b60e46601	2025-08-13	success	success	success	90	1	5	3	46	85.19	\N	2025-10-30 02:05:55.874011+00	2025-10-30 02:05:55.877504+00
29b4fd56-e039-46e4-a515-889b0aab4f71	2025-08-14	success	success	success	87	1	4	3	46	85.19	\N	2025-10-30 02:07:30.236323+00	2025-10-30 02:07:30.23847+00
485761ba-dca1-4330-9290-08c3ba6602e5	2025-08-15	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 02:09:06.224903+00	2025-10-30 02:09:06.228746+00
98ec2dab-ddd8-4aca-a86a-6e2209022e2c	2025-08-18	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 02:10:42.123722+00	2025-10-30 02:10:42.127554+00
e25c9f51-0f6a-4c37-8f69-c9c9852bb596	2025-08-19	success	success	success	89	1	5	3	46	85.19	\N	2025-10-30 02:12:18.270508+00	2025-10-30 02:12:18.273901+00
bd68d364-02a1-453e-8b32-40dba2b27899	2025-08-20	success	success	success	89	1	5	3	46	85.19	\N	2025-10-30 02:13:54.451226+00	2025-10-30 02:13:54.454274+00
6cda1358-a7e2-4537-b21e-0a87b9128668	2025-08-21	success	success	success	88	1	4	3	46	85.19	\N	2025-10-30 02:15:30.231983+00	2025-10-30 02:15:30.235021+00
38a96a1a-c145-4b6e-8c8f-1127da36efae	2025-08-22	success	success	success	89	1	5	3	46	85.19	\N	2025-10-30 02:17:06.487399+00	2025-10-30 02:17:06.489716+00
79e6ea3c-b3fe-493a-a60c-5df570bc6de9	2025-08-25	success	success	success	88	1	5	3	46	85.19	\N	2025-10-30 02:18:42.472508+00	2025-10-30 02:18:42.47654+00
81600eda-2a2a-40c7-9341-f27c59fa0c48	2025-08-26	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 02:20:18.540047+00	2025-10-30 02:20:18.54273+00
be30b70e-19a8-46fe-a86a-5c95dee49e87	2025-08-27	success	success	success	89	1	5	3	46	85.19	\N	2025-10-30 02:21:54.78693+00	2025-10-30 02:21:54.790069+00
5003691a-3db8-4c48-9012-30f5dea91e2e	2025-08-28	success	success	success	95	3	7	3	46	85.19	\N	2025-10-30 02:23:42.11814+00	2025-10-30 02:23:42.121119+00
f57f2b3d-8af2-441f-8cba-5cb02a99dd30	2025-08-29	success	success	success	79	1	5	3	46	85.19	\N	2025-10-30 02:25:08.963954+00	2025-10-30 02:25:08.968802+00
f70c081c-7739-4912-a2d9-dc1779de5a9d	2025-09-02	success	success	success	86	1	5	3	46	85.19	\N	2025-10-30 02:26:42.634782+00	2025-10-30 02:26:42.639012+00
c3a6849c-660c-45e4-8745-0335a0c6c1d1	2025-09-03	success	success	success	88	1	4	3	46	85.19	\N	2025-10-30 02:28:18.255401+00	2025-10-30 02:28:18.25833+00
bcb24d0d-587b-48d5-9324-d00687d252f1	2025-09-04	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 02:29:54.134422+00	2025-10-30 02:29:54.137466+00
5c787162-cb38-44ac-8528-c8fb4dbc8211	2025-09-05	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 02:31:30.29889+00	2025-10-30 02:31:30.300717+00
a35d9bdc-dc71-4fd4-bd9c-a0bc03d0e5eb	2025-09-08	success	success	success	88	1	5	3	46	85.19	\N	2025-10-30 02:33:06.384286+00	2025-10-30 02:33:06.388447+00
640d01c2-0de8-45b0-929c-2aa89cce8e21	2025-09-09	success	success	success	88	2	5	3	46	85.19	\N	2025-10-30 02:34:42.645671+00	2025-10-30 02:34:42.649382+00
172be1d4-1bfb-44a4-a56c-0e00cd60058a	2025-09-10	success	success	success	93	2	8	3	46	85.19	\N	2025-10-30 02:36:26.589784+00	2025-10-30 02:36:26.59308+00
e4eeade4-4ca9-47eb-b656-a53018effbea	2025-09-11	success	success	success	80	1	5	3	46	85.19	\N	2025-10-30 02:37:54.450616+00	2025-10-30 02:37:54.453823+00
16427f51-22fc-4c0a-9e87-2943ca747308	2025-09-12	success	success	success	97	4	9	3	46	85.19	\N	2025-10-30 02:39:45.447727+00	2025-10-30 02:39:45.450439+00
1803f97d-cc37-4e4e-95cf-72fb007b778a	2025-09-15	success	success	success	81	5	7	3	46	85.19	\N	2025-10-30 02:41:19.645907+00	2025-10-30 02:41:19.648728+00
af6362ce-22c6-40eb-bdbd-5f18be920d6a	2025-09-16	success	success	success	83	3	5	3	46	85.19	\N	2025-10-30 02:42:52.719339+00	2025-10-30 02:42:52.722223+00
adfb2140-7806-47de-8399-168a04a2f405	2025-09-17	success	success	success	78	1	5	3	46	85.19	\N	2025-10-30 02:44:18.323553+00	2025-10-30 02:44:18.325768+00
fa841ea6-ea53-48bc-949b-ee767d7e046f	2025-09-18	success	success	success	107	7	15	3	46	85.19	\N	2025-10-30 02:46:29.755686+00	2025-10-30 02:46:29.759581+00
eb1e3a87-2c85-4d36-8585-3dad059a6533	2025-09-19	success	success	success	53	1	4	3	46	85.19	\N	2025-10-30 02:47:30.170176+00	2025-10-30 02:47:30.173595+00
4d5fc002-8733-45b2-9155-41d94b3cee2a	2025-09-22	success	success	success	89	1	5	3	46	85.19	\N	2025-10-30 02:49:06.576593+00	2025-10-30 02:49:06.580336+00
13140ba8-fdf4-4453-aa4d-cd19e15ea4a6	2025-09-23	success	success	success	89	2	5	3	46	85.19	\N	2025-10-30 02:50:43.331913+00	2025-10-30 02:50:43.335687+00
467da630-b2e5-4331-a2aa-c6bebf90d0fd	2025-09-24	success	success	success	87	1	4	3	46	85.19	\N	2025-10-30 02:52:18.31482+00	2025-10-30 02:52:18.317366+00
331d7e77-cb50-4970-a276-fcc5cc3939a5	2025-09-25	success	success	success	89	2	5	3	46	85.19	\N	2025-10-30 02:53:54.682233+00	2025-10-30 02:53:54.684505+00
73c4e5ef-b586-4744-8b2d-483dfc43496b	2025-09-26	success	success	success	92	1	5	3	46	85.19	\N	2025-10-30 02:55:34.760319+00	2025-10-30 02:55:34.764306+00
09135ca9-1112-4111-9ece-4fd27ea0613e	2025-09-29	success	success	success	84	1	4	3	46	85.19	\N	2025-10-30 02:57:06.256468+00	2025-10-30 02:57:06.260594+00
82ae157b-6486-4522-be20-4e0833ec698a	2025-09-30	success	success	success	88	1	4	3	46	85.19	\N	2025-10-30 02:58:42.235683+00	2025-10-30 02:58:42.239364+00
2a432d6f-68ec-46ac-8a9b-83f13f46488a	2025-10-01	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 03:00:18.253063+00	2025-10-30 03:00:18.256318+00
f269f4bb-a30f-4859-8945-b5abb51be09a	2025-10-02	success	success	success	88	1	4	3	46	85.19	\N	2025-10-30 03:01:54.153604+00	2025-10-30 03:01:54.156969+00
7ff37416-1d46-478f-8420-33baa314d9a1	2025-10-03	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 03:03:30.359856+00	2025-10-30 03:03:30.363234+00
f772f1e2-d7e5-4843-bba1-8f93964a112d	2025-10-06	success	success	success	88	1	4	3	46	85.19	\N	2025-10-30 03:05:06.189672+00	2025-10-30 03:05:06.201019+00
e2e84748-80fc-4566-9960-cbdf5bfecc75	2025-10-07	success	success	success	89	2	4	3	46	85.19	\N	2025-10-30 03:06:42.420452+00	2025-10-30 03:06:42.431116+00
92ed60d4-160f-46b0-af68-55cf0b9a53af	2025-10-08	success	success	success	88	1	4	3	46	85.19	\N	2025-10-30 03:08:18.214463+00	2025-10-30 03:08:18.218458+00
5126a0e2-8b50-4dc1-9181-001c73ee43b3	2025-10-09	success	success	success	89	1	5	3	46	85.19	\N	2025-10-30 03:09:54.647534+00	2025-10-30 03:09:54.652399+00
0295926a-c662-4f36-a16c-a4a7e3380279	2025-10-10	success	success	success	88	1	4	3	46	85.19	\N	2025-10-30 03:11:30.260673+00	2025-10-30 03:11:30.263284+00
adc77dc6-dd2d-41ae-ad34-53a7914509c6	2025-10-13	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 03:13:06.322293+00	2025-10-30 03:13:06.325796+00
53b20712-c607-499e-8cfa-d7c753d224dc	2025-10-14	success	success	success	88	2	4	3	46	85.19	\N	2025-10-30 03:14:42.18683+00	2025-10-30 03:14:42.189824+00
3a629d80-2c38-4899-9f0e-0ba93ab113f7	2025-10-15	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 03:16:18.287632+00	2025-10-30 03:16:18.29008+00
d95eb892-a48e-498d-b2a4-77a02927e23e	2025-10-16	success	success	success	88	1	4	3	46	85.19	\N	2025-10-30 03:17:54.353518+00	2025-10-30 03:17:54.359801+00
6f101894-38a7-4f7e-87d0-e66086362f7f	2025-10-17	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 03:19:30.433267+00	2025-10-30 03:19:30.442548+00
fd6db371-3f59-41a1-b7b3-7ce1af1b7bb9	2025-10-20	success	success	success	89	1	4	3	46	85.19	\N	2025-10-30 03:21:06.670753+00	2025-10-30 03:21:06.674648+00
15a2b7bf-cbd0-4f9a-938c-af5cca95a756	2025-10-21	success	success	success	88	1	4	3	46	85.19	\N	2025-10-30 03:22:42.184037+00	2025-10-30 03:22:42.188319+00
58567713-e8c3-4ae9-8641-efd5d8949675	2025-10-22	success	success	success	89	1	5	3	46	85.19	\N	2025-10-30 03:24:18.38933+00	2025-10-30 03:24:18.392275+00
39997f55-8d4e-4aa8-bbfd-a5183ed62445	2025-10-23	success	success	success	88	1	4	3	46	85.19	\N	2025-10-30 03:25:54.13828+00	2025-10-30 03:25:54.143946+00
1f7292ab-1aaf-41d8-9c52-38201f6c605d	2025-10-24	success	success	success	89	2	4	3	46	85.19	\N	2025-10-30 03:27:30.338385+00	2025-10-30 03:27:30.340991+00
7d74e37a-8e55-4ed2-add8-fbb6c2a73b4e	2025-10-27	success	success	success	88	1	4	3	46	85.19	\N	2025-10-30 03:29:06.296388+00	2025-10-30 03:29:06.298713+00
a03d2103-4b1e-46d9-a401-67f352d7bbd6	2025-10-28	success	success	success	86	1	4	3	0	85.19	\N	2025-10-30 03:30:39.490542+00	2025-10-30 03:30:39.493664+00
4edcd119-b5bc-4bf0-90cb-3fa09a9212d8	2025-10-29	success	success	success	640	1	4	3	0	0.00	\N	2025-10-30 03:41:27.328687+00	2025-10-30 03:41:27.334427+00
4e9925e9-6df3-42c9-8db9-884e63df5636	2025-10-31	success	success	success	89	2	7	3	46	85.19	\N	2025-10-31 18:29:07.383952+00	2025-10-31 18:29:07.388325+00
\.


--
-- Data for Name: benchmarks_sector_weights; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.benchmarks_sector_weights (id, benchmark_code, asof_date, sector, weight, market_cap, num_constituents, data_source, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: company_profiles; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.company_profiles (symbol, company_name, sector, industry, exchange, country, market_cap, description, is_etf, is_fund, ceo, employees, website, pe_ratio, forward_pe, dividend_yield, beta, week_52_high, week_52_low, target_mean_price, target_high_price, target_low_price, number_of_analyst_opinions, recommendation_mean, recommendation_key, forward_eps, earnings_growth, revenue_growth, earnings_quarterly_growth, profit_margins, operating_margins, gross_margins, return_on_assets, return_on_equity, total_revenue, current_year_revenue_avg, current_year_revenue_low, current_year_revenue_high, current_year_revenue_growth, current_year_earnings_avg, current_year_earnings_low, current_year_earnings_high, current_year_end_date, next_year_revenue_avg, next_year_revenue_low, next_year_revenue_high, next_year_revenue_growth, next_year_earnings_avg, next_year_earnings_low, next_year_earnings_high, next_year_end_date, data_source, last_updated, created_at, updated_at) FROM stdin;
AAPL	Apple Inc.	Technology	Consumer Electronics	NMS	United States	4027681603584.00	Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide. The company offers iPhone, a line of smartphones; Mac, a line of personal computers; iPad, a line of multi-purpose tablets; and wearables, home, and accessories comprising AirPods, Apple TV, Apple Watch, Beats products, and HomePod. It also provides AppleCare support and cloud services; and operates various platforms, including the App Store that allow customers to discover and download applications and digital content, such as books, music, video, games, and podcasts, as well as advertising services include third-party licensing arrangements and its own advertising platforms. In addition, the company offers various subscription-based services, such as Apple Arcade, a game subscription service; Apple Fitness+, a personalized fitness service; Apple Music, which offers users a curated listening experience with on-demand radio stations; Apple News+, a subscription 	f	f	\N	150000	https://www.apple.com	36.24	32.54	0.380000	1.0940	277.3200	169.2100	274.9676	345.0000	200.0000	41	2.04	buy	8.3100	0.121000	0.096000	0.093000	0.242960	0.299910	0.466780	0.245460	1.498140	408624988160.00	452902605060.00	437285000000.00	466444000000.00	0.088300	8.2435	7.7600	8.8800	2026-09-30	477972218380.00	444291000000.00	526330884300.00	0.055400	9.0784	8.1700	10.0600	2027-09-30	yfinance+yahooquery	2025-11-01 04:22:35.576449+00	2025-11-01 04:22:37.914166+00	2025-11-01 04:22:37.914166+00
META	Meta Platforms, Inc.	Communication Services	Internet Content & Information	NMS	United States	1679855845376.00	Meta Platforms, Inc. engages in the development of products that enable people to connect and share with friends and family through mobile devices, personal computers, virtual reality and mixed reality headsets, augmented reality, and wearables worldwide. It operates through two segments, Family of Apps (FoA) and Reality Labs (RL). The FoA segment offers Facebook, which enables people to build community through feed, reels, stories, groups, marketplace, and other; Instagram that brings people closer through instagram feed, stories, reels, live, and messaging; Messenger, a messaging application for people to connect with friends, family, communities, and businesses across platforms and devices through text, audio, and video calls; Threads, an application for text-based updates and public conversations; and WhatsApp, a messaging application that is used by people and businesses to communicate and transact in a private way. The RL segment provides virtual, augmented, and mixed reality rel	f	f	\N	78450	https://investor.atmeta.com	28.65	25.63	0.320000	1.2030	796.2500	479.8000	846.9155	1117.0000	560.0000	60	1.47	strong_buy	25.3000	-0.826000	0.262000	-0.827000	0.308920	0.400750	0.820130	0.180130	0.326430	189458006016.00	199181224320.00	194663000000.00	200725000000.00	0.210800	24.4352	21.8500	29.4500	2025-12-31	234162706390.00	213000000000.00	258431000000.00	0.175600	29.7825	23.4500	34.8550	2026-12-31	yfinance+yahooquery	2025-11-01 04:22:35.63046+00	2025-11-01 04:22:37.922675+00	2025-11-01 04:22:37.922675+00
UNH	UnitedHealth Group Incorporated	Healthcare	Healthcare Plans	NYQ	United States	312287854592.00	UnitedHealth Group Incorporated operates as a health care company in the United States and internationally. The company operates through four segments: UnitedHealthcare, Optum Health, Optum Insight, and Optum Rx. The UnitedHealthcare segment offers consumer-oriented health benefit plans and services for national employers, public sector employers, mid-sized employers, small businesses, and individuals; health care coverage, and health and well-being services to individuals age 50 and older; Medicaid plans, children's health insurance and health care programs; and health care benefits products and services to state programs caring for the economically disadvantaged, medically underserved, and those without the benefit of employer-funded health care coverage. The Optum Health segment provides care delivery, care management, wellness and consumer engagement, and health financial services patients, consumers, care delivery systems, providers, employers, payers, and public-sector entities. 	f	f	\N	400000	https://www.unitedhealthgroup.com	17.79	11.42	2.590000	0.4780	630.7300	234.6000	385.4000	440.0000	198.0000	25	2.00	buy	29.9000	-0.603000	0.122000	-0.612000	0.040420	0.038130	0.197010	0.053610	0.174760	435159007232.00	447549455080.00	443505000000.00	449674000000.00	0.118100	16.2829	16.0000	16.5006	2025-12-31	458787240490.00	426520700000.00	475799000000.00	0.025100	17.7147	16.4800	19.3100	2026-12-31	yfinance+yahooquery	2025-11-01 04:22:35.684945+00	2025-11-01 04:22:37.926702+00	2025-11-01 04:22:37.926702+00
MSFT	Microsoft Corporation	Technology	Software - Infrastructure	NMS	United States	3907646914560.00	Microsoft Corporation develops and supports software, services, devices, and solutions worldwide. The company's Productivity and Business Processes segment offers Microsoft 365 Commercial, Enterprise Mobility + Security, Windows Commercial, Power BI, Exchange, SharePoint, Microsoft Teams, Security and Compliance, and Copilot; Microsoft 365 Commercial products, such as Windows Commercial on-premises and Office licensed services; Microsoft 365 Consumer products and cloud services, such as Microsoft 365 Consumer subscriptions, Office licensed on-premises, and other consumer services; LinkedIn; Dynamics products and cloud services, such as Dynamics 365, cloud-based applications, and on-premises ERP and CRM applications. Its Intelligent Cloud segment provides Server products and cloud services, such as Azure and other cloud services, GitHub, Nuance Healthcare, virtual desktop offerings, and other cloud services; Server products, including SQL and Windows Server, Visual Studio and System Cen	f	f	\N	228000	https://www.microsoft.com	36.78	34.64	0.700000	1.0230	555.4500	344.7900	625.1688	730.0000	483.0000	52	1.21	strong_buy	14.9500	0.127000	0.184000	0.125000	0.357070	0.488730	0.687640	0.146560	0.322410	293812011008.00	326380957520.00	309912000000.00	333772932290.00	0.158500	15.6909	14.6400	17.0700	2026-06-30	374517842510.00	345949000000.00	403803664780.00	0.147500	18.5632	16.6100	20.4000	2027-06-30	yfinance+yahooquery	2025-11-01 04:22:35.723553+00	2025-11-01 04:22:37.93074+00	2025-11-01 04:22:37.93074+00
SHOP	Shopify Inc.	Technology	Software - Application	NMS	Canada	226470936576.00	Shopify Inc., a commerce technology company, provides tools to start, scale, market, and run a business of various sizes in Canada, the United States, Europe, the Middle East, Africa, the Asia Pacific, and Latin America. The Company offers Shopify platform that enables merchants to manage products and inventory, process orders and payments, fulfill and ship orders, build customer relationships, source products, leverage analytics, and reporting and access financing for running their business across all of their sales channels, including web and mobile storefronts, physical retail locations, social media storefronts, and marketplaces. It also provides Shopify Payments, a fully integrated payment processing service that allows merchants to accept and process payment cards online and offline. In addition, the company engages in the sale of themes and apps; shipping labels through Shopify Shipping; point-of-sale hardware; advertising on the Shopify App Store; and Shop Campaigns for buyer a	f	f	\N	8100	https://www.shopify.com	96.06	93.98	\N	2.7260	182.1900	69.8400	165.8654	200.0000	118.0000	46	1.94	buy	1.8500	4.308000	0.311000	4.298000	0.234170	0.142160	0.493410	0.074350	0.220230	10014000128.00	11277270620.00	11054901000.00	11479200000.00	0.270000	1.4473	1.1300	1.6263	2025-12-31	13802186080.00	13088000000.00	14914000000.00	0.223900	1.8547	1.3600	2.5400	2026-12-31	yfinance+yahooquery	2025-11-01 04:22:35.761673+00	2025-11-01 04:22:37.934708+00	2025-11-01 04:22:37.934708+00
HD	The Home Depot, Inc.	Consumer Cyclical	Home Improvement Retail	NYQ	United States	377838796800.00	The Home Depot, Inc. operates as a home improvement retailer in the United States and internationally. It sells various building materials, home improvement products, lawn and garden products, and décor products, as well as facilities maintenance, repair, and operations products. The company also offers installation services for flooring, water heaters, baths, garage doors, cabinets, cabinet makeovers, countertops, sheds, furnaces and central air systems, and windows. In addition, it provides tool and equipment rental services. The company serves consumers, such as do-it-yourself homeowners and do-it-for-me customers; and professional renovators/remodelers, general contractors, small to medium homebuilders, maintenance professionals, handymen, property managers, building service contractors and specialty tradespeople, such as electricians, landscapers, plumbers, painters, pool contractors, and roofers. It sells its products through websites and its mobile applications, including homede	f	f	\N	470000	https://www.homedepot.com	25.77	24.33	2.420000	1.0010	439.3700	326.3100	438.8485	497.0000	335.0000	33	1.78	buy	15.6000	-0.004000	0.049000	-0.002000	0.088630	0.144780	0.333480	0.137140	1.939540	165054005248.00	164381402200.00	163813892830.00	166323100000.00	0.030500	15.0156	14.8000	15.3000	2026-01-31	171643168130.00	167895021250.00	179021000000.00	0.044200	16.2722	15.4400	16.8300	2027-01-31	yfinance+yahooquery	2025-11-01 04:22:35.861133+00	2025-11-01 04:22:37.938379+00	2025-11-01 04:22:37.938379+00
NFLX	Netflix, Inc.	Communication Services	Entertainment	NMS	United States	474097123328.00	Netflix, Inc. provides entertainment services. The company offers television (TV) series, documentaries, feature films, and games across various genres and languages. It also provides members the ability to receive streaming content through a host of internet-connected devices, including TVs, digital video players, TV set-top boxes, and mobile devices. The company operates approximately in 190 countries. Netflix, Inc. was incorporated in 1997 and is headquartered in Los Gatos, California.	f	f	\N	14000	https://www.netflix.com	46.74	47.05	\N	1.5930	1341.1500	749.6900	1347.3231	1600.0000	770.0000	44	1.90	buy	23.7800	0.087000	0.172000	0.078000	0.240470	0.282200	0.480850	0.147400	0.428610	43378786304.00	45082073330.00	44386000000.00	45623000000.00	0.155900	25.2994	24.9900	26.5600	2025-12-31	50951274930.00	49121000000.00	53247000000.00	0.130200	32.3355	29.7400	35.3700	2026-12-31	yfinance+yahooquery	2025-11-01 04:22:35.929074+00	2025-11-01 04:22:37.94438+00	2025-11-01 04:22:37.94438+00
VIX250716C00025000	\N	\N	\N	Unknown	Unknown	\N		f	f	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:35.987132+00	2025-11-01 04:22:37.948351+00	2025-11-01 04:22:37.948351+00
TSLA250815C00300000	\N	\N	\N	Unknown	Unknown	\N		f	f	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:36.074873+00	2025-11-01 04:22:37.952384+00	2025-11-01 04:22:37.952384+00
PG	The Procter & Gamble Company	Consumer Defensive	Household & Personal Products	NYQ	United States	351374606336.00	The Procter & Gamble Company provides branded consumer packaged goods worldwide. It operates through Beauty; Grooming; Health Care; Fabric & Home Care; and Baby, Feminine & Family Care segments. The company offers conditioners, shampoos, styling aids, and treatments under the Head & Shoulders, Herbal Essences, Pantene, and Rejoice brands; antiperspirants, deodorants, and personal cleansing products under the Native, Old Spice, Safeguard, and Secret brands; and facial moisturizers, cleaners, and treatments under the Olay and SK-II brands. It also provides blades, razors, shave products, appliances, and other grooming products under the Braun, Gillette, and Venus brands. In addition, the company offers toothbrushes, toothpastes, and other oral care products under the Crest and Oral-B brands; and gastrointestinal, pain relief, rapid diagnostics, respiratory, vitamins/minerals/supplements, and other personal health care products under the Metamucil, Neurobion, Pepto-Bismol, and Vicks brand	f	f	\N	109000	https://www.pginvestor.com	21.92	20.27	2.810000	0.3640	180.4300	146.9700	169.0455	186.0000	148.0000	22	2.00	buy	7.4200	0.214000	0.030000	0.200000	0.197390	0.275800	0.512790	0.107460	0.319020	84933001216.00	86951797520.00	85397000000.00	87620000000.00	0.031700	7.0039	6.8879	7.0995	2026-06-30	89541245460.00	87425000000.00	90230069240.00	0.029800	7.3887	6.9500	7.6500	2027-06-30	yfinance+yahooquery	2025-11-01 04:22:36.094312+00	2025-11-01 04:22:37.955478+00	2025-11-01 04:22:37.955478+00
GLD	SPDR Gold Shares	\N	\N	PCX	Unknown	95821635584.00	The Trust holds gold bars and from time to time, issues Baskets in exchange for deposits of gold and distributes gold in connection with redemptions of Baskets. The investment objective of the Trust is for the Shares to reflect the performance of the price of gold bullion, less the Trust’s expenses. The Sponsor believes that, for many investors, the Shares represent a cost-effective investment in gold.	t	t	\N	\N	\N	\N	\N	0.000000	\N	403.3000	236.1300	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:37.401264+00	2025-11-01 04:22:37.959714+00	2025-11-01 04:22:37.959714+00
VNQ	Vanguard Real Estate Index Fund ETF Shares	\N	\N	PCX	Unknown	33012740096.00	The advisor attempts to track the index by investing all, or substantially all, of its assets-either directly or indirectly through a wholly owned subsidiary, which is itself a registered investment company-in the stocks that make up the index, holding each stock in approximately the same proportion as its weighting in the index. The fund is non-diversified.	t	t	\N	\N	\N	32.15	\N	3.860000	\N	99.2000	76.9200	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:37.474591+00	2025-11-01 04:22:37.96325+00	2025-11-01 04:22:37.96325+00
QQQ250815C00420000	\N	\N	\N	Unknown	Unknown	\N		f	f	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:37.530608+00	2025-11-01 04:22:37.966258+00	2025-11-01 04:22:37.966258+00
AMD	Advanced Micro Devices, Inc.	Technology	Semiconductors	NMS	United States	415642714112.00	Advanced Micro Devices, Inc. operates as a semiconductor company worldwide. It operates in three segments: Data Center, Client and Gaming, and Embedded. The company offers artificial intelligence (AI) accelerators, x86 microprocessors, and graphics processing units (GPUs) as standalone devices or as incorporated into accelerated processing units, chipsets, and data center and professional GPUs; and embedded processors and semi-custom system-on-chip (SoC) products, microprocessor and SoC development services and technology, data processing units, field programmable gate arrays (FPGA), system on modules, smart network interface cards, and adaptive SoC products. It provides processors under the AMD Ryzen, AMD Ryzen AI, AMD Ryzen PRO, AMD Ryzen Threadripper, AMD Ryzen Threadripper PRO, AMD Athlon, and AMD PRO A-Series brands; graphics under the AMD Radeon graphics and AMD Embedded Radeon graphics; professional graphics under the AMD Radeon Pro graphics brand; and AI and general-purpose com	f	f	\N	28000	https://www.amd.com	154.29	50.22	\N	1.8940	267.0800	76.4800	241.1053	310.0000	125.1000	45	1.63	buy	5.1000	2.336000	0.317000	2.291000	0.095740	-0.012750	0.509860	0.021900	0.046990	29600000000.00	33090518689.00	31977000000.00	34794000000.00	0.283300	3.9436	3.7000	4.2800	2025-12-31	42175929450.00	34956000000.00	50783000000.00	0.274600	6.3212	5.1500	10.0000	2026-12-31	yfinance+yahooquery	2025-11-01 04:22:37.546216+00	2025-11-01 04:22:37.970258+00	2025-11-01 04:22:37.970258+00
ROKU	Roku, Inc.	Communication Services	Entertainment	NMS	United States	14737482752.00	Roku, Inc., together with its subsidiaries, operates a TV streaming platform in the United States and internationally. The company operates in two segments, Platform and Devices. Its streaming platform allows users to find and access TV shows, movies, news, sports, and others. The company also sells streaming players, Roku-branded TVs, smart home products and services, audio products, and related accessories, as well as offers digital advertising services. Roku, Inc. was incorporated in 2002 and is headquartered in San Jose, California.	f	f	\N	3340	https://www.roku.com	\N	-168.46	\N	2.1270	116.6600	52.4300	106.7917	145.0000	70.0000	24	2.03	buy	-0.6300	\N	0.148000	\N	-0.013990	-0.017680	0.440360	-0.019480	-0.024690	4394959872.00	4695173660.00	4692000000.00	4699941150.00	0.141600	0.2089	0.1200	0.3200	2025-12-31	5292241340.00	5104300000.00	5432000000.00	0.127200	0.8500	0.3800	1.4700	2026-12-31	yfinance+yahooquery	2025-11-01 04:22:41.672156+00	2025-11-01 04:22:42.164532+00	2025-11-01 04:22:42.164532+00
GE	GE Aerospace	Industrials	Aerospace & Defense	NYQ	United States	325884772352.00	General Electric Company, doing business as GE Aerospace, designs and produces commercial and defense aircraft engines, integrated engine components, electric power, and mechanical aircraft systems. The company operates through two reportable segments, Commercial Engines & Services, and Defense & Propulsion Technologies. The Commercial Engines & Services segment designs, develops, manufactures, maintenance, repair, and overhaul (MRO) services of jet engines and sale of spare parts for commercial airframes, business aviation, and aeroderivative applications. The Defense & Propulsion Technologies segment provides designs, develops, manufactures, and MRO services jet engines and avionics and power systems for governments, militaries and commercial airframers, as well as sale of spare parts. This segment also offers small turboprop engines, aeroengine mechanical transmissions, turbines, combustors and controls, additive manufacturing, propeller systems, ignition systems, sensors and engine	f	f	\N	53000	https://www.geaerospace.com	41.30	58.96	0.470000	1.4930	316.6700	159.3600	343.5714	374.0000	279.0000	14	1.38	strong_buy	5.2400	0.193000	0.238000	0.165000	0.183440	0.205980	0.324600	0.049290	0.421310	43949998080.00	41694228800.00	40935000000.00	42628000000.00	0.187200	6.2185	6.0200	6.4000	2025-12-31	46588591610.00	44469000000.00	47494346410.00	0.117400	7.1645	6.5900	7.4800	2026-12-31	yfinance+yahooquery	2025-11-01 04:22:37.678313+00	2025-11-01 04:22:37.973257+00	2025-11-01 04:22:37.973257+00
VTIAX	Vanguard Total Intl Stock Index Admiral	\N	\N	NAS	Unknown	\N	The manager employs an indexing investment approach designed to track the performance of the FTSE Global All Cap ex US Index, a float-adjusted market-capitalization-weighted index designed to measure equity market performance of companies located in developed and emerging markets, excluding the United States. The fund invests all, or substantially all, of its assets in the common stocks included in its target index.	f	t	\N	\N	\N	16.89	\N	2.740000	\N	40.5500	29.9700	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:37.689937+00	2025-11-01 04:22:37.977512+00	2025-11-01 04:22:37.977512+00
AAPL250815P00200000	\N	\N	\N	Unknown	Unknown	\N		f	f	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:37.77094+00	2025-11-01 04:22:37.98052+00	2025-11-01 04:22:37.98052+00
C	Citigroup Inc.	Financial Services	Banks - Diversified	NYQ	United States	181130838016.00	Citigroup Inc., a diversified financial service holding company, provides various financial product and services to consumers, corporations, governments, and institutions. It operates through five segments: Services, Markets, Banking, U.S. Personal Banking, and Wealth. The Services segment includes treasury and trade solutions, which provides cash management, trade, and working capital solutions to multinational corporations, financial institutions, and public sector organizations; and securities services, such as cross-border support for clients, local market expertise, post-trade technologies, data solutions, and various securities services solutions. The Markets segment offers sales and trading services for equities, foreign exchange, rates, spread products, and commodities to corporate, institutional, and public sector clients; and market-making services, including asset classes, risk management solutions, financing, and prime brokerage. The Banking segment includes investment bank	f	f	\N	227000	https://www.citigroup.com	14.22	14.08	2.370000	1.3570	105.5900	55.5100	113.3810	134.0000	82.0000	21	1.82	buy	7.1900	0.231000	0.109000	0.159000	0.194880	0.306060	0.000000	0.005840	0.069950	75383996416.00	86220627370.00	83972000000.00	87054000000.00	0.062600	7.5808	7.1600	7.8200	2025-12-31	88707051860.00	85028487450.00	90390000000.00	0.028800	9.9640	9.0000	10.8900	2026-12-31	yfinance+yahooquery	2025-11-01 04:22:37.819138+00	2025-11-01 04:22:37.984192+00	2025-11-01 04:22:37.984192+00
ZM	Zoom Communications Inc.	Technology	Software - Application	NMS	United States	25242064896.00	Zoom Communications Inc. provides an Artificial Intelligence-first work platform for human connection in the Americas, the Asia Pacific, Europe, the Middle East, and Africa. The company offers Zoom Meetings that offers HD video, voice, chat, and content sharing through mobile devices, desktops, laptops, telephones, and conference room systems; Zoom Phone, a cloud phone system; and Zoom Team Chat enables users to share messages, images, files, and content in desktop, laptop, tablet, and mobile devices. It also provides Zoom Mail and Calendar; Zoom Workflow Automation, a no-code workflow builder that helps users build workflows across Zoom Workplace and third-party applications; Zoom Docs, a modular workspace; Zoom Whiteboard, an interactive canvas; and Zoom Clips for capturing video and screen content. In addition, the company offers Zoom Contact Center, an omnichannel contact center solution; Zoom Revenue Accelerator, a conversation intelligence software for Zoom Meetings and Zoom Phon	f	f	\N	7412	https://www.zoom.com	22.96	16.49	\N	0.7770	92.8000	64.4100	92.7692	115.0000	67.0000	26	2.26	buy	5.2900	0.668000	0.047000	0.637000	0.249940	0.264320	0.763800	0.056410	0.135980	4753620992.00	4832272430.00	4800000000.00	4880801000.00	0.035800	5.8730	5.8100	6.6000	2026-01-31	4995689680.00	4920900000.00	5133355000.00	0.033800	3.4513	2.9000	4.5554	2027-01-31	yfinance+yahooquery	2025-11-01 04:22:37.834883+00	2025-11-01 04:22:37.988212+00	2025-11-01 04:22:37.988212+00
FXNAX	Fidelity U.S. Bond Index	\N	\N	NAS	Unknown	\N	The fund normally invests at least 80% of the fund's assets in bonds included in the Bloomberg U.S. Aggregate Bond Index. Its manager uses statistical sampling techniques based on duration, maturity, interest rate sensitivity, security structure, and credit quality to attempt to replicate the returns of the Bloomberg U.S. Aggregate Bond Index using a smaller number of securities. The fund invests in Fidelity's central funds.	f	t	\N	\N	\N	\N	\N	3.510000	\N	10.6700	10.0900	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:37.913132+00	2025-11-01 04:22:37.992191+00	2025-11-01 04:22:37.992191+00
DJP	iPath Bloomberg Commodity Index Total Return(SM) ETN	\N	\N	PCX	Unknown	\N	The Dow Jones-UBS Commodity Index Total ReturnService Mark (the "index") reflects the returns that are potentially available through an unleveraged investment in the futures contracts on physical commodities comprising the index plus the rate of interest that could be earned on cash collateral invested in specified Treasury Bills. The index is a rolling index rebalancing annually.	t	t	\N	\N	\N	\N	\N	0.000000	\N	36.8000	30.7300	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:39.752492+00	2025-11-01 04:22:42.111226+00	2025-11-01 04:22:42.111226+00
PTON	Peloton Interactive, Inc.	Consumer Cyclical	Leisure	NMS	United States	3025467904.00	Peloton Interactive, Inc. provides fitness and wellness products and services in North America and internationally. The company offers connected fitness products, such as the Peloton Bike, Peloton Bike+, Peloton Tread, Peloton Tread+, and Peloton Row. It also provides all-access, rental, and Peloton App memberships. In addition, the company leases Peloton Bike+ products. The company sells its products through e-commerce and inside sales, retail showrooms, and third-party retailers. Peloton Interactive, Inc. was founded in 2012 and is headquartered in New York, New York.	f	f	\N	2605	https://www.onepeloton.com	\N	-23.42	\N	2.2830	10.8950	4.6300	10.1844	20.0000	5.0000	16	2.05	buy	-0.3100	\N	-0.057000	\N	-0.047740	0.109900	0.509190	0.024710	\N	2490800128.00	2455865240.00	2356000000.00	2538000000.00	-0.014000	0.0636	-0.1300	0.2000	2026-06-30	2501111050.00	2276000000.00	2653720680.00	0.018400	0.1428	-0.1900	0.3900	2027-06-30	yfinance+yahooquery	2025-11-01 04:22:39.762261+00	2025-11-01 04:22:42.120224+00	2025-11-01 04:22:42.120224+00
F	Ford Motor Company	Consumer Cyclical	Auto Manufacturers	NYQ	United States	52037554176.00	Ford Motor Company develops, delivers, and services Ford trucks, sport utility vehicles, commercial vans and cars, and Lincoln luxury vehicles worldwide. It operates through Ford Blue, Ford Model e, Ford Pro, and Ford Credit segments. The company sells Ford and Lincoln internal combustion engine and hybrid vehicles, electric vehicles, service parts, accessories, and digital services for retail customers, as well as develops software. It also sells Ford and Lincoln vehicles, service parts, and accessories through distributors and dealers, as well as through dealerships to commercial fleet customers, daily rental car companies, and governments. In addition, it engages in the vehicle-related financing and leasing activities to and through automotive dealers. Further, the company provides retail installment sale contracts for new and used vehicles; and direct financing leases for new vehicles to retail and commercial customers, such as leasing companies, government entities, daily rental c	f	f	\N	171000	https://www.ford.com	11.22	7.50	4.570000	1.5420	13.9700	8.4400	12.2650	16.0000	9.8000	20	2.91	hold	1.7500	1.727000	0.094000	1.743000	0.024820	0.031460	0.075550	0.008330	0.102950	189587996672.00	174019629610.00	166423000000.00	185512000000.00	0.007600	1.0328	0.9974	1.1200	2025-12-31	174665068930.00	157273506920.00	187630000000.00	0.003700	1.4157	1.1300	1.7700	2026-12-31	yfinance+yahooquery	2025-11-01 04:22:39.783541+00	2025-11-01 04:22:42.124225+00	2025-11-01 04:22:42.124225+00
XOM	Exxon Mobil Corporation	Energy	Oil & Gas Integrated	NYQ	United States	488951808000.00	Exxon Mobil Corporation engages in the exploration and production of crude oil and natural gas in the United States, Guyana, Canada, the United Kingdom, Singapore, France, and internationally. It operates through Upstream, Energy Products, Chemical Products, and Specialty Products segments. The Upstream segment explores for and produces crude oil and natural gas. The Energy Products segment offers fuels, aromatics, and catalysts, as well as licensing services. The Chemical Products segment manufactures and sells petrochemicals, including olefins, polyolefins, and intermediates. The Specialty Products segment offers performance products, including finished lubricants, basestocks, waxes, synthetics, elastomers, and resins. The company is involved in the manufacture, trading, transportation, and sale of crude oil, natural gas, petroleum products, petrochemicals, and other specialty products; and pursuit of lower-emission and business opportunities, including carbon capture and storage, hy	f	f	\N	61000	https://corporate.exxonmobil.com	16.24	14.53	3.450000	0.4840	123.2100	97.8000	126.6512	156.0000	105.0000	25	2.25	buy	7.8700	-0.236000	-0.123000	-0.234000	0.094040	0.117290	0.310200	0.052770	0.118310	329816014848.00	333127577220.00	331513000000.00	334439000000.00	-0.047100	6.8191	6.5500	7.0000	2025-12-31	326032212320.00	284477057440.00	347160223760.00	-0.021300	7.4890	5.9100	10.9300	2026-12-31	yfinance+yahooquery	2025-11-01 04:22:39.932645+00	2025-11-01 04:22:42.128403+00	2025-11-01 04:22:42.128403+00
V	Visa Inc.	Financial Services	Credit Services	NYQ	United States	667032485888.00	Visa Inc. operates as a payment technology company in the United States and internationally. The company operates VisaNet, a transaction processing network that enables authorization, clearing, and settlement of payment transactions. It also offers credit, debit, and prepaid card products; tap to pay, tokenization, and click to pay services; Visa Direct, a solution that facilitates the delivery of funds to eligible cards, bank accounts, and digital wallets; Visa B2B Connect, a multilateral business-to-business cross-border payments network; Visa Cross-Border Solution, a cross-border consumer payments solution; and Visa DPS that provides a range of value-added services, including fraud mitigation, dispute management, data analytics, campaign management, a suite of digital solutions, and contact center services. The company also provides acceptance solutions, which include Cybersource and Authorize.net that provides new and enhanced payment integrations with ecommerce platforms, enabling	f	f	\N	\N	https://www.visa.com	33.44	26.91	0.790000	0.8970	375.5100	290.7600	394.7016	450.0000	305.0000	37	1.62	buy	12.6600	0.130000	0.115000	-0.043000	0.501450	0.657500	0.977650	0.172360	0.520680	40000000000.00	44433891950.00	44080000000.00	45043000000.00	0.110800	12.8068	12.6700	12.9800	2026-09-30	48796348830.00	45741722250.00	50396000000.00	0.098200	14.4280	13.6476	14.9400	2027-09-30	yfinance+yahooquery	2025-11-01 04:22:39.946644+00	2025-11-01 04:22:42.132405+00	2025-11-01 04:22:42.132405+00
SPY250919C00460000	\N	\N	\N	Unknown	Unknown	\N		f	f	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:39.967789+00	2025-11-01 04:22:42.136073+00	2025-11-01 04:22:42.136073+00
FMAGX	Fidelity Magellan	\N	\N	NAS	Unknown	26246696960.00	The fund invests primarily in common stocks. It invests in domestic and foreign issuers. The fund invests in either "growth" stocks or "value" stocks or both. The adviser uses fundamental analysis of factors such as each issuer's financial condition and industry position, as well as market and economic conditions, to select investments.	f	t	\N	\N	\N	3.58	\N	0.160000	\N	16.2700	12.6400	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:40.093057+00	2025-11-01 04:22:42.139072+00	2025-11-01 04:22:42.139072+00
BND	Vanguard Total Bond Market Index Fund	\N	\N	NGM	Unknown	\N	This index measures the performance of a wide spectrum of public, investment-grade, taxable, fixed income securities in the United States-including government, corporate, and international dollar-denominated bonds, as well as mortgage-backed and asset-backed securities-all with maturities of more than 1 year. All of the fund's investments will be selected through the sampling process, and at least 80% of its assets will be invested in bonds held in the index.	t	t	\N	\N	\N	\N	\N	3.760000	\N	75.1500	71.1000	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:40.144965+00	2025-11-01 04:22:42.14492+00	2025-11-01 04:22:42.14492+00
META250919P00450000	\N	\N	\N	Unknown	Unknown	\N		f	f	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:40.22366+00	2025-11-01 04:22:42.148638+00	2025-11-01 04:22:42.148638+00
MSFT250919P00380000	\N	\N	\N	Unknown	Unknown	\N		f	f	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:40.344968+00	2025-11-01 04:22:42.152381+00	2025-11-01 04:22:42.152381+00
VTI	Vanguard Total Stock Market Index Fund ETF Shares	\N	\N	PCX	Unknown	695567187968.00	The fund employs an indexing investment approach designed to track the performance of the index, which represents approximately 100% of the investable U.S. stock market and includes large-, mid-, small-, and micro-cap stocks regularly traded on the New York Stock Exchange and Nasdaq. It invests by sampling the index, meaning that it holds a broadly diversified collection of securities that, in the aggregate, approximates the full index in terms of key characteristics. The fund is non-diversified.	t	t	\N	\N	\N	27.84	\N	1.140000	\N	339.0600	236.4200	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:41.624487+00	2025-11-01 04:22:42.156055+00	2025-11-01 04:22:42.156055+00
NVDA	NVIDIA Corporation	Technology	Semiconductors	NMS	United States	4930024243200.00	NVIDIA Corporation, a computing infrastructure company, provides graphics and compute and networking solutions in the United States, Singapore, Taiwan, China, Hong Kong, and internationally. The Compute & Networking segment includes its Data Centre accelerated computing platforms and artificial intelligence solutions and software; networking; automotive platforms and autonomous and electric vehicle solutions; Jetson for robotics and other embedded platforms; and DGX Cloud computing services. The Graphics segment offers GeForce GPUs for gaming and PCs, the GeForce NOW game streaming service and related infrastructure, and solutions for gaming platforms; Quadro/NVIDIA RTX GPUs for enterprise workstation graphics; virtual GPU or vGPU software for cloud-based visual and virtual computing; automotive platforms for infotainment systems; and Omniverse software for building and operating industrial AI and digital twin applications. It also customized agentic solutions designed in collaboration	f	f	\N	36000	https://www.nvidia.com	57.85	49.15	0.020000	2.1230	212.1900	86.6200	227.1277	320.0000	100.0000	57	1.34	strong_buy	4.1200	0.612000	0.556000	0.592000	0.524140	0.608430	0.698470	0.530940	1.094170	165217992704.00	207245145190.00	201366000000.00	232332000000.00	0.588100	4.5324	4.3200	5.2300	2026-01-31	285062003190.00	226150000000.00	373996462890.00	0.375500	6.6260	4.9100	8.7515	2027-01-31	yfinance+yahooquery	2025-11-01 04:22:41.670184+00	2025-11-01 04:22:42.161294+00	2025-11-01 04:22:42.161294+00
TSLA	Tesla, Inc.	Consumer Cyclical	Auto Manufacturers	NMS	United States	1518435958784.00	Tesla, Inc. designs, develops, manufactures, leases, and sells electric vehicles, and energy generation and storage systems in the United States, China, and internationally. The company operates in two segments, Automotive; and Energy Generation and Storage. The Automotive segment offers electric vehicles, as well as sells automotive regulatory credits; and non-warranty after-sales vehicle, used vehicles, body shop and parts, supercharging, retail merchandise, and vehicle insurance services. This segment also provides sedans and sport utility vehicles through direct and used vehicle sales, a network of Tesla Superchargers, and in-app upgrades; purchase financing and leasing services; services for electric vehicles through its company-owned service locations and Tesla mobile service technicians; and vehicle limited warranties and extended service plans. The Energy Generation and Storage segment engages in the design, manufacture, installation, sale, and leasing of solar energy generatio	f	f	\N	125665	https://www.tesla.com	312.71	140.91	\N	2.0860	488.5400	214.2500	391.3180	600.0000	120.0000	41	2.62	hold	3.2400	-0.371000	0.116000	-0.368000	0.053140	0.066280	0.170070	0.023500	0.067910	95632998400.00	94817800990.00	87335000000.00	99027000000.00	-0.029400	1.6542	1.1600	2.0300	2025-12-31	109299531760.00	96390375940.00	143070000000.00	0.152700	2.2555	0.9600	3.8000	2026-12-31	yfinance+yahooquery	2025-11-01 04:22:41.779054+00	2025-11-01 04:22:42.168505+00	2025-11-01 04:22:42.168505+00
FCNTX	Fidelity Contrafund	\N	\N	NAS	Unknown	\N	The fund normally invests primarily in common stocks. It invests in securities of companies whose value the advisor believes is not fully recognized by the public. The fund invests in domestic and foreign issuers. It invests in either "growth" stocks or "value" stocks or both. The advisor uses fundamental analysis of factors such as each issuer's financial condition and industry position, as well as market and economic conditions to select investments.	f	t	\N	\N	\N	\N	\N	0.050000	\N	25.5400	18.1200	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:41.815367+00	2025-11-01 04:22:42.171534+00	2025-11-01 04:22:42.171534+00
BRK-B	Berkshire Hathaway Inc.	Financial Services	Insurance - Diversified	NYQ	United States	1032401715200.00	Berkshire Hathaway Inc., through its subsidiaries, engages in the insurance, freight rail transportation, and utility businesses. The company provides property, casualty, life, accident, and health insurance and reinsurance; operates railroad systems in North America; generates, transmits, stores, and distributes electricity from natural gas, coal, wind, solar, hydroelectric, nuclear, and geothermal sources; operates natural gas distribution and storage facilities, interstate pipelines, liquefied natural gas facilities, and compressor and meter stations; and holds interest in coal mining assets. It also manufactures boxed chocolates and other confectionery products; specialty chemicals, metal cutting tools, and components for aerospace and power generation applications; prefabricated and site-built residential homes, flooring products; insulation, roofing, and engineered products; building and engineered components; paints and coatings; and bricks and masonry products, as well as offer	f	f	\N	392400	https://www.berkshirehathaway.com	16.37	23.78	\N	0.7700	542.0700	437.9000	519.6667	593.0000	479.0000	3	\N	none	20.0800	-0.593000	-0.012000	-0.592000	0.169980	0.224270	0.229950	0.046810	0.099140	370150998016.00	374693250000.00	371538500000.00	377848000000.00	0.008800	20.6572	20.2000	20.9900	2025-12-31	388933250000.00	380852500000.00	397014000000.00	0.038000	21.6926	20.5300	22.4600	2026-12-31	yfinance+yahooquery	2025-11-01 04:22:41.823931+00	2025-11-01 04:22:42.175796+00	2025-11-01 04:22:42.175796+00
GOOGL	Alphabet Inc.	Communication Services	Internet Content & Information	NMS	United States	3398890160128.00	Alphabet Inc. offers various products and platforms in the United States, Europe, the Middle East, Africa, the Asia-Pacific, Canada, and Latin America. It operates through Google Services, Google Cloud, and Other Bets segments. The Google Services segment provides products and services, including ads, Android, Chrome, devices, Gmail, Google Drive, Google Maps, Google Photos, Google Play, Search, and YouTube. It is also involved in the sale of apps and in-app purchases and digital content in the Google Play and YouTube; and devices, as well as in the provision of YouTube consumer subscription services. The Google Cloud segment offers AI infrastructure, Vertex AI platform, cybersecurity, data and analytics, and other services; Google Workspace that include cloud-based communication and collaboration tools for enterprises, such as Calendar, Gmail, Docs, Drive, and Meet; and other services for enterprise customers. The Other Bets segment sells healthcare-related and internet services. The 	f	f	\N	190167	https://abc.xyz	27.79	31.38	0.300000	1.0000	291.5900	140.5300	305.1822	350.0000	185.0000	54	1.50	strong_buy	8.9600	0.355000	0.159000	0.330000	0.322330	0.305120	0.591720	0.162760	0.354500	385476001792.00	398907746450.00	392268000000.00	402958000000.00	0.139700	10.5773	10.0600	11.0400	2025-12-31	450463542920.00	429200000000.00	484682992730.00	0.129200	11.0005	9.6000	13.1100	2026-12-31	yfinance+yahooquery	2025-11-01 04:22:41.955533+00	2025-11-01 04:22:42.179797+00	2025-11-01 04:22:42.179797+00
JPM	JPMorgan Chase & Co.	Financial Services	Banks - Diversified	NYQ	United States	846930903040.00	JPMorgan Chase & Co. operates as a financial services company worldwide. It operates through three segments: Consumer & Community Banking, Commercial & Investment Bank, and Asset & Wealth Management. The company offers deposit, investment and lending products, cash management, and payments and services; mortgage origination and servicing activities; residential mortgages and home equity loans; and credit cards, auto loans, leases, and travel services to consumers and small businesses through bank branches, ATMs, and digital and telephone banking. It also provides investment banking products and services, including corporate strategy and structure advisory, and equity and debt market capital-raising services, as well as loan origination and syndication; payments; and cash and derivative instruments, risk management solutions, prime brokerage, and research, as well as offers securities services, including custody, fund services, liquidity, and trading services, and data solutions product	f	f	\N	318153	https://www.jpmorganchase.com	15.41	18.59	1.930000	1.1270	318.0100	202.1600	326.4592	370.0000	250.0000	24	2.28	buy	16.7400	0.160000	0.088000	0.116000	0.347210	0.437080	0.000000	0.013230	0.164370	167126007808.00	182739029800.00	181798000000.00	183942000000.00	0.029200	20.0738	19.7955	20.9200	2025-12-31	188777199220.00	185510000000.00	191340000000.00	0.033000	21.2915	20.1700	22.9300	2026-12-31	yfinance+yahooquery	2025-11-01 04:22:42.014267+00	2025-11-01 04:22:42.182767+00	2025-11-01 04:22:42.182767+00
NVDA251017C00800000	\N	\N	\N	Unknown	Unknown	\N		f	f	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:42.062052+00	2025-11-01 04:22:42.186802+00	2025-11-01 04:22:42.186802+00
SPY	SPDR S&P 500 ETF	\N	\N	PCX	Unknown	625982373888.00	The trust seeks to achieve its investment objective by holding a portfolio of the common stocks that are included in the index, with the weight of each stock in the portfolio substantially corresponding to the weight of such stock in the index.	t	t	\N	\N	\N	28.80	\N	1.090000	\N	689.7000	481.8000	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:42.109226+00	2025-11-01 04:22:42.191407+00	2025-11-01 04:22:42.191407+00
QQQ	Invesco QQQ Trust	\N	\N	NGM	Unknown	247287414784.00	To maintain the correspondence between the composition and weights of the securities in the trust (the "securities") and the stocks in the NASDAQ-100 Index®, the adviser adjusts the securities from time to time to conform to periodic changes in the identity and/or relative weights of index securities. The composition and weighting of the securities portion of a portfolio deposit are also adjusted to conform to changes in the index.	t	t	\N	\N	\N	35.47	\N	0.470000	\N	637.0100	402.3900	\N	\N	\N	\N	\N		\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	yfinance+yahooquery	2025-11-01 04:22:43.35747+00	2025-11-01 04:22:43.380434+00	2025-11-01 04:22:43.380434+00
JNJ	Johnson & Johnson	Healthcare	Drug Manufacturers - General	NYQ	United States	455477198848.00	Johnson & Johnson, together with its subsidiaries, engages in the research and development, manufacture, and sale of various products in the healthcare field worldwide. It operates in two segments, Innovative Medicine and MedTech. The Innovative Medicine segment offers products for various therapeutic areas, such as immunology, including rheumatoid arthritis, psoriatic arthritis, inflammatory bowel disease, and psoriasis; infectious diseases comprising HIV/AIDS; neuroscience, consisting of mood disorders, neurodegenerative disorders, and schizophrenia; oncology, such as prostate cancer, hematologic malignancies, lung cancer, and bladder cancer; cardiovascular and metabolism, including thrombosis, diabetes, and macular degeneration; and pulmonary hypertension comprising pulmonary arterial hypertension through retailers, wholesalers, distributors, hospitals, and healthcare professionals for prescription use. The MedTech segment provides electrophysiology products to treat heart rhythm di	f	f	\N	138100	https://www.jnj.com	18.25	17.82	2.750000	0.3920	194.4800	140.6800	199.5552	225.0000	155.0000	23	2.17	buy	10.6000	0.910000	0.068000	0.912000	0.272590	0.302000	0.683550	0.082640	0.336190	92148998144.00	93750694740.00	93418598000.00	94048381250.00	0.055500	10.8643	10.7673	10.9600	2025-12-31	98388937850.00	95163000000.00	99636000000.00	0.049500	11.5065	11.1100	11.9451	2026-12-31	yfinance+yahooquery	2025-11-01 04:22:43.35747+00	2025-11-01 04:22:43.387669+00	2025-11-01 04:22:43.387669+00
AMZN	Amazon.com, Inc.	Consumer Cyclical	Internet Retail	NMS	United States	2609979064320.00	Amazon.com, Inc. engages in the retail sale of consumer products, advertising, and subscriptions service through online and physical stores in North America and internationally. The company operates through three segments: North America, International, and Amazon Web Services (AWS). It also manufactures and sells electronic devices, including Kindle, fire tablets, fire TVs, echo, ring, blink, and eero; and develops and produces media content. In addition, the company offers programs that enable sellers to sell their products in its stores; and programs that allow authors, independent publishers, musicians, filmmakers, Twitch streamers, skill and app developers, and others to publish and sell content. Further, it provides compute, storage, database, analytics, machine learning, and other services, as well as advertising services through programs, such as sponsored ads, display, and video advertising. Additionally, the company offers Amazon Prime, a membership program. The company's prod	f	f	\N	1546000	https://www.amazon.com	34.49	39.71	\N	1.2810	250.5000	161.3800	287.5716	351.8700	240.0000	61	1.29	strong_buy	6.1500	0.333000	0.133000	0.347000	0.105400	0.114320	0.496070	0.076990	0.247700	670038032384.00	713614657730.00	699478000000.00	718002000000.00	0.118600	6.9404	5.7200	7.6300	2025-12-31	789960971830.00	762630543650.00	812864900000.00	0.107000	7.7618	5.7000	8.7989	2026-12-31	yfinance+yahooquery	2025-11-01 04:22:43.379324+00	2025-11-01 04:22:43.392144+00	2025-11-01 04:22:43.392144+00
\.


--
-- Data for Name: correlation_calculations; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.correlation_calculations (id, portfolio_id, duration_days, calculation_date, overall_correlation, correlation_concentration_score, effective_positions, data_quality, min_position_value, min_portfolio_weight, filter_mode, correlation_threshold, positions_included, positions_excluded, created_at) FROM stdin;
\.


--
-- Data for Name: correlation_cluster_positions; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.correlation_cluster_positions (id, cluster_id, position_id, symbol, value, portfolio_percentage, correlation_to_cluster) FROM stdin;
\.


--
-- Data for Name: correlation_clusters; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.correlation_clusters (id, correlation_calculation_id, cluster_number, nickname, avg_correlation, total_value, portfolio_percentage, created_at) FROM stdin;
\.


--
-- Data for Name: export_history; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.export_history (id, user_id, export_type, export_format, file_name, file_size_bytes, created_at) FROM stdin;
\.


--
-- Data for Name: factor_correlations; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.factor_correlations (id, factor_1_id, factor_2_id, correlation, calculation_date, lookback_days, decay_factor, data_points, created_at) FROM stdin;
\.


--
-- Data for Name: factor_definitions; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.factor_definitions (id, name, description, factor_type, calculation_method, etf_proxy, display_order, is_active, created_at, updated_at) FROM stdin;
c92dcfc0-0fca-4972-bfd7-bc5f9467f0ee	Market Beta	Sensitivity to overall market movements (S&P 500)	style	rolling_regression	SPY	0	t	2025-11-01 07:58:22.908428+00	2025-11-01 07:58:22.908428+00
5f683c38-866f-43f5-b45a-d717c2d9500c	Momentum	12-month price momentum excluding most recent month	style	price_momentum	MTUM	1	t	2025-11-01 07:58:22.912427+00	2025-11-01 07:58:22.912427+00
1369701f-7f84-40cf-9298-3ac55008b7ef	Value	Exposure to value stocks (low P/B, P/E ratios)	style	fundamental_ratios	VTV	2	t	2025-11-01 07:58:22.915982+00	2025-11-01 07:58:22.915982+00
7ab27757-d91a-458c-8e27-ebd6164087c2	Growth	Exposure to growth stocks (high earnings growth)	style	earnings_growth	VUG	3	t	2025-11-01 07:58:22.918981+00	2025-11-01 07:58:22.918981+00
953b5da3-ea52-4ce4-bc43-f34c94e38402	Quality	Exposure to high-quality companies (high ROE, low debt)	style	quality_metrics	QUAL	4	t	2025-11-01 07:58:22.922981+00	2025-11-01 07:58:22.922981+00
6c222977-eed2-4238-aaf1-d0c9282195e0	Size	Exposure to small-cap vs large-cap stocks	style	market_cap	IWM	5	t	2025-11-01 07:58:22.926982+00	2025-11-01 07:58:22.926982+00
2d671713-106d-4b89-930d-c61966144e01	Low Volatility	Exposure to low volatility stocks	style	realized_volatility	USMV	6	t	2025-11-01 07:58:22.930156+00	2025-11-01 07:58:22.930156+00
a4bbff9e-c545-4309-9094-24431a6a9113	Short Interest	Exposure to heavily shorted stocks	style	short_interest_ratio	\N	7	t	2025-11-01 07:58:22.934666+00	2025-11-01 07:58:22.934666+00
\.


--
-- Data for Name: factor_exposures; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.factor_exposures (id, portfolio_id, factor_id, calculation_date, exposure_value, exposure_dollar, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: fund_holdings; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.fund_holdings (id, fund_symbol, holding_symbol, holding_name, weight, shares, market_value, data_source, last_updated, data_quality, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: market_data_cache; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.market_data_cache (id, symbol, date, open, high, low, close, volume, sector, industry, exchange, country, market_cap, data_source, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: market_risk_scenarios; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.market_risk_scenarios (id, portfolio_id, scenario_type, scenario_value, predicted_pnl, calculation_date, created_at) FROM stdin;
\.


--
-- Data for Name: modeling_session_snapshots; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.modeling_session_snapshots (id, session_id, user_id, name, status, base_portfolio_snapshot, modified_portfolio_snapshot, changes, impact_summary, created_at, updated_at, completed_at) FROM stdin;
\.


--
-- Data for Name: pairwise_correlations; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.pairwise_correlations (id, correlation_calculation_id, symbol_1, symbol_2, correlation_value, data_points, statistical_significance) FROM stdin;
\.


--
-- Data for Name: portfolio_snapshots; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.portfolio_snapshots (id, portfolio_id, snapshot_date, total_value, cash_value, long_value, short_value, gross_exposure, net_exposure, daily_pnl, daily_return, cumulative_pnl, portfolio_delta, portfolio_gamma, portfolio_theta, portfolio_vega, num_positions, num_long_positions, num_short_positions, equity_balance, realized_volatility_21d, realized_volatility_63d, expected_volatility_21d, volatility_trend, volatility_percentile, beta_calculated_90d, beta_calculated_90d_r_squared, beta_calculated_90d_observations, beta_provider_1y, beta_portfolio_regression, sector_exposure, hhi, effective_num_positions, top_3_concentration, top_10_concentration, target_price_return_eoy, target_price_return_next_year, target_price_downside_return, target_price_upside_eoy_dollars, target_price_upside_next_year_dollars, target_price_downside_dollars, target_price_coverage_pct, target_price_positions_count, target_price_total_positions, target_price_last_updated, created_at) FROM stdin;
594848e6-dc0c-44bd-98e4-0cea5b28e221	e23ab931-a033-edfe-ed4f-9d02474780b4	2025-11-01	0.00	0.00	0.00	0.00	0.00	0.00	\N	\N	\N	\N	\N	\N	\N	29	0	0	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8.7616	\N	\N	249705.09	\N	\N	44.8276	13	29	2025-11-01 08:04:24.460273+00	2025-11-01 08:02:48.935743+00
bfb1d60e-38e3-4dad-900a-aad3eb8a55c5	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	2025-11-01	0.00	0.00	0.00	0.00	0.00	0.00	\N	\N	\N	\N	\N	\N	\N	16	0	0	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	13.3230	\N	\N	64616.54	\N	\N	56.2500	9	16	2025-11-01 08:32:28.682929+00	2025-11-01 08:31:41.085452+00
\.


--
-- Data for Name: portfolio_target_prices; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.portfolio_target_prices (id, portfolio_id, position_id, symbol, position_type, target_price_eoy, target_price_next_year, downside_target_price, current_price, current_implied_vol, expected_return_eoy, expected_return_next_year, downside_return, target_upside_eoy_value, target_upside_next_year_value, target_downside_value, position_weight, contribution_to_portfolio_return, contribution_to_portfolio_risk, price_updated_at, analyst_notes, data_source, created_by, created_at, updated_at) FROM stdin;
799523a0-8de5-431e-9e54-a1b99067ad61	e23ab931-a033-edfe-ed4f-9d02474780b4	c0415f8d-fe2d-b605-adea-e0a62fbb3402	AAPL	LONG	256.0066	\N	\N	225.0000	\N	13.7807	\N	\N	12402.64	\N	\N	\N	\N	\N	2025-11-01 08:02:48.742972+00	\N	\N	9dacfb0f-2123-7a94-debc-0f982b90d845	2025-11-01 08:02:48.75627+00	2025-11-01 08:02:48.75627+00
5ff0786d-484f-478c-9a80-aa120f31fefc	e23ab931-a033-edfe-ed4f-9d02474780b4	f15a6f13-5ce6-c94d-a3d2-79c98a7a1e18	JPM	LONG	326.4592	\N	\N	170.0000	\N	92.0348	\N	\N	54760.72	\N	\N	\N	\N	\N	2025-11-01 08:02:48.866545+00	\N	\N	9dacfb0f-2123-7a94-debc-0f982b90d845	2025-11-01 08:02:48.871155+00	2025-11-01 08:02:48.871155+00
6929e464-3cc6-437e-b436-2ffff39f6aec	e23ab931-a033-edfe-ed4f-9d02474780b4	9fb75e5f-5ca7-ee0d-f895-23aa1b1f110f	GOOGL	LONG	263.1508	\N	\N	160.0000	\N	64.4693	\N	\N	51575.40	\N	\N	\N	\N	\N	2025-11-01 08:02:48.844188+00	\N	\N	9dacfb0f-2123-7a94-debc-0f982b90d845	2025-11-01 08:02:48.869447+00	2025-11-01 08:02:48.869447+00
dfc2d4ee-5fd1-4bd8-b7f5-7cc2544563c4	e23ab931-a033-edfe-ed4f-9d02474780b4	d7e0c28e-4d39-05bf-4c35-2eeea852694b	BRK-B	LONG	519.6667	\N	\N	440.0000	\N	18.1061	\N	\N	14340.01	\N	\N	\N	\N	\N	2025-11-01 08:02:48.894294+00	\N	\N	9dacfb0f-2123-7a94-debc-0f982b90d845	2025-11-01 08:02:48.917815+00	2025-11-01 08:02:48.917815+00
7ed20dbd-49b8-45ba-9ba6-860f19a3d8a8	e23ab931-a033-edfe-ed4f-9d02474780b4	b498f201-32a4-9587-1f9b-ecc36eff7339	MSFT	LONG	621.0688	\N	\N	420.0000	\N	47.8735	\N	\N	40213.76	\N	\N	\N	\N	\N	2025-11-01 08:02:48.915983+00	\N	\N	9dacfb0f-2123-7a94-debc-0f982b90d845	2025-11-01 08:02:48.920815+00	2025-11-01 08:02:48.920815+00
98b46540-588c-474c-a38c-9b492a90c791	e23ab931-a033-edfe-ed4f-9d02474780b4	48c795d9-acf6-470c-4961-cb86f7ccdce0	AMZN	LONG	267.9206	\N	\N	170.0000	\N	57.6004	\N	\N	47001.89	\N	\N	\N	\N	\N	2025-11-01 08:03:00.424897+00	\N	\N	9dacfb0f-2123-7a94-debc-0f982b90d845	2025-11-01 08:03:00.427896+00	2025-11-01 08:03:00.427896+00
ec26cb26-d82a-4366-9a97-f1d2e8d0306a	e23ab931-a033-edfe-ed4f-9d02474780b4	7afe826a-72d8-7dd0-829e-c696e34b57fe	JNJ	LONG	199.5552	\N	\N	160.0000	\N	24.7220	\N	\N	12262.11	\N	\N	\N	\N	\N	2025-11-01 08:03:12.411872+00	\N	\N	9dacfb0f-2123-7a94-debc-0f982b90d845	2025-11-01 08:03:12.413869+00	2025-11-01 08:03:12.413869+00
b1d4f02c-c49d-4a8b-8942-64b4bd5c87db	e23ab931-a033-edfe-ed4f-9d02474780b4	dcfa17de-04c3-a149-1f1c-337fc301baa0	NVDA	LONG	223.6190	\N	\N	700.0000	\N	-68.0544	\N	\N	-33346.67	\N	\N	\N	\N	\N	2025-11-01 08:03:24.429412+00	\N	\N	9dacfb0f-2123-7a94-debc-0f982b90d845	2025-11-01 08:03:24.432413+00	2025-11-01 08:03:24.432413+00
3ae67c3a-2ec4-4d13-acbb-dc5b33c2429c	e23ab931-a033-edfe-ed4f-9d02474780b4	1409d784-877d-176a-5126-7830a3d2d256	META	LONG	868.3053	\N	\N	530.0000	\N	63.8312	\N	\N	30447.48	\N	\N	\N	\N	\N	2025-11-01 08:03:36.425854+00	\N	\N	9dacfb0f-2123-7a94-debc-0f982b90d845	2025-11-01 08:03:36.428853+00	2025-11-01 08:03:36.428853+00
fe2d1571-c09f-4962-aeee-a66f9342e97d	e23ab931-a033-edfe-ed4f-9d02474780b4	70e53e12-b75e-4cff-8bbd-5b572da5a6fc	HD	LONG	438.8485	\N	\N	350.0000	\N	25.3853	\N	\N	11106.06	\N	\N	\N	\N	\N	2025-11-01 08:03:48.421232+00	\N	\N	9dacfb0f-2123-7a94-debc-0f982b90d845	2025-11-01 08:03:48.424357+00	2025-11-01 08:03:48.424357+00
99d80420-4e23-44ec-87f2-07a1f1055dea	e23ab931-a033-edfe-ed4f-9d02474780b4	ff7dc307-b919-a6a6-2db4-531cbfd5e08b	V	LONG	394.7827	\N	\N	268.0000	\N	47.3070	\N	\N	21553.06	\N	\N	\N	\N	\N	2025-11-01 08:04:00.438615+00	\N	\N	9dacfb0f-2123-7a94-debc-0f982b90d845	2025-11-01 08:04:00.441536+00	2025-11-01 08:04:00.441536+00
a03df8f3-4f4a-4e95-bf6f-0b50fad7738d	e23ab931-a033-edfe-ed4f-9d02474780b4	68701396-33d1-79c5-fd76-f3e227d38081	UNH	LONG	385.0000	\N	\N	545.0000	\N	-29.3578	\N	\N	-13600.00	\N	\N	\N	\N	\N	2025-11-01 08:04:12.418625+00	\N	\N	9dacfb0f-2123-7a94-debc-0f982b90d845	2025-11-01 08:04:12.421626+00	2025-11-01 08:04:12.421626+00
938a8260-006a-4469-bef1-0ba96a9ad113	e23ab931-a033-edfe-ed4f-9d02474780b4	aafea4f3-6ae7-8475-2160-39bb316037dc	PG	LONG	168.9545	\N	\N	165.0000	\N	2.3967	\N	\N	988.63	\N	\N	\N	\N	\N	2025-11-01 08:04:24.429252+00	\N	\N	9dacfb0f-2123-7a94-debc-0f982b90d845	2025-11-01 08:04:24.432201+00	2025-11-01 08:04:24.432201+00
1ea93daa-75c3-4cf5-8c99-dcaf8ad13da7	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	ddd4b332-4b4b-ca49-17bb-e998404ed581	AAPL	LONG	274.9676	\N	\N	225.0000	\N	22.2078	\N	\N	4247.25	\N	\N	\N	\N	\N	2025-11-01 08:31:40.900967+00	\N	\N	fd5f083c-6ffc-df32-89ca-a4044b5723f5	2025-11-01 08:31:40.905964+00	2025-11-01 08:31:40.905964+00
04832c2d-ac2a-4668-a959-963948e42318	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	43d5f997-48d7-5e4b-aa64-07f58ff66c32	TSLA	LONG	391.3180	\N	\N	255.0000	\N	53.4580	\N	\N	9542.26	\N	\N	\N	\N	\N	2025-11-01 08:31:40.927499+00	\N	\N	fd5f083c-6ffc-df32-89ca-a4044b5723f5	2025-11-01 08:31:40.933499+00	2025-11-01 08:31:40.933499+00
68bf6a56-d3fe-41e2-9650-e37009d15139	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	b9d5970d-6ec4-b3b1-9044-2e5f8c37376f	NVDA	LONG	227.1277	\N	\N	700.0000	\N	-67.5532	\N	\N	-11821.81	\N	\N	\N	\N	\N	2025-11-01 08:31:40.964181+00	\N	\N	fd5f083c-6ffc-df32-89ca-a4044b5723f5	2025-11-01 08:31:40.996842+00	2025-11-01 08:31:40.996842+00
72d2c396-14cc-49fa-b5d8-1e41f8fde5c9	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	ad93ac42-91f2-bd2c-b835-5da6b6bc44bb	MSFT	LONG	625.1688	\N	\N	420.0000	\N	48.8497	\N	\N	9232.60	\N	\N	\N	\N	\N	2025-11-01 08:31:40.994842+00	\N	\N	fd5f083c-6ffc-df32-89ca-a4044b5723f5	2025-11-01 08:31:41.001086+00	2025-11-01 08:31:41.001086+00
2c1c788d-801f-4ba4-8f43-37821f7727cf	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	16875284-3b5b-d473-1c36-eb549851db22	GOOGL	LONG	305.1822	\N	\N	160.0000	\N	90.7389	\N	\N	16695.95	\N	\N	\N	\N	\N	2025-11-01 08:31:41.05745+00	\N	\N	fd5f083c-6ffc-df32-89ca-a4044b5723f5	2025-11-01 08:31:41.065452+00	2025-11-01 08:31:41.065452+00
29d99e4a-26de-4a20-86e8-1b65042bdb96	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	2c8449ca-b800-c153-9f4b-0b8ea7c2fc08	AMZN	LONG	287.5716	\N	\N	170.0000	\N	69.1598	\N	\N	12932.88	\N	\N	\N	\N	\N	2025-11-01 08:31:52.573802+00	\N	\N	fd5f083c-6ffc-df32-89ca-a4044b5723f5	2025-11-01 08:31:52.576803+00	2025-11-01 08:31:52.576803+00
0d485359-872f-4204-be7a-b25d3aa0e065	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	582275ae-3305-5097-5452-da918bc51cb2	JNJ	LONG	199.5552	\N	\N	160.0000	\N	24.7220	\N	\N	4153.30	\N	\N	\N	\N	\N	2025-11-01 08:32:04.60275+00	\N	\N	fd5f083c-6ffc-df32-89ca-a4044b5723f5	2025-11-01 08:32:04.606404+00	2025-11-01 08:32:04.606404+00
34abd000-791b-417c-935a-2085c7aa2239	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	b53331c7-7399-52ca-d2c6-0a2f1ec847e2	V	LONG	394.7016	\N	\N	268.0000	\N	47.2767	\N	\N	6335.08	\N	\N	\N	\N	\N	2025-11-01 08:32:16.586361+00	\N	\N	fd5f083c-6ffc-df32-89ca-a4044b5723f5	2025-11-01 08:32:16.588361+00	2025-11-01 08:32:16.588361+00
8e980261-b415-49bf-af1e-f52c1d4271cc	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	17c52141-8347-ccac-0e79-93b0b182c48f	JPM	LONG	326.4592	\N	\N	170.0000	\N	92.0348	\N	\N	13299.03	\N	\N	\N	\N	\N	2025-11-01 08:32:28.596994+00	\N	\N	fd5f083c-6ffc-df32-89ca-a4044b5723f5	2025-11-01 08:32:28.598993+00	2025-11-01 08:32:28.598993+00
\.


--
-- Data for Name: portfolios; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.portfolios (id, user_id, name, description, currency, equity_balance, created_at, updated_at, deleted_at) FROM stdin;
1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	fd5f083c-6ffc-df32-89ca-a4044b5723f5	Demo Individual Investor Portfolio	Individual investor with 401k, IRA, and taxable accounts. Core holdings with growth tilt, heavy mutual fund allocation.	USD	485000.00	2025-11-01 07:58:23.603054+00	2025-11-01 07:58:23.603054+00	\N
e23ab931-a033-edfe-ed4f-9d02474780b4	9dacfb0f-2123-7a94-debc-0f982b90d845	Demo High Net Worth Investor Portfolio	High net worth individual with access to private investments. Diversified across public markets with alternative investments.	USD	2850000.00	2025-11-01 07:58:24.516545+00	2025-11-01 07:58:24.516545+00	\N
fcd71196-e93e-f000-5a74-31a9eead3118	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Demo Hedge Fund Style Investor Portfolio	Sophisticated trader with derivatives access. Market-neutral with volatility trading and options overlay.	USD	3200000.00	2025-11-01 07:58:26.44343+00	2025-11-01 07:58:26.44343+00	\N
\.


--
-- Data for Name: position_factor_exposures; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.position_factor_exposures (id, position_id, factor_id, calculation_date, exposure_value, quality_flag, created_at) FROM stdin;
\.


--
-- Data for Name: position_greeks; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.position_greeks (id, position_id, calculation_date, delta, gamma, theta, vega, rho, delta_dollars, gamma_dollars, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: position_interest_rate_betas; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.position_interest_rate_betas (id, portfolio_id, position_id, ir_beta, r_squared, calculation_date, created_at) FROM stdin;
\.


--
-- Data for Name: position_market_betas; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.position_market_betas (id, portfolio_id, position_id, calc_date, beta, alpha, r_squared, std_error, p_value, observations, window_days, method, market_index, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: position_tags; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.position_tags (id, position_id, tag_id, assigned_at, assigned_by) FROM stdin;
9a2f8811-ba71-4400-b9e0-5c2b7822aadf	ddd4b332-4b4b-ca49-17bb-e998404ed581	eeb2dc69-18a1-4fe0-b448-679923dcb79b	2025-11-01 03:58:23.593826+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
5da8e7cc-0006-4ce0-8387-0f96f184bce4	ddd4b332-4b4b-ca49-17bb-e998404ed581	23c7f0c0-c741-42b6-94a5-2f4f8844b97c	2025-11-01 03:58:23.668482+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
0dc10e99-2787-444f-a508-b20f72f9c51f	ddd4b332-4b4b-ca49-17bb-e998404ed581	771afdd9-12a5-4b73-938e-ee43f294dc3b	2025-11-01 03:58:23.690026+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
b7c3c8a9-f4eb-4c93-b940-bd5247211ec2	ad93ac42-91f2-bd2c-b835-5da6b6bc44bb	eeb2dc69-18a1-4fe0-b448-679923dcb79b	2025-11-01 03:58:23.690026+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
56913b1a-e779-4004-86bf-e213d109bc9f	ad93ac42-91f2-bd2c-b835-5da6b6bc44bb	23c7f0c0-c741-42b6-94a5-2f4f8844b97c	2025-11-01 03:58:23.746786+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
14fc3889-da67-40f9-befd-6799471f4a41	ad93ac42-91f2-bd2c-b835-5da6b6bc44bb	771afdd9-12a5-4b73-938e-ee43f294dc3b	2025-11-01 03:58:23.766442+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
2c40a8ba-fed5-4719-87f8-25c12a49677e	2c8449ca-b800-c153-9f4b-0b8ea7c2fc08	eeb2dc69-18a1-4fe0-b448-679923dcb79b	2025-11-01 03:58:23.766442+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
2f2998db-7a22-4840-8238-cea5bcd6f6bc	2c8449ca-b800-c153-9f4b-0b8ea7c2fc08	23c7f0c0-c741-42b6-94a5-2f4f8844b97c	2025-11-01 03:58:23.805682+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
5cdad455-e5cf-4c56-8c0f-d59da8ae3335	2c8449ca-b800-c153-9f4b-0b8ea7c2fc08	771afdd9-12a5-4b73-938e-ee43f294dc3b	2025-11-01 03:58:23.824464+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
84ab5a0b-9b9a-469b-be1c-9f46b6f16b2a	16875284-3b5b-d473-1c36-eb549851db22	eeb2dc69-18a1-4fe0-b448-679923dcb79b	2025-11-01 03:58:23.824464+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
d83b2f89-b0fa-454c-a4c4-05a3fd839afc	16875284-3b5b-d473-1c36-eb549851db22	23c7f0c0-c741-42b6-94a5-2f4f8844b97c	2025-11-01 03:58:23.864343+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
2a0775a3-ac02-49ca-99b6-b7a27ab0ec7f	16875284-3b5b-d473-1c36-eb549851db22	771afdd9-12a5-4b73-938e-ee43f294dc3b	2025-11-01 03:58:23.882416+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
4a37b5d2-14ec-4159-b447-f5e69233ac6c	43d5f997-48d7-5e4b-aa64-07f58ff66c32	23c7f0c0-c741-42b6-94a5-2f4f8844b97c	2025-11-01 03:58:23.882416+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
9a0a4c6a-bdcd-4875-9e05-f86055f04e53	43d5f997-48d7-5e4b-aa64-07f58ff66c32	771afdd9-12a5-4b73-938e-ee43f294dc3b	2025-11-01 03:58:23.920536+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
b0ffd132-17e7-43a2-a2dc-70ac117f5ed9	b9d5970d-6ec4-b3b1-9044-2e5f8c37376f	23c7f0c0-c741-42b6-94a5-2f4f8844b97c	2025-11-01 03:58:23.920536+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
409575e0-a58b-42fc-95ee-6a10e00f35c8	b9d5970d-6ec4-b3b1-9044-2e5f8c37376f	771afdd9-12a5-4b73-938e-ee43f294dc3b	2025-11-01 03:58:23.957057+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
fc0185ae-7e30-4196-869d-b276ecb65fa7	582275ae-3305-5097-5452-da918bc51cb2	c4b8febf-753d-4cf7-86e5-2181cd57539f	2025-11-01 03:58:23.957057+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
c3eb9923-c682-41a0-8fe0-8c49f2d860e7	582275ae-3305-5097-5452-da918bc51cb2	771afdd9-12a5-4b73-938e-ee43f294dc3b	2025-11-01 03:58:23.995145+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
48fc37fe-ec57-4f8d-a38f-f08d8425372b	17c52141-8347-ccac-0e79-93b0b182c48f	c4b8febf-753d-4cf7-86e5-2181cd57539f	2025-11-01 03:58:23.995145+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
fee962a1-5ee5-400a-b864-6471931595d2	17c52141-8347-ccac-0e79-93b0b182c48f	771afdd9-12a5-4b73-938e-ee43f294dc3b	2025-11-01 03:58:24.030897+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
ec633665-4cfd-4de1-be53-076fa2990381	b53331c7-7399-52ca-d2c6-0a2f1ec847e2	eeb2dc69-18a1-4fe0-b448-679923dcb79b	2025-11-01 03:58:24.030897+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
8aaa4971-46cc-4e30-ac36-302bd84af74b	b53331c7-7399-52ca-d2c6-0a2f1ec847e2	771afdd9-12a5-4b73-938e-ee43f294dc3b	2025-11-01 03:58:24.065177+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
90ae9ce9-79d5-4233-b95e-242d6d5c6eee	9a1ef980-a831-f29f-9cb5-03e978510bcd	eeb2dc69-18a1-4fe0-b448-679923dcb79b	2025-11-01 03:58:24.065177+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
9a4ff3c5-9d67-4422-a264-32e458e7267f	9a1ef980-a831-f29f-9cb5-03e978510bcd	9516be79-1ac1-41d8-8db4-52d6083044ff	2025-11-01 03:58:24.103783+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
df137479-e2b7-4386-b7bb-e0ae62134de6	9a1ef980-a831-f29f-9cb5-03e978510bcd	771afdd9-12a5-4b73-938e-ee43f294dc3b	2025-11-01 03:58:24.122115+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
aa76c750-1ca8-458a-afcc-ccfcadded4fc	408b33a1-2a41-c8f6-1bc1-486f7cd239b8	eeb2dc69-18a1-4fe0-b448-679923dcb79b	2025-11-01 03:58:24.122115+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
a3e78e22-54bf-490c-8717-302d529a92f4	408b33a1-2a41-c8f6-1bc1-486f7cd239b8	89c367ba-a3f7-4592-84a1-1b2ad080b82d	2025-11-01 03:58:24.164187+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
a50ed6b6-ee4a-4f36-8405-30a4d19d3208	408b33a1-2a41-c8f6-1bc1-486f7cd239b8	771afdd9-12a5-4b73-938e-ee43f294dc3b	2025-11-01 03:58:24.183103+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
7365f513-d91b-4fc5-9db7-67620cc7247b	d29ebb59-d2b1-b17a-f512-cbca791646da	eeb2dc69-18a1-4fe0-b448-679923dcb79b	2025-11-01 03:58:24.183103+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
bb6bf9b7-be45-4c32-968e-a37133a593ba	d29ebb59-d2b1-b17a-f512-cbca791646da	ccb572af-1228-4aab-9b79-3b9a10836c74	2025-11-01 03:58:24.2222+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
791bf8fa-9a18-4fc8-a28a-82889b63eb50	d29ebb59-d2b1-b17a-f512-cbca791646da	771afdd9-12a5-4b73-938e-ee43f294dc3b	2025-11-01 03:58:24.241072+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
2463e8b4-c74a-4810-a10a-c36dc8cd9a89	531d2a35-0ddc-65b7-9444-2ff23d40f846	eeb2dc69-18a1-4fe0-b448-679923dcb79b	2025-11-01 03:58:24.241072+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
145f12c0-9827-462d-a90f-1200ea5c2d82	531d2a35-0ddc-65b7-9444-2ff23d40f846	ccb572af-1228-4aab-9b79-3b9a10836c74	2025-11-01 03:58:24.280722+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
e1613463-d880-459a-b421-b4c8fab5941d	531d2a35-0ddc-65b7-9444-2ff23d40f846	771afdd9-12a5-4b73-938e-ee43f294dc3b	2025-11-01 03:58:24.304268+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
f01e5b9f-707f-4354-bd4e-5ef4b6d30455	6fb17e84-682f-893a-a73d-1eaee18a072b	eeb2dc69-18a1-4fe0-b448-679923dcb79b	2025-11-01 03:58:24.304268+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
55ec0458-632b-447f-a7b3-45a6b7f2c2f3	6fb17e84-682f-893a-a73d-1eaee18a072b	4cc1fd73-f967-46bf-860c-23fefac8f881	2025-11-01 03:58:24.350576+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
a3e5aa53-a9f7-4593-a3ff-b42cf3fe5ef0	6fb17e84-682f-893a-a73d-1eaee18a072b	771afdd9-12a5-4b73-938e-ee43f294dc3b	2025-11-01 03:58:24.370345+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
f8d2776e-013f-48c4-b8d9-2e10b5563744	9c7e4ad8-dd19-af4c-5495-1cf816079596	eeb2dc69-18a1-4fe0-b448-679923dcb79b	2025-11-01 03:58:24.370345+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
35b0fca9-d06e-4d96-ac51-605513198a65	9c7e4ad8-dd19-af4c-5495-1cf816079596	9e60772c-eed3-4dfd-8a47-e006f6f61e7d	2025-11-01 03:58:24.417097+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
a6f2d411-2897-4c36-95f8-3ca4cc28b0f9	9c7e4ad8-dd19-af4c-5495-1cf816079596	771afdd9-12a5-4b73-938e-ee43f294dc3b	2025-11-01 03:58:24.437099+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
c18a6c1b-e67b-4446-9c5e-3abcabc8ae6d	82e18b81-5e1f-8dc6-d115-6a4acaa78a0a	eeb2dc69-18a1-4fe0-b448-679923dcb79b	2025-11-01 03:58:24.437099+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
860440df-1ba5-4e71-8c3b-e069af625872	82e18b81-5e1f-8dc6-d115-6a4acaa78a0a	15b8bef6-c7bc-4dc7-8775-1bd6a48d1b20	2025-11-01 03:58:24.477872+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
e418b0c5-aec0-4086-8148-3ca1de4598f5	82e18b81-5e1f-8dc6-d115-6a4acaa78a0a	771afdd9-12a5-4b73-938e-ee43f294dc3b	2025-11-01 03:58:24.496911+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
40212f49-0b0b-478b-a5f5-b2f5014ccb70	b036d715-1392-2cb1-7018-d8f296ef35c3	0fcb4eef-adc9-47a6-b005-7492ee16d054	2025-11-01 03:58:24.496911+00	9dacfb0f-2123-7a94-debc-0f982b90d845
8e93559f-64f4-4ad8-9bfc-4e2c5435e2ce	b036d715-1392-2cb1-7018-d8f296ef35c3	503c0196-5ce5-4c7a-891e-da1555788131	2025-11-01 03:58:24.548106+00	9dacfb0f-2123-7a94-debc-0f982b90d845
6ff9b072-bba0-4f9c-8a28-06534d50f109	b036d715-1392-2cb1-7018-d8f296ef35c3	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:24.567724+00	9dacfb0f-2123-7a94-debc-0f982b90d845
bc2695ce-15d8-4a0e-ae32-3f6ecfa1087b	7f3f9dda-d295-edd9-48a3-61532b4ad804	0fcb4eef-adc9-47a6-b005-7492ee16d054	2025-11-01 03:58:24.567724+00	9dacfb0f-2123-7a94-debc-0f982b90d845
c8e356c5-32a1-43b4-b9aa-70891f852b8d	7f3f9dda-d295-edd9-48a3-61532b4ad804	f0931dc9-1799-4215-99ce-f891e8344810	2025-11-01 03:58:24.619251+00	9dacfb0f-2123-7a94-debc-0f982b90d845
eb4c1582-8559-4685-b5bc-4c77bcb14a6b	7f3f9dda-d295-edd9-48a3-61532b4ad804	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:24.642124+00	9dacfb0f-2123-7a94-debc-0f982b90d845
bee9498c-5efd-4b60-9ecc-f068e2e57c63	cbdba890-4eb2-19ad-eff6-a82281c27067	0fcb4eef-adc9-47a6-b005-7492ee16d054	2025-11-01 03:58:24.642124+00	9dacfb0f-2123-7a94-debc-0f982b90d845
bf0b0411-b980-4c25-bd90-8b6de91feff4	cbdba890-4eb2-19ad-eff6-a82281c27067	5f8f69ec-84cb-4928-95a7-56f1ff1b41eb	2025-11-01 03:58:24.687664+00	9dacfb0f-2123-7a94-debc-0f982b90d845
b1db6e38-6c99-46b7-b5bd-fa530fe9a2ca	cbdba890-4eb2-19ad-eff6-a82281c27067	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:24.707703+00	9dacfb0f-2123-7a94-debc-0f982b90d845
36289c2f-2620-4b11-a0c1-8a33d544a388	c0415f8d-fe2d-b605-adea-e0a62fbb3402	0fcb4eef-adc9-47a6-b005-7492ee16d054	2025-11-01 03:58:24.707703+00	9dacfb0f-2123-7a94-debc-0f982b90d845
50c59cf5-1297-4c7b-aae1-4a66e68f94a7	c0415f8d-fe2d-b605-adea-e0a62fbb3402	ffecdffb-83df-45f6-9d5c-835e47538321	2025-11-01 03:58:24.754412+00	9dacfb0f-2123-7a94-debc-0f982b90d845
da596ca0-993c-4d74-aafe-9c1288f787f5	c0415f8d-fe2d-b605-adea-e0a62fbb3402	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:24.77463+00	9dacfb0f-2123-7a94-debc-0f982b90d845
9ca1ee15-caab-4eab-97cb-c29c6027c8a4	b498f201-32a4-9587-1f9b-ecc36eff7339	0fcb4eef-adc9-47a6-b005-7492ee16d054	2025-11-01 03:58:24.77463+00	9dacfb0f-2123-7a94-debc-0f982b90d845
a249e057-c4e1-4c73-b306-e012962fd49b	b498f201-32a4-9587-1f9b-ecc36eff7339	ffecdffb-83df-45f6-9d5c-835e47538321	2025-11-01 03:58:24.820017+00	9dacfb0f-2123-7a94-debc-0f982b90d845
08762be2-d2fb-43d0-b1d8-94e6d7104bf4	b498f201-32a4-9587-1f9b-ecc36eff7339	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:24.839389+00	9dacfb0f-2123-7a94-debc-0f982b90d845
19cf20fc-ce83-4852-a73b-71df8a69b964	48c795d9-acf6-470c-4961-cb86f7ccdce0	0fcb4eef-adc9-47a6-b005-7492ee16d054	2025-11-01 03:58:24.839389+00	9dacfb0f-2123-7a94-debc-0f982b90d845
45c9cd76-6bde-45ee-a29e-d008049cf928	48c795d9-acf6-470c-4961-cb86f7ccdce0	ffecdffb-83df-45f6-9d5c-835e47538321	2025-11-01 03:58:24.887958+00	9dacfb0f-2123-7a94-debc-0f982b90d845
75ba04fb-f68d-4460-8c14-1af13d6035c3	48c795d9-acf6-470c-4961-cb86f7ccdce0	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:24.910572+00	9dacfb0f-2123-7a94-debc-0f982b90d845
80eeac11-9948-4d6b-9cfc-15232ca6e883	9fb75e5f-5ca7-ee0d-f895-23aa1b1f110f	0fcb4eef-adc9-47a6-b005-7492ee16d054	2025-11-01 03:58:24.910572+00	9dacfb0f-2123-7a94-debc-0f982b90d845
f92e4d7c-ccfb-4ce9-b06d-938669eab45e	9fb75e5f-5ca7-ee0d-f895-23aa1b1f110f	ffecdffb-83df-45f6-9d5c-835e47538321	2025-11-01 03:58:24.951395+00	9dacfb0f-2123-7a94-debc-0f982b90d845
906e4acc-943b-4a2b-a54c-26899e41b155	9fb75e5f-5ca7-ee0d-f895-23aa1b1f110f	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:24.969109+00	9dacfb0f-2123-7a94-debc-0f982b90d845
1e9a4989-54b3-48ae-a3ad-c871dac2b4d0	d7e0c28e-4d39-05bf-4c35-2eeea852694b	0fcb4eef-adc9-47a6-b005-7492ee16d054	2025-11-01 03:58:24.969109+00	9dacfb0f-2123-7a94-debc-0f982b90d845
ef2aad8c-f32f-49d0-b255-6ce4e8e58071	d7e0c28e-4d39-05bf-4c35-2eeea852694b	ffecdffb-83df-45f6-9d5c-835e47538321	2025-11-01 03:58:25.008846+00	9dacfb0f-2123-7a94-debc-0f982b90d845
089038b3-1156-4d14-951a-b010b3cf0fb1	d7e0c28e-4d39-05bf-4c35-2eeea852694b	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:25.02476+00	9dacfb0f-2123-7a94-debc-0f982b90d845
b7bed3f5-0914-4bae-9e69-d6b420c9c5c4	f15a6f13-5ce6-c94d-a3d2-79c98a7a1e18	0fcb4eef-adc9-47a6-b005-7492ee16d054	2025-11-01 03:58:25.02476+00	9dacfb0f-2123-7a94-debc-0f982b90d845
f8ddc4dd-d95e-4d13-9ebc-9a57e27c950b	f15a6f13-5ce6-c94d-a3d2-79c98a7a1e18	ffecdffb-83df-45f6-9d5c-835e47538321	2025-11-01 03:58:25.061879+00	9dacfb0f-2123-7a94-debc-0f982b90d845
841bc61c-9ed4-4cf3-bb00-b38af807f1f3	f15a6f13-5ce6-c94d-a3d2-79c98a7a1e18	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:25.078581+00	9dacfb0f-2123-7a94-debc-0f982b90d845
be1a419f-b568-4406-89b8-2239bd53cce2	7afe826a-72d8-7dd0-829e-c696e34b57fe	0fcb4eef-adc9-47a6-b005-7492ee16d054	2025-11-01 03:58:25.078581+00	9dacfb0f-2123-7a94-debc-0f982b90d845
693fe5b7-85c9-47a1-aef5-1ed98b2b8ff7	7afe826a-72d8-7dd0-829e-c696e34b57fe	ffecdffb-83df-45f6-9d5c-835e47538321	2025-11-01 03:58:25.117673+00	9dacfb0f-2123-7a94-debc-0f982b90d845
940ba53f-601a-4a8f-bcce-726434fb0dbd	7afe826a-72d8-7dd0-829e-c696e34b57fe	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:25.137144+00	9dacfb0f-2123-7a94-debc-0f982b90d845
6882faa1-c25d-4861-a687-c3a7df20c864	dcfa17de-04c3-a149-1f1c-337fc301baa0	0fcb4eef-adc9-47a6-b005-7492ee16d054	2025-11-01 03:58:25.137144+00	9dacfb0f-2123-7a94-debc-0f982b90d845
b5b15662-3ea4-49af-9644-f32184e56745	dcfa17de-04c3-a149-1f1c-337fc301baa0	ffecdffb-83df-45f6-9d5c-835e47538321	2025-11-01 03:58:25.175847+00	9dacfb0f-2123-7a94-debc-0f982b90d845
ae6a9b6b-be51-4800-a19c-07c5df9bc964	dcfa17de-04c3-a149-1f1c-337fc301baa0	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:25.194218+00	9dacfb0f-2123-7a94-debc-0f982b90d845
6d5ce701-fe0d-4a63-8e36-fd84ea82bf39	1409d784-877d-176a-5126-7830a3d2d256	0fcb4eef-adc9-47a6-b005-7492ee16d054	2025-11-01 03:58:25.194218+00	9dacfb0f-2123-7a94-debc-0f982b90d845
dd86c47c-5ab8-4dfd-87a6-77a09d25d825	1409d784-877d-176a-5126-7830a3d2d256	ffecdffb-83df-45f6-9d5c-835e47538321	2025-11-01 03:58:25.233053+00	9dacfb0f-2123-7a94-debc-0f982b90d845
736eda3a-7426-4f9e-9ca1-0374b905e396	1409d784-877d-176a-5126-7830a3d2d256	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:25.255092+00	9dacfb0f-2123-7a94-debc-0f982b90d845
d04156df-002b-4b4d-93d9-e07d95a8438e	68701396-33d1-79c5-fd76-f3e227d38081	0fcb4eef-adc9-47a6-b005-7492ee16d054	2025-11-01 03:58:25.255092+00	9dacfb0f-2123-7a94-debc-0f982b90d845
e6264cc8-6efa-44c8-be82-e7a195a945a4	68701396-33d1-79c5-fd76-f3e227d38081	ffecdffb-83df-45f6-9d5c-835e47538321	2025-11-01 03:58:25.296459+00	9dacfb0f-2123-7a94-debc-0f982b90d845
9737ba88-9929-449b-994a-df405e86b7e2	68701396-33d1-79c5-fd76-f3e227d38081	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:25.316946+00	9dacfb0f-2123-7a94-debc-0f982b90d845
5bf9a761-06ef-45d3-8d71-0727e9aecb67	ff7dc307-b919-a6a6-2db4-531cbfd5e08b	0fcb4eef-adc9-47a6-b005-7492ee16d054	2025-11-01 03:58:25.316946+00	9dacfb0f-2123-7a94-debc-0f982b90d845
069272b9-9bca-4c92-bcb0-2380cdc66dbf	ff7dc307-b919-a6a6-2db4-531cbfd5e08b	ffecdffb-83df-45f6-9d5c-835e47538321	2025-11-01 03:58:25.35718+00	9dacfb0f-2123-7a94-debc-0f982b90d845
17f50c06-3bce-40f2-a38c-cfece30d1709	ff7dc307-b919-a6a6-2db4-531cbfd5e08b	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:25.376669+00	9dacfb0f-2123-7a94-debc-0f982b90d845
c50f0332-7544-46b2-95b5-b788dd5b247c	70e53e12-b75e-4cff-8bbd-5b572da5a6fc	0fcb4eef-adc9-47a6-b005-7492ee16d054	2025-11-01 03:58:25.376669+00	9dacfb0f-2123-7a94-debc-0f982b90d845
359ca796-28e2-42ae-a83d-c9948bacf7d7	70e53e12-b75e-4cff-8bbd-5b572da5a6fc	ffecdffb-83df-45f6-9d5c-835e47538321	2025-11-01 03:58:25.416643+00	9dacfb0f-2123-7a94-debc-0f982b90d845
6e38c21f-a797-4094-a98d-509d37bd4c83	70e53e12-b75e-4cff-8bbd-5b572da5a6fc	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:25.438478+00	9dacfb0f-2123-7a94-debc-0f982b90d845
7754c198-b182-4882-80e3-21eef0f5a061	aafea4f3-6ae7-8475-2160-39bb316037dc	0fcb4eef-adc9-47a6-b005-7492ee16d054	2025-11-01 03:58:25.438478+00	9dacfb0f-2123-7a94-debc-0f982b90d845
37b7b266-023e-426f-bead-4192d31d42fc	aafea4f3-6ae7-8475-2160-39bb316037dc	ffecdffb-83df-45f6-9d5c-835e47538321	2025-11-01 03:58:25.484069+00	9dacfb0f-2123-7a94-debc-0f982b90d845
c113db3d-900e-4e8c-8549-3f4d7c14931d	aafea4f3-6ae7-8475-2160-39bb316037dc	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:25.50391+00	9dacfb0f-2123-7a94-debc-0f982b90d845
6fadff2d-aaf6-4255-9ac9-f61bb9f2d34f	95a4cde1-4806-4f66-2847-4ec5e9fe804d	a173d206-ccbb-41e1-b19c-f82b6da8a089	2025-11-01 03:58:25.50391+00	9dacfb0f-2123-7a94-debc-0f982b90d845
482104c5-bbd2-4545-9c20-f327bf835ec7	95a4cde1-4806-4f66-2847-4ec5e9fe804d	c3904fc7-86fc-44ca-89fa-b11f0f55c05b	2025-11-01 03:58:25.554337+00	9dacfb0f-2123-7a94-debc-0f982b90d845
bda57ce3-83f0-43b1-98d7-928c1c617e6e	95a4cde1-4806-4f66-2847-4ec5e9fe804d	815a6893-2626-4491-9a3f-d67523fb4f24	2025-11-01 03:58:25.573133+00	9dacfb0f-2123-7a94-debc-0f982b90d845
e86c47eb-5a1f-448b-947e-5e1fd1083538	95a4cde1-4806-4f66-2847-4ec5e9fe804d	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:25.59065+00	9dacfb0f-2123-7a94-debc-0f982b90d845
53be0e16-e885-4955-a3fd-eb2d0fa3bae9	09c4b1c6-7d85-bf1b-c25b-a34843f34c32	a173d206-ccbb-41e1-b19c-f82b6da8a089	2025-11-01 03:58:25.59065+00	9dacfb0f-2123-7a94-debc-0f982b90d845
23c3dd57-d80e-467d-802c-c8596bab1e88	09c4b1c6-7d85-bf1b-c25b-a34843f34c32	c3904fc7-86fc-44ca-89fa-b11f0f55c05b	2025-11-01 03:58:25.634259+00	9dacfb0f-2123-7a94-debc-0f982b90d845
4273101a-a5f8-4d30-9787-efd3582e17d3	09c4b1c6-7d85-bf1b-c25b-a34843f34c32	9193d038-bf06-457a-8c6c-0a6139f52b87	2025-11-01 03:58:25.653446+00	9dacfb0f-2123-7a94-debc-0f982b90d845
a4b1fb22-b45d-414d-a2b3-8e18eb2486bf	09c4b1c6-7d85-bf1b-c25b-a34843f34c32	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:25.672568+00	9dacfb0f-2123-7a94-debc-0f982b90d845
23a9be7b-32cd-4c8f-9402-35285490bc8c	f179e1ff-44c8-bc3f-be8f-739f923abaa0	138e39db-377f-4246-bad6-22c785ac408a	2025-11-01 03:58:25.672568+00	9dacfb0f-2123-7a94-debc-0f982b90d845
cd409c82-21d8-4996-a0c8-40f1ee07a1ee	f179e1ff-44c8-bc3f-be8f-739f923abaa0	3cf23106-c86c-4f38-ab71-4ccd949718f9	2025-11-01 03:58:25.718351+00	9dacfb0f-2123-7a94-debc-0f982b90d845
c1010edc-fc74-415b-b294-d7b7afd07e9d	f179e1ff-44c8-bc3f-be8f-739f923abaa0	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:25.736671+00	9dacfb0f-2123-7a94-debc-0f982b90d845
46b0850e-aeb5-43f3-8969-ce8ed0670f88	2c068dbf-590a-6426-6268-abf3e359df7c	138e39db-377f-4246-bad6-22c785ac408a	2025-11-01 03:58:25.736671+00	9dacfb0f-2123-7a94-debc-0f982b90d845
aa3153aa-28bd-49d7-a665-ba2f78643d9a	2c068dbf-590a-6426-6268-abf3e359df7c	a640f97a-06ef-4abd-ae5a-a19cfb7a8fe4	2025-11-01 03:58:25.778813+00	9dacfb0f-2123-7a94-debc-0f982b90d845
2fbcd5a2-8410-48b7-8f7e-f899d0c1cb56	2c068dbf-590a-6426-6268-abf3e359df7c	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:25.800752+00	9dacfb0f-2123-7a94-debc-0f982b90d845
0259c0a0-d0c5-4825-b37f-76c10786f51e	e186da02-561a-1e30-478a-0a67443ed431	138e39db-377f-4246-bad6-22c785ac408a	2025-11-01 03:58:25.800752+00	9dacfb0f-2123-7a94-debc-0f982b90d845
5cfc6634-34e0-4b45-8653-f2e69ac09439	e186da02-561a-1e30-478a-0a67443ed431	098f581d-9421-4de1-ae12-265fee641f9e	2025-11-01 03:58:25.846564+00	9dacfb0f-2123-7a94-debc-0f982b90d845
9bcb701a-aa76-426b-bd20-7f9a05a37708	e186da02-561a-1e30-478a-0a67443ed431	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:25.866963+00	9dacfb0f-2123-7a94-debc-0f982b90d845
088b2cfa-578d-40c0-8566-21c7e59e74fc	eef9f9ff-bac9-ec5d-102d-330602aa1bda	138e39db-377f-4246-bad6-22c785ac408a	2025-11-01 03:58:25.866963+00	9dacfb0f-2123-7a94-debc-0f982b90d845
abc69ed9-9702-4ecb-bbec-b7842420826e	eef9f9ff-bac9-ec5d-102d-330602aa1bda	3e51af9c-1116-479a-b5fd-41cb42648d01	2025-11-01 03:58:25.906474+00	9dacfb0f-2123-7a94-debc-0f982b90d845
499af08e-5000-49cf-bf26-1be7e6c21eef	eef9f9ff-bac9-ec5d-102d-330602aa1bda	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:25.924676+00	9dacfb0f-2123-7a94-debc-0f982b90d845
8e758695-5d60-4379-9627-867ccd1c8ecb	414e8934-e16e-a43a-7fd2-5144b588ab4b	7ab18b7b-7479-4635-b8a8-d62a0a89851c	2025-11-01 03:58:25.924676+00	9dacfb0f-2123-7a94-debc-0f982b90d845
f4272067-6bea-4467-88d8-6bc59def2dac	414e8934-e16e-a43a-7fd2-5144b588ab4b	fc6c3754-6586-4fe9-a99e-7fa5095a4347	2025-11-01 03:58:25.969355+00	9dacfb0f-2123-7a94-debc-0f982b90d845
8e2cf014-f03a-48c2-b07c-d0a62b332cfd	414e8934-e16e-a43a-7fd2-5144b588ab4b	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:25.989193+00	9dacfb0f-2123-7a94-debc-0f982b90d845
7982dcae-b422-4335-8b98-946c17026e6a	fad18fd5-beda-baa2-2dc7-8ebb9c1db6dd	7ab18b7b-7479-4635-b8a8-d62a0a89851c	2025-11-01 03:58:25.989193+00	9dacfb0f-2123-7a94-debc-0f982b90d845
dd023902-9c5d-41d4-b4c8-350bbbc7099f	fad18fd5-beda-baa2-2dc7-8ebb9c1db6dd	104a8cc5-e59a-49c2-843a-ff8126dfdd55	2025-11-01 03:58:26.031566+00	9dacfb0f-2123-7a94-debc-0f982b90d845
b813305f-b90d-4a8d-9bdc-a7ad1ca42565	fad18fd5-beda-baa2-2dc7-8ebb9c1db6dd	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:26.050706+00	9dacfb0f-2123-7a94-debc-0f982b90d845
30e3d622-f41e-46c4-9d1d-ed385387de6b	c9e3e36b-1080-aecd-1201-840f82ed3243	7ab18b7b-7479-4635-b8a8-d62a0a89851c	2025-11-01 03:58:26.050706+00	9dacfb0f-2123-7a94-debc-0f982b90d845
e28c9e09-3e13-4cfd-ac3b-ac349057110b	c9e3e36b-1080-aecd-1201-840f82ed3243	104a8cc5-e59a-49c2-843a-ff8126dfdd55	2025-11-01 03:58:26.094551+00	9dacfb0f-2123-7a94-debc-0f982b90d845
6e7ed47f-e8e5-4afb-8b79-8d1f300fed5f	c9e3e36b-1080-aecd-1201-840f82ed3243	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:26.129768+00	9dacfb0f-2123-7a94-debc-0f982b90d845
dfec0a61-3c78-447e-821c-676e84fd0d3e	1901e980-86bd-4a07-4b15-2665f320affa	a173d206-ccbb-41e1-b19c-f82b6da8a089	2025-11-01 03:58:26.129768+00	9dacfb0f-2123-7a94-debc-0f982b90d845
51ad91fe-31c2-405b-803a-e7cb9f77858b	1901e980-86bd-4a07-4b15-2665f320affa	32715e38-dd50-4dd3-8566-9fbba018c229	2025-11-01 03:58:26.171802+00	9dacfb0f-2123-7a94-debc-0f982b90d845
2de514df-a9d9-400b-bc4f-794b3351cc48	1901e980-86bd-4a07-4b15-2665f320affa	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:26.190215+00	9dacfb0f-2123-7a94-debc-0f982b90d845
81f5f186-429f-4d45-9d64-0bf92cc25c18	3b6d1fa7-1f9e-4173-6f6d-054cf222b60a	a173d206-ccbb-41e1-b19c-f82b6da8a089	2025-11-01 03:58:26.190215+00	9dacfb0f-2123-7a94-debc-0f982b90d845
90c88a9d-9db2-4ede-9fd8-39a533cafdf1	3b6d1fa7-1f9e-4173-6f6d-054cf222b60a	559a530f-1ad0-4aac-8fb0-741319573365	2025-11-01 03:58:26.23595+00	9dacfb0f-2123-7a94-debc-0f982b90d845
b0939cc7-338d-4277-82d0-42fca86048d1	3b6d1fa7-1f9e-4173-6f6d-054cf222b60a	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:26.255979+00	9dacfb0f-2123-7a94-debc-0f982b90d845
b80ac5fd-aac7-44c7-95dc-5476b2347b81	177e21f7-34ad-22b9-3036-3194f1d40f8c	af9059a6-c71b-49a9-bef2-1623ddce4ec4	2025-11-01 03:58:26.255979+00	9dacfb0f-2123-7a94-debc-0f982b90d845
a7934b20-5afe-472a-9486-10b9adfeb1ff	177e21f7-34ad-22b9-3036-3194f1d40f8c	78bde295-e1a7-4a74-ba21-c380b76cb633	2025-11-01 03:58:26.301494+00	9dacfb0f-2123-7a94-debc-0f982b90d845
a2172406-b856-431c-8583-88108ae62151	177e21f7-34ad-22b9-3036-3194f1d40f8c	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:26.360474+00	9dacfb0f-2123-7a94-debc-0f982b90d845
c2fe453a-8dec-4b9b-b36c-3ff9ed6853c2	ed1cb925-fab2-1a0f-4f5f-ff1b97d19c8d	af9059a6-c71b-49a9-bef2-1623ddce4ec4	2025-11-01 03:58:26.360474+00	9dacfb0f-2123-7a94-debc-0f982b90d845
e63a1185-eef2-4fb0-a93d-3ed0521bad9e	ed1cb925-fab2-1a0f-4f5f-ff1b97d19c8d	2502186e-5c10-45b9-87c1-1401f71ff2e0	2025-11-01 03:58:26.402962+00	9dacfb0f-2123-7a94-debc-0f982b90d845
ee9e6e5c-26e7-4d14-a801-4ac1734d2523	ed1cb925-fab2-1a0f-4f5f-ff1b97d19c8d	e66adeb0-6645-4821-b312-35e3ff9a73d5	2025-11-01 03:58:26.42244+00	9dacfb0f-2123-7a94-debc-0f982b90d845
88cf3dbb-5ff1-4dc6-b0b3-f78bd7b7ec24	cb498eb4-a045-7409-7b78-ab3c2b1dfb57	397dc979-36a1-4199-984c-0b8909f11151	2025-11-01 03:58:26.42244+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
a92a743e-1faf-4f54-9db9-f6b5c95a2a4e	cb498eb4-a045-7409-7b78-ab3c2b1dfb57	0467dac0-a67e-414a-a124-e65d13598dbd	2025-11-01 03:58:26.474264+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
75ed452f-6754-4330-9b3d-5b67582dd5b1	cb498eb4-a045-7409-7b78-ab3c2b1dfb57	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:26.494345+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
70ff4e74-4bae-481c-8157-e1224c2d420b	b9f0b21b-8562-c86a-dfd8-a4d3bf861d07	397dc979-36a1-4199-984c-0b8909f11151	2025-11-01 03:58:26.494345+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
adeff836-2c35-4064-971b-a9accda7444d	b9f0b21b-8562-c86a-dfd8-a4d3bf861d07	2230327e-376a-4345-816b-4de3f60e1bb1	2025-11-01 03:58:26.53898+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
86dff5f0-aecf-4687-96e3-f80e8907c86a	b9f0b21b-8562-c86a-dfd8-a4d3bf861d07	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:26.557039+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
db6d77a9-5b90-494d-9199-ebbb00fd650c	a7166705-45ab-1527-c779-2e50f105eb5e	397dc979-36a1-4199-984c-0b8909f11151	2025-11-01 03:58:26.557039+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
a138d2ec-aee1-4d72-881a-ca47babd4b5b	a7166705-45ab-1527-c779-2e50f105eb5e	3643615f-e7de-4c2b-9f55-46aa40d88864	2025-11-01 03:58:26.597603+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
97eaf3d7-b4d5-4211-bc92-f386a9e16c59	a7166705-45ab-1527-c779-2e50f105eb5e	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:26.617073+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
1b5d4ba7-79cc-4e82-969a-549074489ea0	ff6b27d6-2003-fd8a-cd60-e39baa9a5f25	397dc979-36a1-4199-984c-0b8909f11151	2025-11-01 03:58:26.617073+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
55ef7da8-c655-4f1f-9b2c-cd5ef9e764aa	ff6b27d6-2003-fd8a-cd60-e39baa9a5f25	d82d4ea7-b096-4664-9745-8b09cdfb8bb0	2025-11-01 03:58:26.657218+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
c790bebd-12f3-4813-bdb7-a8fcf6e2b476	ff6b27d6-2003-fd8a-cd60-e39baa9a5f25	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:26.674451+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
f1d5521d-c9cb-468d-910f-b5e53f4d0145	794655e0-ac5a-65c9-c17b-2c082e42c24e	397dc979-36a1-4199-984c-0b8909f11151	2025-11-01 03:58:26.674451+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
0dd070a3-e060-4974-b2ba-e6b39c00447c	794655e0-ac5a-65c9-c17b-2c082e42c24e	84d10043-4721-4c54-9f8f-aaf27b725e48	2025-11-01 03:58:26.71705+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
b3a201fb-e166-4999-aa1c-9886a3265121	794655e0-ac5a-65c9-c17b-2c082e42c24e	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:26.736358+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
495b3b21-d623-43f6-8eb2-4ecc44560ea2	8182dbbe-16bb-f4b6-d64a-c47be61f269d	397dc979-36a1-4199-984c-0b8909f11151	2025-11-01 03:58:26.736358+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
f093e528-793a-45a1-bae7-2f1582e0d5eb	8182dbbe-16bb-f4b6-d64a-c47be61f269d	d9e9d88b-8155-4d10-b962-a8bbd40b7fc0	2025-11-01 03:58:26.778213+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
ca6bb7b0-fe7a-4abf-a3e5-42f697d0f7ec	8182dbbe-16bb-f4b6-d64a-c47be61f269d	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:26.79739+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
2c0d6d9c-5ae5-495d-9035-ffa584df4a94	36addc8c-76ac-e981-b0b5-2a7fe95ad565	397dc979-36a1-4199-984c-0b8909f11151	2025-11-01 03:58:26.79739+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
5dea8e06-f02f-4162-8b8b-038a185c3ffd	36addc8c-76ac-e981-b0b5-2a7fe95ad565	0f7a1767-be76-4ce2-9afb-9ffb931fe50e	2025-11-01 03:58:26.839755+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
adefed43-b8e4-4fe4-b481-4da322171eb2	36addc8c-76ac-e981-b0b5-2a7fe95ad565	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:26.858507+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
1169894d-d433-42db-9611-74ada24285a1	fa6ffacf-8717-af52-934e-4d2d915a9df8	397dc979-36a1-4199-984c-0b8909f11151	2025-11-01 03:58:26.858507+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
ef360c2a-ec1b-4379-b0ea-a4e1b454dc8a	fa6ffacf-8717-af52-934e-4d2d915a9df8	32449c38-a426-43fb-88ff-d8a9c55af872	2025-11-01 03:58:26.898187+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
efbdc4aa-5757-4821-9151-8fc395e61a6c	fa6ffacf-8717-af52-934e-4d2d915a9df8	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:26.917678+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
8b003f8f-94e6-4ebd-8002-a554be54c837	7b742620-07dd-e3c4-3711-d217a078b6d8	3045ee77-b50d-460c-be14-7af7bb09e26f	2025-11-01 03:58:26.917678+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
e45edebe-45a5-492e-a384-1362c38d52c9	7b742620-07dd-e3c4-3711-d217a078b6d8	afe5a6e7-ecd2-4b2c-88f4-373161847687	2025-11-01 03:58:26.96116+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
9cba94ed-05d9-4af3-ad28-9cceea8cca91	7b742620-07dd-e3c4-3711-d217a078b6d8	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:26.978823+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
86c72e58-436a-46da-b190-97bea3abb048	8fc46cbb-a19d-4e04-d305-6c7c8fbd5450	3045ee77-b50d-460c-be14-7af7bb09e26f	2025-11-01 03:58:26.978823+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
5e3dbe21-a57b-4ff5-aaa8-053006a288f2	8fc46cbb-a19d-4e04-d305-6c7c8fbd5450	a4940399-0cee-4962-ab76-62bea51cadd1	2025-11-01 03:58:27.02104+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
4f8182e1-bb0e-415d-b408-4954ac9bd5b9	8fc46cbb-a19d-4e04-d305-6c7c8fbd5450	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.039366+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
aea553ab-0960-4979-b92d-33055335227f	6a760c61-dd99-7cd5-6d92-f017e3951df2	3045ee77-b50d-460c-be14-7af7bb09e26f	2025-11-01 03:58:27.039366+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
4e5ade7b-ce03-4f8a-be03-48fb65b8c895	6a760c61-dd99-7cd5-6d92-f017e3951df2	97e2cf05-57e0-4434-b312-ba43fb3c02b2	2025-11-01 03:58:27.076234+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
711c89a2-bef6-4830-a6fe-d1ff1d12fc6f	6a760c61-dd99-7cd5-6d92-f017e3951df2	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.092507+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
9a208f78-999b-4de1-ae36-4c55ee37331d	e32cf196-33d7-106a-bf8d-2eff19f16108	3045ee77-b50d-460c-be14-7af7bb09e26f	2025-11-01 03:58:27.092507+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
75fc2426-c32c-40eb-af4f-95ec0fae14f1	e32cf196-33d7-106a-bf8d-2eff19f16108	a2b53588-f92f-4e0b-a896-791d8b4b2bb8	2025-11-01 03:58:27.128556+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
90bf8107-234e-4149-b1fa-3a22d3bd52e7	e32cf196-33d7-106a-bf8d-2eff19f16108	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.145552+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
25a8a3df-19bc-4b86-b88d-26104a1711f8	02b7f65d-8ace-71fc-17f3-1279376247e4	3045ee77-b50d-460c-be14-7af7bb09e26f	2025-11-01 03:58:27.145552+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
f6e7f3c9-476f-4018-b3ac-12fd30341efb	02b7f65d-8ace-71fc-17f3-1279376247e4	0851d4fd-fec5-4d55-85b5-afea80c3b210	2025-11-01 03:58:27.181039+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
60a4c276-fec2-40f6-8497-4d6b22a29784	02b7f65d-8ace-71fc-17f3-1279376247e4	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.197931+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
3f190f34-e565-4a45-827e-3dec41e81297	1e88b0bb-1da5-2f38-f6d1-6594cb3462c4	d392b948-bf82-4b70-acab-764486d98735	2025-11-01 03:58:27.197931+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
c319cf34-6416-49af-99f9-f1140003eba9	1e88b0bb-1da5-2f38-f6d1-6594cb3462c4	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.232632+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
84549a92-b812-4471-8ec7-44ef3604abf4	99b03662-0fcb-b2a0-96a9-d0d23d8c0b1d	d392b948-bf82-4b70-acab-764486d98735	2025-11-01 03:58:27.232632+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
5ee0436c-5491-492f-9018-ad6d090372d5	99b03662-0fcb-b2a0-96a9-d0d23d8c0b1d	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.274256+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
f8e71e18-b5bb-4528-b6b8-27c582d11ba3	6648b795-c9ee-7cc4-7b5b-e2f740dcfc82	d392b948-bf82-4b70-acab-764486d98735	2025-11-01 03:58:27.274256+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
522e22c5-402c-4170-afbf-221970532b46	6648b795-c9ee-7cc4-7b5b-e2f740dcfc82	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.314663+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
b549f7ff-143f-4376-839c-3601966a7272	0bb50439-7d17-1a5e-ea31-4e026faa7fb0	d392b948-bf82-4b70-acab-764486d98735	2025-11-01 03:58:27.314663+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
1c525af7-ea91-4f60-b823-1b15f7d24b3d	0bb50439-7d17-1a5e-ea31-4e026faa7fb0	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.349748+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
3dfdfbad-a4de-4e0b-9aa4-73f7fe3af0c0	9e385327-160a-098e-4dd8-2d0244ebbdcb	d392b948-bf82-4b70-acab-764486d98735	2025-11-01 03:58:27.349748+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
f7bb8561-7c4b-42de-a0f8-5fa7aba865d0	9e385327-160a-098e-4dd8-2d0244ebbdcb	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.385736+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
21840503-09a2-4cb2-992c-30bae7fb14b0	721561b3-4b12-7f59-0f40-820515457c1e	d392b948-bf82-4b70-acab-764486d98735	2025-11-01 03:58:27.385736+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
d20fca57-7d8b-4319-9455-d1bc90a08f38	721561b3-4b12-7f59-0f40-820515457c1e	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.426401+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
7d876bfb-f40f-4195-a182-ca3c926a0add	d95b392f-38c7-e4a4-93eb-7e8d5a3bce35	d392b948-bf82-4b70-acab-764486d98735	2025-11-01 03:58:27.426401+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
2b7ace30-5552-493e-9a02-7a06c6851a3f	d95b392f-38c7-e4a4-93eb-7e8d5a3bce35	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.465139+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
d99bd318-987c-4fac-9fac-4e0afde6edef	412b2a7f-b3ff-6503-efce-65b1982cb9b6	d392b948-bf82-4b70-acab-764486d98735	2025-11-01 03:58:27.465139+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
df88deca-f306-4648-b632-b495266d8177	412b2a7f-b3ff-6503-efce-65b1982cb9b6	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.512378+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
6e50608a-3ac4-4667-aa2e-729765e8275d	098de461-2c8a-ff40-83c1-aeb5a0b0f26a	d392b948-bf82-4b70-acab-764486d98735	2025-11-01 03:58:27.512378+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
8b02bb8e-d43f-49de-8916-58656b939323	098de461-2c8a-ff40-83c1-aeb5a0b0f26a	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.55843+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
d1593dfc-31d9-487a-8ff3-4c4214441948	dbacb2bf-e360-43ec-bd34-3ba959e9958e	a53083e1-1658-48ea-aad6-de94f26001f6	2025-11-01 03:58:27.55843+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
51f5f53e-a0b3-4b33-82c2-5456a0840be1	dbacb2bf-e360-43ec-bd34-3ba959e9958e	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.60449+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
3e20e786-ebb8-49f9-b6de-46515bd3f060	7bb2f870-6c7c-d07f-0b24-9980b942798d	a53083e1-1658-48ea-aad6-de94f26001f6	2025-11-01 03:58:27.60449+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
fda349e3-afb4-442c-a757-50e33faf37a8	7bb2f870-6c7c-d07f-0b24-9980b942798d	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.649627+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
24c03e1e-52ed-40c6-8a7c-23a8b8ff6824	d2af8406-8a9f-81bc-3b0b-a81375f3c747	a53083e1-1658-48ea-aad6-de94f26001f6	2025-11-01 03:58:27.649627+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
ceee5f4c-68a7-4984-b190-ea6ad2e16a13	d2af8406-8a9f-81bc-3b0b-a81375f3c747	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.686802+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
ba1c2e51-1f9c-4b64-9ad6-b649e837d979	1b820294-9860-9dda-1596-587211100df5	a53083e1-1658-48ea-aad6-de94f26001f6	2025-11-01 03:58:27.686802+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
69d79199-ac2e-4083-bf8a-bcbb521bafc7	1b820294-9860-9dda-1596-587211100df5	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.728795+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
f04199b0-5a5a-4414-85dc-488d98b96fe6	c1a374d6-2d41-776f-9b25-26e9996ee9ac	a53083e1-1658-48ea-aad6-de94f26001f6	2025-11-01 03:58:27.728795+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
7221c15f-2603-4baa-8338-2f2445b16755	c1a374d6-2d41-776f-9b25-26e9996ee9ac	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.7706+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
ec20899f-f8f9-40ae-bfb3-713415ff5cbb	f001677f-f77b-39ba-df96-b1917a0c62ef	a53083e1-1658-48ea-aad6-de94f26001f6	2025-11-01 03:58:27.7706+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
34a97b78-4fe7-47d3-88e5-e5636a0ce7ec	f001677f-f77b-39ba-df96-b1917a0c62ef	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.815274+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
f4e44c09-f7f5-4417-a792-32c6d33c5ee1	d5957bbc-8bc3-a848-990f-fbd552cc54e9	a53083e1-1658-48ea-aad6-de94f26001f6	2025-11-01 03:58:27.815274+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
565d41f1-44c3-4171-b584-f94e4bea5413	d5957bbc-8bc3-a848-990f-fbd552cc54e9	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 03:58:27.862361+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
a553a1e1-fe21-4c27-9b0f-85646c78e6ef	bd1cf22d-c93a-fa22-a107-882e4473f177	a53083e1-1658-48ea-aad6-de94f26001f6	2025-11-01 03:58:27.862361+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
4b578d94-3f0d-47af-b6c3-fc4514e01ea0	ddd4b332-4b4b-ca49-17bb-e998404ed581	3f6e937c-acab-4531-9583-c70bdbb66796	2025-11-01 04:23:14.303358+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
bbaed321-29a6-47a6-9b1d-f7033e833590	ad93ac42-91f2-bd2c-b835-5da6b6bc44bb	3f6e937c-acab-4531-9583-c70bdbb66796	2025-11-01 04:23:14.303358+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
6a25f931-7e7a-4c8a-87dc-f21a955bec4b	2c8449ca-b800-c153-9f4b-0b8ea7c2fc08	2e104f4e-c2fa-4aa5-8d69-5eeeba7216b8	2025-11-01 04:23:14.303358+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
5c30cfbc-5548-4140-8caa-83fdde4043d9	16875284-3b5b-d473-1c36-eb549851db22	4b8bcfa9-da85-4655-8c77-bcfe6b8e0553	2025-11-01 04:23:14.303358+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
219446a3-d67a-4124-944e-0039baee3844	43d5f997-48d7-5e4b-aa64-07f58ff66c32	2e104f4e-c2fa-4aa5-8d69-5eeeba7216b8	2025-11-01 04:23:14.303358+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
e701968c-a265-4cfb-ae45-2f752e88342e	b9d5970d-6ec4-b3b1-9044-2e5f8c37376f	3f6e937c-acab-4531-9583-c70bdbb66796	2025-11-01 04:23:14.303358+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
e03e1490-c587-4767-955c-ff5f9608c45c	582275ae-3305-5097-5452-da918bc51cb2	a6d17fc7-c622-47d0-85b6-b918fd83ccb9	2025-11-01 04:23:14.303358+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
fa38b22f-00db-412f-835c-07dedd6eb3a6	17c52141-8347-ccac-0e79-93b0b182c48f	398a8280-2e94-4120-a5d7-f5a705c17f78	2025-11-01 04:23:14.303358+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
44788af8-ac81-4767-bc01-0c7a7f46c15e	b53331c7-7399-52ca-d2c6-0a2f1ec847e2	398a8280-2e94-4120-a5d7-f5a705c17f78	2025-11-01 04:23:14.303358+00	fd5f083c-6ffc-df32-89ca-a4044b5723f5
84639aa7-2c92-400d-8e02-267b2b2d6b5a	c0415f8d-fe2d-b605-adea-e0a62fbb3402	58c827d0-4bc7-445d-8c83-d5c5c2c92832	2025-11-01 04:23:14.454568+00	9dacfb0f-2123-7a94-debc-0f982b90d845
440dafff-4d65-49d0-81f9-887d4902653a	b498f201-32a4-9587-1f9b-ecc36eff7339	58c827d0-4bc7-445d-8c83-d5c5c2c92832	2025-11-01 04:23:14.454568+00	9dacfb0f-2123-7a94-debc-0f982b90d845
5f344cf4-2496-4ea9-b234-af656145a5f9	48c795d9-acf6-470c-4961-cb86f7ccdce0	e1875673-5025-4917-8350-8e3c1be86b4a	2025-11-01 04:23:14.454568+00	9dacfb0f-2123-7a94-debc-0f982b90d845
7957ef93-acf2-492b-9df5-546ab68ee920	9fb75e5f-5ca7-ee0d-f895-23aa1b1f110f	4b1def4d-871c-4e26-9800-4b7526c2baae	2025-11-01 04:23:14.454568+00	9dacfb0f-2123-7a94-debc-0f982b90d845
ea30c607-e591-4ea1-ad16-05d206df1bf1	d7e0c28e-4d39-05bf-4c35-2eeea852694b	639f38b4-71b0-43ee-a71a-5c25741314fd	2025-11-01 04:23:14.454568+00	9dacfb0f-2123-7a94-debc-0f982b90d845
fdd2027e-33cf-47e2-b399-4eff9994a567	f15a6f13-5ce6-c94d-a3d2-79c98a7a1e18	639f38b4-71b0-43ee-a71a-5c25741314fd	2025-11-01 04:23:14.454568+00	9dacfb0f-2123-7a94-debc-0f982b90d845
14eebf31-f5c4-4fea-b0a0-620bb4e1132e	7afe826a-72d8-7dd0-829e-c696e34b57fe	87d9c81f-540f-47d4-ab1f-06ea9ae7072c	2025-11-01 04:23:14.454568+00	9dacfb0f-2123-7a94-debc-0f982b90d845
5262e37d-7127-4410-8fbb-77bfb12ab54d	dcfa17de-04c3-a149-1f1c-337fc301baa0	58c827d0-4bc7-445d-8c83-d5c5c2c92832	2025-11-01 04:23:14.454568+00	9dacfb0f-2123-7a94-debc-0f982b90d845
d3d076b6-8d3d-4450-8131-a572fb0a9570	1409d784-877d-176a-5126-7830a3d2d256	4b1def4d-871c-4e26-9800-4b7526c2baae	2025-11-01 04:23:14.454568+00	9dacfb0f-2123-7a94-debc-0f982b90d845
8100151d-253e-444e-ab17-caf2d5221a1f	68701396-33d1-79c5-fd76-f3e227d38081	87d9c81f-540f-47d4-ab1f-06ea9ae7072c	2025-11-01 04:23:14.454568+00	9dacfb0f-2123-7a94-debc-0f982b90d845
1a280419-8a0c-40e3-a664-e05ad06e3b0b	ff7dc307-b919-a6a6-2db4-531cbfd5e08b	639f38b4-71b0-43ee-a71a-5c25741314fd	2025-11-01 04:23:14.454568+00	9dacfb0f-2123-7a94-debc-0f982b90d845
83a8986e-f28d-4866-8b74-6aad4a221597	70e53e12-b75e-4cff-8bbd-5b572da5a6fc	e1875673-5025-4917-8350-8e3c1be86b4a	2025-11-01 04:23:14.454568+00	9dacfb0f-2123-7a94-debc-0f982b90d845
2909b95a-5a0d-4f49-ac15-33600f0e842a	aafea4f3-6ae7-8475-2160-39bb316037dc	429df1ab-dcc6-4b60-8543-5c060e6befce	2025-11-01 04:23:14.454568+00	9dacfb0f-2123-7a94-debc-0f982b90d845
5b4df7cf-9114-487f-9b78-3b4be0a66062	cb498eb4-a045-7409-7b78-ab3c2b1dfb57	755149b8-0d5e-486d-9c52-8233496fe41a	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
0856ae83-aa05-483d-ba30-412944ab8940	b9f0b21b-8562-c86a-dfd8-a4d3bf861d07	755149b8-0d5e-486d-9c52-8233496fe41a	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
2f671d59-b552-436b-a71c-8e957c8370eb	a7166705-45ab-1527-c779-2e50f105eb5e	755149b8-0d5e-486d-9c52-8233496fe41a	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
64e5341c-f139-4d47-b603-4b3da792e016	ff6b27d6-2003-fd8a-cd60-e39baa9a5f25	620953a7-cf1a-4a1a-b010-991699a2576a	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
27799c14-c951-48a3-8fcf-94e78119ce8e	794655e0-ac5a-65c9-c17b-2c082e42c24e	620953a7-cf1a-4a1a-b010-991699a2576a	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
8d1cd63e-cc04-443b-afbe-ab2996da556b	8182dbbe-16bb-f4b6-d64a-c47be61f269d	22691010-2cf8-464c-8498-64fbacb80834	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
e4dd9386-7019-4500-89d5-6610cc97066b	36addc8c-76ac-e981-b0b5-2a7fe95ad565	22691010-2cf8-464c-8498-64fbacb80834	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
7f9ae0be-1ab6-44ce-ac62-47cef2934bf9	fa6ffacf-8717-af52-934e-4d2d915a9df8	755149b8-0d5e-486d-9c52-8233496fe41a	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
5ceb3109-5fd6-47b2-822b-592f10e4359c	7b742620-07dd-e3c4-3711-d217a078b6d8	a0c692e8-9526-4ec6-aa36-f2e6c0e00154	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
40e5c8c4-5402-423c-ac2f-d5de178526c8	8fc46cbb-a19d-4e04-d305-6c7c8fbd5450	a0c692e8-9526-4ec6-aa36-f2e6c0e00154	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
de74a3d7-b05a-4f95-996e-02b3656dd26f	6a760c61-dd99-7cd5-6d92-f017e3951df2	a4221c36-b722-4b05-929b-ec9e76e256ef	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
3861b05c-a90b-461f-9e63-6fa73a12007a	e32cf196-33d7-106a-bf8d-2eff19f16108	a4221c36-b722-4b05-929b-ec9e76e256ef	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
d0ffd06e-63b8-4186-b6f8-09a117b84570	02b7f65d-8ace-71fc-17f3-1279376247e4	a0c692e8-9526-4ec6-aa36-f2e6c0e00154	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
27e52fcc-098d-4d9e-9117-c45f7f2593b3	1e88b0bb-1da5-2f38-f6d1-6594cb3462c4	620953a7-cf1a-4a1a-b010-991699a2576a	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
b0992335-d7ba-456d-a975-0111ddcac7ea	99b03662-0fcb-b2a0-96a9-d0d23d8c0b1d	755149b8-0d5e-486d-9c52-8233496fe41a	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
00b93413-a5d0-4f8a-ab07-177ee8bd7e65	6648b795-c9ee-7cc4-7b5b-e2f740dcfc82	755149b8-0d5e-486d-9c52-8233496fe41a	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
bc58a921-7410-4f81-9d9c-e02f97036602	0bb50439-7d17-1a5e-ea31-4e026faa7fb0	22691010-2cf8-464c-8498-64fbacb80834	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
712ecaac-3a49-4ed7-9cd9-09334ae8dc57	9e385327-160a-098e-4dd8-2d0244ebbdcb	620953a7-cf1a-4a1a-b010-991699a2576a	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
b6fb2c31-841c-4be7-a66b-4bd92ab0f10f	721561b3-4b12-7f59-0f40-820515457c1e	000484c8-91dc-4b97-b984-e3d49af559d2	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
bf06b0da-8164-45ee-a091-4666ba58a82f	d95b392f-38c7-e4a4-93eb-7e8d5a3bce35	22691010-2cf8-464c-8498-64fbacb80834	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
138d6014-ef47-4b0c-bec9-d63518838a5e	412b2a7f-b3ff-6503-efce-65b1982cb9b6	bbe91ac9-bfcf-425f-83f6-3ad79a23a4de	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
057961e5-4c52-4925-a174-75f0d117e05b	098de461-2c8a-ff40-83c1-aeb5a0b0f26a	a0c692e8-9526-4ec6-aa36-f2e6c0e00154	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
90a8691f-6bc8-423e-a266-08e33819396c	bd1cf22d-c93a-fa22-a107-882e4473f177	e813c891-0212-40bf-b668-1075ed904a64	2025-11-01 04:23:14.63648+00	b13cd6e9-6a6e-c644-8a44-e710b2868e54
\.


--
-- Data for Name: position_volatility; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.position_volatility (id, position_id, calculation_date, realized_vol_21d, realized_vol_63d, vol_daily, vol_weekly, vol_monthly, expected_vol_21d, vol_trend, vol_trend_strength, vol_percentile, observations, model_r_squared, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: positions; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.positions (id, portfolio_id, symbol, position_type, quantity, entry_price, entry_date, exit_price, exit_date, underlying_symbol, strike_price, expiration_date, investment_class, investment_subtype, last_price, market_value, unrealized_pnl, realized_pnl, created_at, updated_at, deleted_at) FROM stdin;
ddd4b332-4b4b-ca49-17bb-e998404ed581	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	AAPL	LONG	85.0000	225.0000	2024-01-15	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:23.608859+00	2025-11-01 07:58:23.608859+00	\N
ad93ac42-91f2-bd2c-b835-5da6b6bc44bb	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	MSFT	LONG	45.0000	420.0000	2024-01-16	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:23.717915+00	2025-11-01 07:58:23.717915+00	\N
2c8449ca-b800-c153-9f4b-0b8ea7c2fc08	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	AMZN	LONG	110.0000	170.0000	2024-01-18	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:23.780598+00	2025-11-01 07:58:23.780598+00	\N
16875284-3b5b-d473-1c36-eb549851db22	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	GOOGL	LONG	115.0000	160.0000	2024-01-20	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:23.838577+00	2025-11-01 07:58:23.838577+00	\N
43d5f997-48d7-5e4b-aa64-07f58ff66c32	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	TSLA	LONG	70.0000	255.0000	2024-01-22	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:23.895691+00	2025-11-01 07:58:23.895691+00	\N
b9d5970d-6ec4-b3b1-9044-2e5f8c37376f	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	NVDA	LONG	25.0000	700.0000	2024-01-25	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:23.932977+00	2025-11-01 07:58:23.932977+00	\N
582275ae-3305-5097-5452-da918bc51cb2	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	JNJ	LONG	105.0000	160.0000	2024-02-01	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:23.97145+00	2025-11-01 07:58:23.97145+00	\N
17c52141-8347-ccac-0e79-93b0b182c48f	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	JPM	LONG	85.0000	170.0000	2024-02-05	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:24.0083+00	2025-11-01 07:58:24.0083+00	\N
b53331c7-7399-52ca-d2c6-0a2f1ec847e2	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	V	LONG	50.0000	268.0000	2024-02-08	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:24.044249+00	2025-11-01 07:58:24.044249+00	\N
9a1ef980-a831-f29f-9cb5-03e978510bcd	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	FXNAX	LONG	4365.0000	20.0000	2023-12-15	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:24.078324+00	2025-11-01 07:58:24.078324+00	\N
408b33a1-2a41-c8f6-1bc1-486f7cd239b8	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	FCNTX	LONG	4850.0000	15.0000	2023-12-15	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:24.136191+00	2025-11-01 07:58:24.136191+00	\N
d29ebb59-d2b1-b17a-f512-cbca791646da	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	FMAGX	LONG	3880.0000	15.0000	2023-12-15	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:24.195905+00	2025-11-01 07:58:24.195905+00	\N
531d2a35-0ddc-65b7-9444-2ff23d40f846	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	VTIAX	LONG	970.0000	30.0000	2023-12-15	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:24.255048+00	2025-11-01 07:58:24.255048+00	\N
6fb17e84-682f-893a-a73d-1eaee18a072b	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	VTI	LONG	155.0000	250.0000	2023-11-20	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:24.318863+00	2025-11-01 07:58:24.318863+00	\N
9c7e4ad8-dd19-af4c-5495-1cf816079596	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	BND	LONG	315.0000	77.0000	2023-11-20	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:24.386384+00	2025-11-01 07:58:24.386384+00	\N
82e18b81-5e1f-8dc6-d115-6a4acaa78a0a	1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe	VNQ	LONG	204.0000	95.0000	2023-11-20	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:24.450643+00	2025-11-01 07:58:24.450643+00	\N
b036d715-1392-2cb1-7018-d8f296ef35c3	e23ab931-a033-edfe-ed4f-9d02474780b4	SPY	LONG	400.0000	530.0000	2024-01-05	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:24.519161+00	2025-11-01 07:58:24.519161+00	\N
7f3f9dda-d295-edd9-48a3-61532b4ad804	e23ab931-a033-edfe-ed4f-9d02474780b4	QQQ	LONG	450.0000	420.0000	2024-01-05	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:24.585446+00	2025-11-01 07:58:24.585446+00	\N
cbdba890-4eb2-19ad-eff6-a82281c27067	e23ab931-a033-edfe-ed4f-9d02474780b4	VTI	LONG	800.0000	230.0000	2024-01-05	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:24.658397+00	2025-11-01 07:58:24.658397+00	\N
c0415f8d-fe2d-b605-adea-e0a62fbb3402	e23ab931-a033-edfe-ed4f-9d02474780b4	AAPL	LONG	400.0000	225.0000	2024-01-10	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:24.723074+00	2025-11-01 07:58:24.723074+00	\N
b498f201-32a4-9587-1f9b-ecc36eff7339	e23ab931-a033-edfe-ed4f-9d02474780b4	MSFT	LONG	200.0000	420.0000	2024-01-10	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:24.789167+00	2025-11-01 07:58:24.789167+00	\N
48c795d9-acf6-470c-4961-cb86f7ccdce0	e23ab931-a033-edfe-ed4f-9d02474780b4	AMZN	LONG	480.0000	170.0000	2024-01-12	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:24.853296+00	2025-11-01 07:58:24.853296+00	\N
9fb75e5f-5ca7-ee0d-f895-23aa1b1f110f	e23ab931-a033-edfe-ed4f-9d02474780b4	GOOGL	LONG	500.0000	160.0000	2024-01-12	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:24.923792+00	2025-11-01 07:58:24.923792+00	\N
d7e0c28e-4d39-05bf-4c35-2eeea852694b	e23ab931-a033-edfe-ed4f-9d02474780b4	BRK-B	LONG	180.0000	440.0000	2024-01-15	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:24.982965+00	2025-11-01 07:58:24.982965+00	\N
f15a6f13-5ce6-c94d-a3d2-79c98a7a1e18	e23ab931-a033-edfe-ed4f-9d02474780b4	JPM	LONG	350.0000	170.0000	2024-01-15	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:25.036826+00	2025-11-01 07:58:25.036826+00	\N
7afe826a-72d8-7dd0-829e-c696e34b57fe	e23ab931-a033-edfe-ed4f-9d02474780b4	JNJ	LONG	310.0000	160.0000	2024-01-18	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:25.091135+00	2025-11-01 07:58:25.091135+00	\N
dcfa17de-04c3-a149-1f1c-337fc301baa0	e23ab931-a033-edfe-ed4f-9d02474780b4	NVDA	LONG	70.0000	700.0000	2024-01-20	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:25.151759+00	2025-11-01 07:58:25.151759+00	\N
1409d784-877d-176a-5126-7830a3d2d256	e23ab931-a033-edfe-ed4f-9d02474780b4	META	LONG	90.0000	530.0000	2024-01-20	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:25.206755+00	2025-11-01 07:58:25.206755+00	\N
68701396-33d1-79c5-fd76-f3e227d38081	e23ab931-a033-edfe-ed4f-9d02474780b4	UNH	LONG	85.0000	545.0000	2024-01-22	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:25.269903+00	2025-11-01 07:58:25.269903+00	\N
ff7dc307-b919-a6a6-2db4-531cbfd5e08b	e23ab931-a033-edfe-ed4f-9d02474780b4	V	LONG	170.0000	268.0000	2024-01-22	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:25.330214+00	2025-11-01 07:58:25.330214+00	\N
70e53e12-b75e-4cff-8bbd-5b572da5a6fc	e23ab931-a033-edfe-ed4f-9d02474780b4	HD	LONG	125.0000	350.0000	2024-01-25	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:25.388257+00	2025-11-01 07:58:25.388257+00	\N
aafea4f3-6ae7-8475-2160-39bb316037dc	e23ab931-a033-edfe-ed4f-9d02474780b4	PG	LONG	250.0000	165.0000	2024-01-25	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:25.454677+00	2025-11-01 07:58:25.454677+00	\N
95a4cde1-4806-4f66-2847-4ec5e9fe804d	e23ab931-a033-edfe-ed4f-9d02474780b4	GLD	LONG	325.0000	219.2300	2024-02-01	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:25.516683+00	2025-11-01 07:58:25.516683+00	\N
09c4b1c6-7d85-bf1b-c25b-a34843f34c32	e23ab931-a033-edfe-ed4f-9d02474780b4	DJP	LONG	1900.0000	30.0000	2024-02-01	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:25.602864+00	2025-11-01 07:58:25.602864+00	\N
e186da02-561a-1e30-478a-0a67443ed431	e23ab931-a033-edfe-ed4f-9d02474780b4	STARWOOD_REIT	LONG	1.0000	142500.0000	2023-06-01	\N	\N	\N	\N	\N	PRIVATE	PRIVATE_REIT	\N	\N	\N	\N	2025-11-01 07:58:25.816296+00	2025-11-01 07:58:25.816296+00	\N
eef9f9ff-bac9-ec5d-102d-330602aa1bda	e23ab931-a033-edfe-ed4f-9d02474780b4	TWO_SIGMA_FUND	LONG	1.0000	142500.0000	2023-06-01	\N	\N	\N	\N	\N	PRIVATE	HEDGE_FUND	\N	\N	\N	\N	2025-11-01 07:58:25.880575+00	2025-11-01 07:58:25.880575+00	\N
414e8934-e16e-a43a-7fd2-5144b588ab4b	e23ab931-a033-edfe-ed4f-9d02474780b4	HOME_EQUITY	LONG	1.0000	285000.0000	2023-01-15	\N	\N	\N	\N	\N	PRIVATE	\N	\N	\N	\N	\N	2025-11-01 07:58:25.938623+00	2025-11-01 07:58:25.938623+00	\N
c9e3e36b-1080-aecd-1201-840f82ed3243	e23ab931-a033-edfe-ed4f-9d02474780b4	RENTAL_SFH	LONG	1.0000	142500.0000	2021-09-01	\N	\N	\N	\N	\N	PRIVATE	\N	\N	\N	\N	\N	2025-11-01 07:58:26.064966+00	2025-11-01 07:58:26.064966+00	\N
177e21f7-34ad-22b9-3036-3194f1d40f8c	e23ab931-a033-edfe-ed4f-9d02474780b4	MONEY_MARKET	LONG	1.0000	57000.0000	2024-01-01	\N	\N	\N	\N	\N	PRIVATE	\N	\N	\N	\N	\N	2025-11-01 07:58:26.270311+00	2025-11-01 07:58:26.270311+00	\N
ed1cb925-fab2-1a0f-4f5f-ff1b97d19c8d	e23ab931-a033-edfe-ed4f-9d02474780b4	TREASURY_BILLS	LONG	1.0000	28500.0000	2024-01-01	\N	\N	\N	\N	\N	PRIVATE	\N	\N	\N	\N	\N	2025-11-01 07:58:26.373313+00	2025-11-01 07:58:26.373313+00	\N
cb498eb4-a045-7409-7b78-ab3c2b1dfb57	fcd71196-e93e-f000-5a74-31a9eead3118	NVDA	LONG	800.0000	700.0000	2024-01-05	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:26.446429+00	2025-11-01 07:58:26.446429+00	\N
b9f0b21b-8562-c86a-dfd8-a4d3bf861d07	fcd71196-e93e-f000-5a74-31a9eead3118	MSFT	LONG	1000.0000	420.0000	2024-01-05	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:26.511302+00	2025-11-01 07:58:26.511302+00	\N
a7166705-45ab-1527-c779-2e50f105eb5e	fcd71196-e93e-f000-5a74-31a9eead3118	AAPL	LONG	1500.0000	225.0000	2024-01-08	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:26.56977+00	2025-11-01 07:58:26.56977+00	\N
ff6b27d6-2003-fd8a-cd60-e39baa9a5f25	fcd71196-e93e-f000-5a74-31a9eead3118	GOOGL	LONG	1800.0000	160.0000	2024-01-08	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:26.630741+00	2025-11-01 07:58:26.630741+00	\N
794655e0-ac5a-65c9-c17b-2c082e42c24e	fcd71196-e93e-f000-5a74-31a9eead3118	META	LONG	1000.0000	265.0000	2024-01-10	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:26.688091+00	2025-11-01 07:58:26.688091+00	\N
8182dbbe-16bb-f4b6-d64a-c47be61f269d	fcd71196-e93e-f000-5a74-31a9eead3118	AMZN	LONG	1400.0000	170.0000	2024-01-10	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:26.750409+00	2025-11-01 07:58:26.750409+00	\N
36addc8c-76ac-e981-b0b5-2a7fe95ad565	fcd71196-e93e-f000-5a74-31a9eead3118	TSLA	LONG	800.0000	255.0000	2024-01-12	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:26.811768+00	2025-11-01 07:58:26.811768+00	\N
fa6ffacf-8717-af52-934e-4d2d915a9df8	fcd71196-e93e-f000-5a74-31a9eead3118	AMD	LONG	1200.0000	162.0000	2024-01-12	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:26.871865+00	2025-11-01 07:58:26.871865+00	\N
7b742620-07dd-e3c4-3711-d217a078b6d8	fcd71196-e93e-f000-5a74-31a9eead3118	BRK-B	LONG	600.0000	440.0000	2024-01-15	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:26.931255+00	2025-11-01 07:58:26.931255+00	\N
8fc46cbb-a19d-4e04-d305-6c7c8fbd5450	fcd71196-e93e-f000-5a74-31a9eead3118	JPM	LONG	1000.0000	170.0000	2024-01-15	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:26.993262+00	2025-11-01 07:58:26.993262+00	\N
6a760c61-dd99-7cd5-6d92-f017e3951df2	fcd71196-e93e-f000-5a74-31a9eead3118	JNJ	LONG	800.0000	160.0000	2024-01-18	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:27.052239+00	2025-11-01 07:58:27.052239+00	\N
e32cf196-33d7-106a-bf8d-2eff19f16108	fcd71196-e93e-f000-5a74-31a9eead3118	UNH	LONG	200.0000	545.0000	2024-01-18	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:27.103599+00	2025-11-01 07:58:27.103599+00	\N
02b7f65d-8ace-71fc-17f3-1279376247e4	fcd71196-e93e-f000-5a74-31a9eead3118	V	LONG	350.0000	268.0000	2024-01-20	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:27.156071+00	2025-11-01 07:58:27.156071+00	\N
1e88b0bb-1da5-2f38-f6d1-6594cb3462c4	fcd71196-e93e-f000-5a74-31a9eead3118	NFLX	SHORT	-600.0000	490.0000	2024-01-25	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:27.209923+00	2025-11-01 07:58:27.209923+00	\N
99b03662-0fcb-b2a0-96a9-d0d23d8c0b1d	fcd71196-e93e-f000-5a74-31a9eead3118	SHOP	SHORT	-1000.0000	195.0000	2024-01-25	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:27.245479+00	2025-11-01 07:58:27.245479+00	\N
6648b795-c9ee-7cc4-7b5b-e2f740dcfc82	fcd71196-e93e-f000-5a74-31a9eead3118	ZM	SHORT	-2000.0000	70.0000	2024-01-28	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:27.290915+00	2025-11-01 07:58:27.290915+00	\N
0bb50439-7d17-1a5e-ea31-4e026faa7fb0	fcd71196-e93e-f000-5a74-31a9eead3118	PTON	SHORT	-3000.0000	40.0000	2024-01-28	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:27.329016+00	2025-11-01 07:58:27.329016+00	\N
9e385327-160a-098e-4dd8-2d0244ebbdcb	fcd71196-e93e-f000-5a74-31a9eead3118	ROKU	SHORT	-1800.0000	60.0000	2024-01-30	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:27.361278+00	2025-11-01 07:58:27.361278+00	\N
721561b3-4b12-7f59-0f40-820515457c1e	fcd71196-e93e-f000-5a74-31a9eead3118	XOM	SHORT	-2000.0000	110.0000	2024-02-01	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:27.400982+00	2025-11-01 07:58:27.400982+00	\N
d95b392f-38c7-e4a4-93eb-7e8d5a3bce35	fcd71196-e93e-f000-5a74-31a9eead3118	F	SHORT	-10000.0000	12.0000	2024-02-01	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:27.44117+00	2025-11-01 07:58:27.44117+00	\N
412b2a7f-b3ff-6503-efce-65b1982cb9b6	fcd71196-e93e-f000-5a74-31a9eead3118	GE	SHORT	-800.0000	140.0000	2024-02-05	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:27.478028+00	2025-11-01 07:58:27.478028+00	\N
098de461-2c8a-ff40-83c1-aeb5a0b0f26a	fcd71196-e93e-f000-5a74-31a9eead3118	C	SHORT	-2000.0000	55.0000	2024-02-05	\N	\N	\N	\N	\N	PUBLIC	\N	\N	\N	\N	\N	2025-11-01 07:58:27.524993+00	2025-11-01 07:58:27.524993+00	\N
1b820294-9860-9dda-1596-587211100df5	fcd71196-e93e-f000-5a74-31a9eead3118	NVDA251017C00800000	LC	50.0000	12.5000	2024-01-15	\N	\N	NVDA	800.0000	2025-10-17	OPTIONS	\N	\N	\N	\N	\N	2025-11-01 07:58:27.702482+00	2025-11-01 08:00:20.067173+00	\N
7bb2f870-6c7c-d07f-0b24-9980b942798d	fcd71196-e93e-f000-5a74-31a9eead3118	QQQ250815C00420000	LC	150.0000	7.0000	2024-01-10	\N	\N	QQQ	420.0000	2025-08-15	OPTIONS	\N	\N	\N	\N	\N	2025-11-01 07:58:27.620741+00	2025-11-01 08:00:20.067173+00	\N
bd1cf22d-c93a-fa22-a107-882e4473f177	fcd71196-e93e-f000-5a74-31a9eead3118	META250919P00450000	SP	-50.0000	7.5000	2024-01-25	\N	\N	META	450.0000	2025-09-19	OPTIONS	\N	\N	\N	\N	\N	2025-11-01 07:58:27.876541+00	2025-11-01 08:00:20.067173+00	\N
c1a374d6-2d41-776f-9b25-26e9996ee9ac	fcd71196-e93e-f000-5a74-31a9eead3118	AAPL250815P00200000	SP	-100.0000	4.5000	2024-01-20	\N	\N	AAPL	200.0000	2025-08-15	OPTIONS	\N	\N	\N	\N	\N	2025-11-01 07:58:27.743697+00	2025-11-01 08:00:20.067173+00	\N
d2af8406-8a9f-81bc-3b0b-a81375f3c747	fcd71196-e93e-f000-5a74-31a9eead3118	VIX250716C00025000	LC	300.0000	2.5000	2024-01-15	\N	\N	VIX	25.0000	2025-07-16	OPTIONS	\N	\N	\N	\N	\N	2025-11-01 07:58:27.663356+00	2025-11-01 08:00:20.067173+00	\N
d5957bbc-8bc3-a848-990f-fbd552cc54e9	fcd71196-e93e-f000-5a74-31a9eead3118	TSLA250815C00300000	SC	-60.0000	8.0000	2024-01-25	\N	\N	TSLA	300.0000	2025-08-15	OPTIONS	\N	\N	\N	\N	\N	2025-11-01 07:58:27.827784+00	2025-11-01 08:00:20.067173+00	\N
dbacb2bf-e360-43ec-bd34-3ba959e9958e	fcd71196-e93e-f000-5a74-31a9eead3118	SPY250919C00460000	LC	200.0000	7.0000	2024-01-10	\N	\N	SPY	460.0000	2025-09-19	OPTIONS	\N	\N	\N	\N	\N	2025-11-01 07:58:27.57175+00	2025-11-01 08:00:20.067173+00	\N
f001677f-f77b-39ba-df96-b1917a0c62ef	fcd71196-e93e-f000-5a74-31a9eead3118	MSFT250919P00380000	SP	-80.0000	5.0000	2024-01-20	\N	\N	MSFT	380.0000	2025-09-19	OPTIONS	\N	\N	\N	\N	\N	2025-11-01 07:58:27.784479+00	2025-11-01 08:00:20.067173+00	\N
1901e980-86bd-4a07-4b15-2665f320affa	e23ab931-a033-edfe-ed4f-9d02474780b4	CRYPTO_BTC_ETH	LONG	1.0000	42750.0000	2023-03-01	\N	\N	\N	\N	\N	PRIVATE	\N	\N	\N	\N	\N	2025-11-01 07:58:26.145221+00	2025-11-01 08:00:58.645771+00	\N
2c068dbf-590a-6426-6268-abf3e359df7c	e23ab931-a033-edfe-ed4f-9d02474780b4	A16Z_VC_FUND	LONG	1.0000	142500.0000	2023-06-01	\N	\N	\N	\N	\N	PRIVATE	VENTURE_CAPITAL	\N	\N	\N	\N	2025-11-01 07:58:25.750667+00	2025-11-01 08:00:58.645771+00	\N
3b6d1fa7-1f9e-4173-6f6d-054cf222b60a	e23ab931-a033-edfe-ed4f-9d02474780b4	ART_COLLECTIBLES	LONG	1.0000	28500.0000	2022-11-01	\N	\N	\N	\N	\N	PRIVATE	\N	\N	\N	\N	\N	2025-11-01 07:58:26.205666+00	2025-11-01 08:00:58.645771+00	\N
f179e1ff-44c8-bc3f-be8f-739f923abaa0	e23ab931-a033-edfe-ed4f-9d02474780b4	BX_PRIVATE_EQUITY	LONG	1.0000	285000.0000	2023-06-01	\N	\N	\N	\N	\N	PRIVATE	PRIVATE_EQUITY	\N	\N	\N	\N	2025-11-01 07:58:25.687142+00	2025-11-01 08:00:58.645771+00	\N
fad18fd5-beda-baa2-2dc7-8ebb9c1db6dd	e23ab931-a033-edfe-ed4f-9d02474780b4	RENTAL_CONDO	LONG	1.0000	142500.0000	2022-06-01	\N	\N	\N	\N	\N	PRIVATE	\N	\N	\N	\N	\N	2025-11-01 07:58:26.002816+00	2025-11-01 08:00:58.645771+00	\N
\.


--
-- Data for Name: stress_test_results; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.stress_test_results (id, portfolio_id, scenario_id, calculation_date, direct_pnl, correlated_pnl, correlation_effect, factor_impacts, calculation_metadata, created_at) FROM stdin;
\.


--
-- Data for Name: stress_test_scenarios; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.stress_test_scenarios (id, scenario_id, name, description, category, severity, shock_config, active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: tags; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.tags (id) FROM stdin;
\.


--
-- Data for Name: tags_v2; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.tags_v2 (id, user_id, name, color, description, display_order, usage_count, is_archived, archived_at, archived_by, created_at, updated_at) FROM stdin;
503c0196-5ce5-4c7a-891e-da1555788131	9dacfb0f-2123-7a94-debc-0f982b90d845	Core Index	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:24.496911+00	2025-11-01 03:58:24.548106+00
fc6c3754-6586-4fe9-a99e-7fa5095a4347	9dacfb0f-2123-7a94-debc-0f982b90d845	Primary Residence	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:25.924676+00	2025-11-01 03:58:25.969355+00
0467dac0-a67e-414a-a124-e65d13598dbd	b13cd6e9-6a6e-c644-8a44-e710b2868e54	AI Play	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:26.42244+00	2025-11-01 03:58:26.474264+00
f0931dc9-1799-4215-99ce-f891e8344810	9dacfb0f-2123-7a94-debc-0f982b90d845	Tech Index	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:24.567724+00	2025-11-01 03:58:24.619251+00
5f8f69ec-84cb-4928-95a7-56f1ff1b41eb	9dacfb0f-2123-7a94-debc-0f982b90d845	Total Market	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:24.642124+00	2025-11-01 03:58:24.687664+00
d9e9d88b-8155-4d10-b962-a8bbd40b7fc0	b13cd6e9-6a6e-c644-8a44-e710b2868e54	AWS Growth	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:26.736358+00	2025-11-01 03:58:26.778213+00
0fcb4eef-adc9-47a6-b005-7492ee16d054	9dacfb0f-2123-7a94-debc-0f982b90d845	Blue Chip	#4A90E2	\N	0	16	f	\N	\N	2025-11-01 03:58:24.496911+00	2025-11-01 03:58:25.438478+00
23c7f0c0-c741-42b6-94a5-2f4f8844b97c	fd5f083c-6ffc-df32-89ca-a4044b5723f5	Tech Growth	#4A90E2	\N	0	6	f	\N	\N	2025-11-01 03:58:23.593826+00	2025-11-01 03:58:23.920536+00
ffecdffb-83df-45f6-9d5c-835e47538321	9dacfb0f-2123-7a94-debc-0f982b90d845	Individual Stock	#4A90E2	\N	0	13	f	\N	\N	2025-11-01 03:58:24.707703+00	2025-11-01 03:58:25.484069+00
c4b8febf-753d-4cf7-86e5-2181cd57539f	fd5f083c-6ffc-df32-89ca-a4044b5723f5	Dividend Income	#4A90E2	\N	0	2	f	\N	\N	2025-11-01 03:58:23.957057+00	2025-11-01 03:58:23.995145+00
7ab18b7b-7479-4635-b8a8-d62a0a89851c	9dacfb0f-2123-7a94-debc-0f982b90d845	Real Estate	#4A90E2	\N	0	3	f	\N	\N	2025-11-01 03:58:25.924676+00	2025-11-01 03:58:26.050706+00
104a8cc5-e59a-49c2-843a-ff8126dfdd55	9dacfb0f-2123-7a94-debc-0f982b90d845	Rental Property	#4A90E2	\N	0	2	f	\N	\N	2025-11-01 03:58:25.989193+00	2025-11-01 03:58:26.094551+00
9516be79-1ac1-41d8-8db4-52d6083044ff	fd5f083c-6ffc-df32-89ca-a4044b5723f5	Large Cap Growth	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:24.065177+00	2025-11-01 03:58:24.103783+00
815a6893-2626-4491-9a3f-d67523fb4f24	9dacfb0f-2123-7a94-debc-0f982b90d845	Gold	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:25.50391+00	2025-11-01 03:58:25.573133+00
89c367ba-a3f7-4592-84a1-1b2ad080b82d	fd5f083c-6ffc-df32-89ca-a4044b5723f5	Large Cap Blend	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:24.122115+00	2025-11-01 03:58:24.164187+00
2230327e-376a-4345-816b-4de3f60e1bb1	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Cloud Dominance	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:26.494345+00	2025-11-01 03:58:26.53898+00
c3904fc7-86fc-44ca-89fa-b11f0f55c05b	9dacfb0f-2123-7a94-debc-0f982b90d845	Risk Hedge	#4A90E2	\N	0	2	f	\N	\N	2025-11-01 03:58:25.50391+00	2025-11-01 03:58:25.634259+00
9193d038-bf06-457a-8c6c-0a6139f52b87	9dacfb0f-2123-7a94-debc-0f982b90d845	Commodities	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:25.59065+00	2025-11-01 03:58:25.653446+00
ccb572af-1228-4aab-9b79-3b9a10836c74	fd5f083c-6ffc-df32-89ca-a4044b5723f5	International	#4A90E2	\N	0	2	f	\N	\N	2025-11-01 03:58:24.183103+00	2025-11-01 03:58:24.280722+00
4cc1fd73-f967-46bf-860c-23fefac8f881	fd5f083c-6ffc-df32-89ca-a4044b5723f5	Total Market	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:24.304268+00	2025-11-01 03:58:24.350576+00
3cf23106-c86c-4f38-ab71-4ccd949718f9	9dacfb0f-2123-7a94-debc-0f982b90d845	Private Equity	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:25.672568+00	2025-11-01 03:58:25.718351+00
9e60772c-eed3-4dfd-8a47-e006f6f61e7d	fd5f083c-6ffc-df32-89ca-a4044b5723f5	Bonds	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:24.370345+00	2025-11-01 03:58:24.417097+00
32715e38-dd50-4dd3-8566-9fbba018c229	9dacfb0f-2123-7a94-debc-0f982b90d845	Cryptocurrency	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:26.129768+00	2025-11-01 03:58:26.171802+00
eeb2dc69-18a1-4fe0-b448-679923dcb79b	fd5f083c-6ffc-df32-89ca-a4044b5723f5	Core Holdings	#4A90E2	\N	0	12	f	\N	\N	2025-11-01 03:58:23.593826+00	2025-11-01 03:58:24.437099+00
15b8bef6-c7bc-4dc7-8775-1bd6a48d1b20	fd5f083c-6ffc-df32-89ca-a4044b5723f5	REITs	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:24.437099+00	2025-11-01 03:58:24.477872+00
771afdd9-12a5-4b73-938e-ee43f294dc3b	fd5f083c-6ffc-df32-89ca-a4044b5723f5	Uncategorized	#9E9E9E	Positions without sector classification	0	16	f	\N	\N	2025-11-01 03:58:23.690026+00	2025-11-01 03:58:24.496911+00
a640f97a-06ef-4abd-ae5a-a19cfb7a8fe4	9dacfb0f-2123-7a94-debc-0f982b90d845	Venture Capital	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:25.736671+00	2025-11-01 03:58:25.778813+00
a173d206-ccbb-41e1-b19c-f82b6da8a089	9dacfb0f-2123-7a94-debc-0f982b90d845	Alternative Assets	#4A90E2	\N	0	4	f	\N	\N	2025-11-01 03:58:25.50391+00	2025-11-01 03:58:26.190215+00
098f581d-9421-4de1-ae12-265fee641f9e	9dacfb0f-2123-7a94-debc-0f982b90d845	Private REIT	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:25.800752+00	2025-11-01 03:58:25.846564+00
559a530f-1ad0-4aac-8fb0-741319573365	9dacfb0f-2123-7a94-debc-0f982b90d845	Art	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:26.190215+00	2025-11-01 03:58:26.23595+00
a4940399-0cee-4962-ab76-62bea51cadd1	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Bank Quality	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:26.978823+00	2025-11-01 03:58:27.02104+00
3643615f-e7de-4c2b-9f55-46aa40d88864	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Ecosystem Moat	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:26.557039+00	2025-11-01 03:58:26.597603+00
138e39db-377f-4246-bad6-22c785ac408a	9dacfb0f-2123-7a94-debc-0f982b90d845	Private Investments	#4A90E2	\N	0	4	f	\N	\N	2025-11-01 03:58:25.672568+00	2025-11-01 03:58:25.866963+00
3e51af9c-1116-479a-b5fd-41cb42648d01	9dacfb0f-2123-7a94-debc-0f982b90d845	Hedge Fund	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:25.866963+00	2025-11-01 03:58:25.906474+00
0f7a1767-be76-4ce2-9afb-9ffb931fe50e	b13cd6e9-6a6e-c644-8a44-e710b2868e54	EV Revolution	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:26.79739+00	2025-11-01 03:58:26.839755+00
78bde295-e1a7-4a74-ba21-c380b76cb633	9dacfb0f-2123-7a94-debc-0f982b90d845	Money Market	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:26.255979+00	2025-11-01 03:58:26.301494+00
3045ee77-b50d-460c-be14-7af7bb09e26f	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Long Value	#4A90E2	\N	0	5	f	\N	\N	2025-11-01 03:58:26.917678+00	2025-11-01 03:58:27.145552+00
af9059a6-c71b-49a9-bef2-1623ddce4ec4	9dacfb0f-2123-7a94-debc-0f982b90d845	Cash	#4A90E2	\N	0	2	f	\N	\N	2025-11-01 03:58:26.255979+00	2025-11-01 03:58:26.360474+00
2502186e-5c10-45b9-87c1-1401f71ff2e0	9dacfb0f-2123-7a94-debc-0f982b90d845	Fixed Income	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:26.360474+00	2025-11-01 03:58:26.402962+00
e66adeb0-6645-4821-b312-35e3ff9a73d5	9dacfb0f-2123-7a94-debc-0f982b90d845	Uncategorized	#9E9E9E	Positions without sector classification	0	29	f	\N	\N	2025-11-01 03:58:24.567724+00	2025-11-01 03:58:26.42244+00
d82d4ea7-b096-4664-9745-8b09cdfb8bb0	b13cd6e9-6a6e-c644-8a44-e710b2868e54	AI & Search	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:26.617073+00	2025-11-01 03:58:26.657218+00
0851d4fd-fec5-4d55-85b5-afea80c3b210	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Payment Network	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:27.145552+00	2025-11-01 03:58:27.181039+00
84d10043-4721-4c54-9f8f-aaf27b725e48	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Metaverse	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:26.674451+00	2025-11-01 03:58:26.71705+00
97e2cf05-57e0-4434-b312-ba43fb3c02b2	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Healthcare Defensive	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:27.039366+00	2025-11-01 03:58:27.076234+00
397dc979-36a1-4199-984c-0b8909f11151	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Long Momentum	#4A90E2	\N	0	8	f	\N	\N	2025-11-01 03:58:26.42244+00	2025-11-01 03:58:26.858507+00
32449c38-a426-43fb-88ff-d8a9c55af872	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Data Center	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:26.858507+00	2025-11-01 03:58:26.898187+00
d392b948-bf82-4b70-acab-764486d98735	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Short Value Traps	#4A90E2	\N	0	9	f	\N	\N	2025-11-01 03:58:27.197931+00	2025-11-01 03:58:27.512378+00
afe5a6e7-ecd2-4b2c-88f4-373161847687	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Quality	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:26.917678+00	2025-11-01 03:58:26.96116+00
e813c891-0212-40bf-b668-1075ed904a64	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Uncategorized	#9E9E9E	Positions without sector classification	0	30	f	\N	\N	2025-11-01 03:58:26.494345+00	2025-11-01 04:23:14.63648+00
a2b53588-f92f-4e0b-a896-791d8b4b2bb8	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Healthcare Quality	#4A90E2	\N	0	1	f	\N	\N	2025-11-01 03:58:27.092507+00	2025-11-01 03:58:27.128556+00
4b8bcfa9-da85-4655-8c77-bcfe6b8e0553	fd5f083c-6ffc-df32-89ca-a4044b5723f5	Communication Services	#3F51B5	Sector: Communication Services	0	1	f	\N	\N	2025-11-01 04:23:14.303358+00	2025-11-01 04:23:14.303358+00
a53083e1-1658-48ea-aad6-de94f26001f6	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Options Overlay	#4A90E2	\N	0	8	f	\N	\N	2025-11-01 03:58:27.55843+00	2025-11-01 03:58:27.862361+00
2e104f4e-c2fa-4aa5-8d69-5eeeba7216b8	fd5f083c-6ffc-df32-89ca-a4044b5723f5	Consumer Cyclical	#9C27B0	Sector: Consumer Cyclical	0	2	f	\N	\N	2025-11-01 04:23:14.303358+00	2025-11-01 04:23:14.303358+00
3f6e937c-acab-4531-9583-c70bdbb66796	fd5f083c-6ffc-df32-89ca-a4044b5723f5	Technology	#2196F3	Sector: Technology	0	3	f	\N	\N	2025-11-01 04:23:14.303358+00	2025-11-01 04:23:14.303358+00
a6d17fc7-c622-47d0-85b6-b918fd83ccb9	fd5f083c-6ffc-df32-89ca-a4044b5723f5	Healthcare	#4CAF50	Sector: Healthcare	0	1	f	\N	\N	2025-11-01 04:23:14.303358+00	2025-11-01 04:23:14.303358+00
a0c692e8-9526-4ec6-aa36-f2e6c0e00154	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Financial Services	#FF9800	Sector: Financial Services	0	4	f	\N	\N	2025-11-01 04:23:14.63648+00	2025-11-01 04:23:14.63648+00
398a8280-2e94-4120-a5d7-f5a705c17f78	fd5f083c-6ffc-df32-89ca-a4044b5723f5	Financial Services	#FF9800	Sector: Financial Services	0	2	f	\N	\N	2025-11-01 04:23:14.303358+00	2025-11-01 04:23:14.303358+00
58c827d0-4bc7-445d-8c83-d5c5c2c92832	9dacfb0f-2123-7a94-debc-0f982b90d845	Technology	#2196F3	Sector: Technology	0	3	f	\N	\N	2025-11-01 04:23:14.454568+00	2025-11-01 04:23:14.454568+00
4b1def4d-871c-4e26-9800-4b7526c2baae	9dacfb0f-2123-7a94-debc-0f982b90d845	Communication Services	#3F51B5	Sector: Communication Services	0	2	f	\N	\N	2025-11-01 04:23:14.454568+00	2025-11-01 04:23:14.454568+00
87d9c81f-540f-47d4-ab1f-06ea9ae7072c	9dacfb0f-2123-7a94-debc-0f982b90d845	Healthcare	#4CAF50	Sector: Healthcare	0	2	f	\N	\N	2025-11-01 04:23:14.454568+00	2025-11-01 04:23:14.454568+00
639f38b4-71b0-43ee-a71a-5c25741314fd	9dacfb0f-2123-7a94-debc-0f982b90d845	Financial Services	#FF9800	Sector: Financial Services	0	3	f	\N	\N	2025-11-01 04:23:14.454568+00	2025-11-01 04:23:14.454568+00
e1875673-5025-4917-8350-8e3c1be86b4a	9dacfb0f-2123-7a94-debc-0f982b90d845	Consumer Cyclical	#9C27B0	Sector: Consumer Cyclical	0	2	f	\N	\N	2025-11-01 04:23:14.454568+00	2025-11-01 04:23:14.454568+00
429df1ab-dcc6-4b60-8543-5c060e6befce	9dacfb0f-2123-7a94-debc-0f982b90d845	Consumer Defensive	#E91E63	Sector: Consumer Defensive	0	1	f	\N	\N	2025-11-01 04:23:14.454568+00	2025-11-01 04:23:14.454568+00
a4221c36-b722-4b05-929b-ec9e76e256ef	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Healthcare	#4CAF50	Sector: Healthcare	0	2	f	\N	\N	2025-11-01 04:23:14.63648+00	2025-11-01 04:23:14.63648+00
755149b8-0d5e-486d-9c52-8233496fe41a	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Technology	#2196F3	Sector: Technology	0	6	f	\N	\N	2025-11-01 04:23:14.63648+00	2025-11-01 04:23:14.63648+00
620953a7-cf1a-4a1a-b010-991699a2576a	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Communication Services	#3F51B5	Sector: Communication Services	0	4	f	\N	\N	2025-11-01 04:23:14.63648+00	2025-11-01 04:23:14.63648+00
000484c8-91dc-4b97-b984-e3d49af559d2	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Energy	#FFC107	Sector: Energy	0	1	f	\N	\N	2025-11-01 04:23:14.63648+00	2025-11-01 04:23:14.63648+00
22691010-2cf8-464c-8498-64fbacb80834	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Consumer Cyclical	#9C27B0	Sector: Consumer Cyclical	0	4	f	\N	\N	2025-11-01 04:23:14.63648+00	2025-11-01 04:23:14.63648+00
bbe91ac9-bfcf-425f-83f6-3ad79a23a4de	b13cd6e9-6a6e-c644-8a44-e710b2868e54	Industrials	#795548	Sector: Industrials	0	1	f	\N	\N	2025-11-01 04:23:14.63648+00	2025-11-01 04:23:14.63648+00
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: sigmasight
--

COPY public.users (id, email, hashed_password, full_name, is_active, created_at, updated_at) FROM stdin;
fd5f083c-6ffc-df32-89ca-a4044b5723f5	demo_individual@sigmasight.com	$2b$12$yBLKD2CtzYMDU6fRKlXXgOas.ORsQ8EEWZBJRgbpu5GeK5Letfoz6	Demo Individual Investor	t	2025-11-01 07:58:23.176434+00	2025-11-01 07:58:23.176434+00
9dacfb0f-2123-7a94-debc-0f982b90d845	demo_hnw@sigmasight.com	$2b$12$NBW5syovzOUS4uQHDvpx3eF8WjvgS1d1ipHV0wCoVmGmMmus5OVay	Demo High Net Worth Investor	t	2025-11-01 07:58:23.375656+00	2025-11-01 07:58:23.375656+00
b13cd6e9-6a6e-c644-8a44-e710b2868e54	demo_hedgefundstyle@sigmasight.com	$2b$12$p7E5Pm0rYWsRNelzQL9dkOmBUt6AyKUcMvfDI1SH8a5ZdM9qVyuDq	Demo Hedge Fund Style Investor	t	2025-11-01 07:58:23.578252+00	2025-11-01 07:58:23.578252+00
\.


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: agent_conversations pk_agent_conversations; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.agent_conversations
    ADD CONSTRAINT pk_agent_conversations PRIMARY KEY (id);


--
-- Name: agent_messages pk_agent_messages; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.agent_messages
    ADD CONSTRAINT pk_agent_messages PRIMARY KEY (id);


--
-- Name: agent_user_preferences pk_agent_user_preferences; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.agent_user_preferences
    ADD CONSTRAINT pk_agent_user_preferences PRIMARY KEY (id);


--
-- Name: ai_insight_templates pk_ai_insight_templates; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.ai_insight_templates
    ADD CONSTRAINT pk_ai_insight_templates PRIMARY KEY (id);


--
-- Name: ai_insights pk_ai_insights; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.ai_insights
    ADD CONSTRAINT pk_ai_insights PRIMARY KEY (id);


--
-- Name: batch_job_schedules pk_batch_job_schedules; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.batch_job_schedules
    ADD CONSTRAINT pk_batch_job_schedules PRIMARY KEY (id);


--
-- Name: batch_jobs pk_batch_jobs; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.batch_jobs
    ADD CONSTRAINT pk_batch_jobs PRIMARY KEY (id);


--
-- Name: batch_run_tracking pk_batch_run_tracking; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.batch_run_tracking
    ADD CONSTRAINT pk_batch_run_tracking PRIMARY KEY (id);


--
-- Name: benchmarks_sector_weights pk_benchmarks_sector_weights; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.benchmarks_sector_weights
    ADD CONSTRAINT pk_benchmarks_sector_weights PRIMARY KEY (id);


--
-- Name: company_profiles pk_company_profiles; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.company_profiles
    ADD CONSTRAINT pk_company_profiles PRIMARY KEY (symbol);


--
-- Name: correlation_calculations pk_correlation_calculations; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.correlation_calculations
    ADD CONSTRAINT pk_correlation_calculations PRIMARY KEY (id);


--
-- Name: correlation_cluster_positions pk_correlation_cluster_positions; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.correlation_cluster_positions
    ADD CONSTRAINT pk_correlation_cluster_positions PRIMARY KEY (id);


--
-- Name: correlation_clusters pk_correlation_clusters; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.correlation_clusters
    ADD CONSTRAINT pk_correlation_clusters PRIMARY KEY (id);


--
-- Name: export_history pk_export_history; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.export_history
    ADD CONSTRAINT pk_export_history PRIMARY KEY (id);


--
-- Name: factor_correlations pk_factor_correlations; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.factor_correlations
    ADD CONSTRAINT pk_factor_correlations PRIMARY KEY (id);


--
-- Name: factor_definitions pk_factor_definitions; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.factor_definitions
    ADD CONSTRAINT pk_factor_definitions PRIMARY KEY (id);


--
-- Name: factor_exposures pk_factor_exposures; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.factor_exposures
    ADD CONSTRAINT pk_factor_exposures PRIMARY KEY (id);


--
-- Name: fund_holdings pk_fund_holdings; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.fund_holdings
    ADD CONSTRAINT pk_fund_holdings PRIMARY KEY (id);


--
-- Name: market_data_cache pk_market_data_cache; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.market_data_cache
    ADD CONSTRAINT pk_market_data_cache PRIMARY KEY (id);


--
-- Name: market_risk_scenarios pk_market_risk_scenarios; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.market_risk_scenarios
    ADD CONSTRAINT pk_market_risk_scenarios PRIMARY KEY (id);


--
-- Name: modeling_session_snapshots pk_modeling_session_snapshots; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.modeling_session_snapshots
    ADD CONSTRAINT pk_modeling_session_snapshots PRIMARY KEY (id);


--
-- Name: pairwise_correlations pk_pairwise_correlations; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.pairwise_correlations
    ADD CONSTRAINT pk_pairwise_correlations PRIMARY KEY (id);


--
-- Name: portfolio_snapshots pk_portfolio_snapshots; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.portfolio_snapshots
    ADD CONSTRAINT pk_portfolio_snapshots PRIMARY KEY (id);


--
-- Name: portfolio_target_prices pk_portfolio_target_prices; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.portfolio_target_prices
    ADD CONSTRAINT pk_portfolio_target_prices PRIMARY KEY (id);


--
-- Name: portfolios pk_portfolios; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.portfolios
    ADD CONSTRAINT pk_portfolios PRIMARY KEY (id);


--
-- Name: position_factor_exposures pk_position_factor_exposures; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_factor_exposures
    ADD CONSTRAINT pk_position_factor_exposures PRIMARY KEY (id);


--
-- Name: position_greeks pk_position_greeks; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_greeks
    ADD CONSTRAINT pk_position_greeks PRIMARY KEY (id);


--
-- Name: position_interest_rate_betas pk_position_interest_rate_betas; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_interest_rate_betas
    ADD CONSTRAINT pk_position_interest_rate_betas PRIMARY KEY (id);


--
-- Name: position_market_betas pk_position_market_betas; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_market_betas
    ADD CONSTRAINT pk_position_market_betas PRIMARY KEY (id);


--
-- Name: position_tags pk_position_tags; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_tags
    ADD CONSTRAINT pk_position_tags PRIMARY KEY (id);


--
-- Name: position_volatility pk_position_volatility; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_volatility
    ADD CONSTRAINT pk_position_volatility PRIMARY KEY (id);


--
-- Name: positions pk_positions; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.positions
    ADD CONSTRAINT pk_positions PRIMARY KEY (id);


--
-- Name: stress_test_results pk_stress_test_results; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.stress_test_results
    ADD CONSTRAINT pk_stress_test_results PRIMARY KEY (id);


--
-- Name: stress_test_scenarios pk_stress_test_scenarios; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.stress_test_scenarios
    ADD CONSTRAINT pk_stress_test_scenarios PRIMARY KEY (id);


--
-- Name: tags pk_tags; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.tags
    ADD CONSTRAINT pk_tags PRIMARY KEY (id);


--
-- Name: tags_v2 pk_tags_v2; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.tags_v2
    ADD CONSTRAINT pk_tags_v2 PRIMARY KEY (id);


--
-- Name: users pk_users; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT pk_users PRIMARY KEY (id);


--
-- Name: tags_v2 unique_active_tag_name_v2; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.tags_v2
    ADD CONSTRAINT unique_active_tag_name_v2 UNIQUE (user_id, name, is_archived);


--
-- Name: position_tags unique_position_tag; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_tags
    ADD CONSTRAINT unique_position_tag UNIQUE (position_id, tag_id);


--
-- Name: agent_user_preferences uq_agent_user_preferences_user_id; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.agent_user_preferences
    ADD CONSTRAINT uq_agent_user_preferences_user_id UNIQUE (user_id);


--
-- Name: batch_job_schedules uq_batch_job_schedules_job_name; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.batch_job_schedules
    ADD CONSTRAINT uq_batch_job_schedules_job_name UNIQUE (job_name);


--
-- Name: batch_run_tracking uq_batch_run_tracking_run_date; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.batch_run_tracking
    ADD CONSTRAINT uq_batch_run_tracking_run_date UNIQUE (run_date);


--
-- Name: benchmarks_sector_weights uq_benchmark_sector_date; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.benchmarks_sector_weights
    ADD CONSTRAINT uq_benchmark_sector_date UNIQUE (benchmark_code, asof_date, sector);


--
-- Name: correlation_calculations uq_correlation_calculations_portfolio_id; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.correlation_calculations
    ADD CONSTRAINT uq_correlation_calculations_portfolio_id UNIQUE (portfolio_id, duration_days, calculation_date);


--
-- Name: factor_correlations uq_factor_correlations_factors_date; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.factor_correlations
    ADD CONSTRAINT uq_factor_correlations_factors_date UNIQUE (factor_1_id, factor_2_id, calculation_date);


--
-- Name: factor_definitions uq_factor_definitions_name; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.factor_definitions
    ADD CONSTRAINT uq_factor_definitions_name UNIQUE (name);


--
-- Name: factor_exposures uq_factor_exposures_portfolio_factor_date; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.factor_exposures
    ADD CONSTRAINT uq_factor_exposures_portfolio_factor_date UNIQUE (portfolio_id, factor_id, calculation_date);


--
-- Name: fund_holdings uq_fund_holdings_fund_holding_date; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.fund_holdings
    ADD CONSTRAINT uq_fund_holdings_fund_holding_date UNIQUE (fund_symbol, holding_symbol, last_updated);


--
-- Name: market_data_cache uq_market_data_cache_symbol_date; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.market_data_cache
    ADD CONSTRAINT uq_market_data_cache_symbol_date UNIQUE (symbol, date);


--
-- Name: portfolio_snapshots uq_portfolio_snapshots_portfolio_date; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.portfolio_snapshots
    ADD CONSTRAINT uq_portfolio_snapshots_portfolio_date UNIQUE (portfolio_id, snapshot_date);


--
-- Name: portfolio_target_prices uq_portfolio_symbol_type; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.portfolio_target_prices
    ADD CONSTRAINT uq_portfolio_symbol_type UNIQUE (portfolio_id, symbol, position_type);


--
-- Name: portfolios uq_portfolios_user_id; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.portfolios
    ADD CONSTRAINT uq_portfolios_user_id UNIQUE (user_id);


--
-- Name: position_market_betas uq_position_beta_calc; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_market_betas
    ADD CONSTRAINT uq_position_beta_calc UNIQUE (portfolio_id, position_id, calc_date, method, window_days);


--
-- Name: position_factor_exposures uq_position_factor_date; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_factor_exposures
    ADD CONSTRAINT uq_position_factor_date UNIQUE (position_id, factor_id, calculation_date);


--
-- Name: position_greeks uq_position_greeks_position_id; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_greeks
    ADD CONSTRAINT uq_position_greeks_position_id UNIQUE (position_id);


--
-- Name: position_volatility uq_position_volatility_date; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_volatility
    ADD CONSTRAINT uq_position_volatility_date UNIQUE (position_id, calculation_date);


--
-- Name: stress_test_scenarios uq_stress_test_scenarios_scenario_id; Type: CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.stress_test_scenarios
    ADD CONSTRAINT uq_stress_test_scenarios_scenario_id UNIQUE (scenario_id);


--
-- Name: idx_active_sessions; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_active_sessions ON public.modeling_session_snapshots USING btree (user_id, status);


--
-- Name: idx_agent_conversations_created_at; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_agent_conversations_created_at ON public.agent_conversations USING btree (created_at);


--
-- Name: idx_agent_conversations_provider_thread_id; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_agent_conversations_provider_thread_id ON public.agent_conversations USING btree (provider_thread_id);


--
-- Name: idx_agent_conversations_user_id; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_agent_conversations_user_id ON public.agent_conversations USING btree (user_id);


--
-- Name: idx_agent_messages_conversation_id; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_agent_messages_conversation_id ON public.agent_messages USING btree (conversation_id);


--
-- Name: idx_agent_messages_created_at; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_agent_messages_created_at ON public.agent_messages USING btree (created_at);


--
-- Name: idx_agent_user_preferences_user_id; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_agent_user_preferences_user_id ON public.agent_user_preferences USING btree (user_id);


--
-- Name: idx_batch_run_date; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_batch_run_date ON public.batch_run_tracking USING btree (run_date);


--
-- Name: idx_benchmark_lookup; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_benchmark_lookup ON public.benchmarks_sector_weights USING btree (benchmark_code, asof_date);


--
-- Name: idx_benchmark_sector; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_benchmark_sector ON public.benchmarks_sector_weights USING btree (benchmark_code, sector, asof_date);


--
-- Name: idx_cluster_positions_cluster; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_cluster_positions_cluster ON public.correlation_cluster_positions USING btree (cluster_id);


--
-- Name: idx_cluster_positions_position; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_cluster_positions_position ON public.correlation_cluster_positions USING btree (position_id);


--
-- Name: idx_correlation_calculations_portfolio_date; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_correlation_calculations_portfolio_date ON public.correlation_calculations USING btree (portfolio_id, calculation_date);


--
-- Name: idx_correlation_clusters_calculation; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_correlation_clusters_calculation ON public.correlation_clusters USING btree (correlation_calculation_id);


--
-- Name: idx_factor_correlations_date; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_factor_correlations_date ON public.factor_correlations USING btree (calculation_date);


--
-- Name: idx_factor_correlations_factors; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_factor_correlations_factors ON public.factor_correlations USING btree (factor_1_id, factor_2_id);


--
-- Name: idx_ir_betas_portfolio_date; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_ir_betas_portfolio_date ON public.position_interest_rate_betas USING btree (portfolio_id, calculation_date);


--
-- Name: idx_ir_betas_position_date; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_ir_betas_position_date ON public.position_interest_rate_betas USING btree (position_id, calculation_date);


--
-- Name: idx_market_risk_portfolio_date; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_market_risk_portfolio_date ON public.market_risk_scenarios USING btree (portfolio_id, calculation_date);


--
-- Name: idx_market_risk_scenario_type; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_market_risk_scenario_type ON public.market_risk_scenarios USING btree (scenario_type);


--
-- Name: idx_pairwise_correlations_calculation; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_pairwise_correlations_calculation ON public.pairwise_correlations USING btree (correlation_calculation_id);


--
-- Name: idx_pairwise_correlations_calculation_symbols; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_pairwise_correlations_calculation_symbols ON public.pairwise_correlations USING btree (correlation_calculation_id, symbol_1, symbol_2);


--
-- Name: idx_pfe_calculation_date; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_pfe_calculation_date ON public.position_factor_exposures USING btree (calculation_date);


--
-- Name: idx_pfe_factor_date; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_pfe_factor_date ON public.position_factor_exposures USING btree (factor_id, calculation_date);


--
-- Name: idx_pfe_position_date; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_pfe_position_date ON public.position_factor_exposures USING btree (position_id, calculation_date);


--
-- Name: idx_pos_beta_created; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_pos_beta_created ON public.position_market_betas USING btree (created_at);


--
-- Name: idx_pos_beta_lookup; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_pos_beta_lookup ON public.position_market_betas USING btree (portfolio_id, calc_date);


--
-- Name: idx_pos_beta_position; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_pos_beta_position ON public.position_market_betas USING btree (position_id, calc_date);


--
-- Name: idx_stress_results_calculation_date; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_stress_results_calculation_date ON public.stress_test_results USING btree (calculation_date);


--
-- Name: idx_stress_results_portfolio_date; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_stress_results_portfolio_date ON public.stress_test_results USING btree (portfolio_id, calculation_date);


--
-- Name: idx_stress_results_scenario; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_stress_results_scenario ON public.stress_test_results USING btree (scenario_id);


--
-- Name: idx_stress_scenarios_active; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_stress_scenarios_active ON public.stress_test_scenarios USING btree (active);


--
-- Name: idx_stress_scenarios_category; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_stress_scenarios_category ON public.stress_test_scenarios USING btree (category);


--
-- Name: idx_stress_scenarios_severity; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX idx_stress_scenarios_severity ON public.stress_test_scenarios USING btree (severity);


--
-- Name: ix_ai_insight_templates_insight_type; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_ai_insight_templates_insight_type ON public.ai_insight_templates USING btree (insight_type);


--
-- Name: ix_ai_insights_cache_key; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_ai_insights_cache_key ON public.ai_insights USING btree (cache_key);


--
-- Name: ix_ai_insights_cache_lookup; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_ai_insights_cache_lookup ON public.ai_insights USING btree (cache_key, created_at);


--
-- Name: ix_ai_insights_created_at; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_ai_insights_created_at ON public.ai_insights USING btree (created_at);


--
-- Name: ix_ai_insights_insight_type; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_ai_insights_insight_type ON public.ai_insights USING btree (insight_type);


--
-- Name: ix_ai_insights_portfolio_created; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_ai_insights_portfolio_created ON public.ai_insights USING btree (portfolio_id, created_at);


--
-- Name: ix_ai_insights_portfolio_id; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_ai_insights_portfolio_id ON public.ai_insights USING btree (portfolio_id);


--
-- Name: ix_ai_insights_type_severity; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_ai_insights_type_severity ON public.ai_insights USING btree (insight_type, severity);


--
-- Name: ix_ai_templates_type_active; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_ai_templates_type_active ON public.ai_insight_templates USING btree (insight_type, active);


--
-- Name: ix_ai_templates_version; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_ai_templates_version ON public.ai_insight_templates USING btree (insight_type, version);


--
-- Name: ix_batch_job_schedules_is_active; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_batch_job_schedules_is_active ON public.batch_job_schedules USING btree (is_active);


--
-- Name: ix_batch_job_schedules_next_run_at; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_batch_job_schedules_next_run_at ON public.batch_job_schedules USING btree (next_run_at);


--
-- Name: ix_batch_jobs_job_type; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_batch_jobs_job_type ON public.batch_jobs USING btree (job_type);


--
-- Name: ix_batch_jobs_started_at; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_batch_jobs_started_at ON public.batch_jobs USING btree (started_at);


--
-- Name: ix_batch_jobs_status; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_batch_jobs_status ON public.batch_jobs USING btree (status);


--
-- Name: ix_company_profiles_symbol; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_company_profiles_symbol ON public.company_profiles USING btree (symbol);


--
-- Name: ix_export_history_user_id; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_export_history_user_id ON public.export_history USING btree (user_id);


--
-- Name: ix_factor_exposures_calculation_date; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_factor_exposures_calculation_date ON public.factor_exposures USING btree (calculation_date);


--
-- Name: ix_factor_exposures_portfolio_id_factor_id; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_factor_exposures_portfolio_id_factor_id ON public.factor_exposures USING btree (portfolio_id, factor_id);


--
-- Name: ix_fund_holdings_data_source; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_fund_holdings_data_source ON public.fund_holdings USING btree (data_source);


--
-- Name: ix_fund_holdings_fund_date; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_fund_holdings_fund_date ON public.fund_holdings USING btree (fund_symbol, last_updated);


--
-- Name: ix_fund_holdings_fund_symbol; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_fund_holdings_fund_symbol ON public.fund_holdings USING btree (fund_symbol);


--
-- Name: ix_fund_holdings_holding_symbol; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_fund_holdings_holding_symbol ON public.fund_holdings USING btree (holding_symbol);


--
-- Name: ix_fund_holdings_last_updated; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_fund_holdings_last_updated ON public.fund_holdings USING btree (last_updated);


--
-- Name: ix_market_data_cache_date; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_market_data_cache_date ON public.market_data_cache USING btree (date);


--
-- Name: ix_market_data_cache_symbol; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_market_data_cache_symbol ON public.market_data_cache USING btree (symbol);


--
-- Name: ix_modeling_session_snapshots_session_id; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE UNIQUE INDEX ix_modeling_session_snapshots_session_id ON public.modeling_session_snapshots USING btree (session_id);


--
-- Name: ix_portfolio_snapshots_portfolio_id; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_portfolio_snapshots_portfolio_id ON public.portfolio_snapshots USING btree (portfolio_id);


--
-- Name: ix_portfolio_snapshots_snapshot_date; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_portfolio_snapshots_snapshot_date ON public.portfolio_snapshots USING btree (snapshot_date);


--
-- Name: ix_portfolios_deleted_at; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_portfolios_deleted_at ON public.portfolios USING btree (deleted_at);


--
-- Name: ix_position_greeks_calculation_date; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_position_greeks_calculation_date ON public.position_greeks USING btree (calculation_date);


--
-- Name: ix_position_greeks_position_id; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_position_greeks_position_id ON public.position_greeks USING btree (position_id);


--
-- Name: ix_position_tags_assigned_at; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_position_tags_assigned_at ON public.position_tags USING btree (assigned_at);


--
-- Name: ix_position_tags_position_id; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_position_tags_position_id ON public.position_tags USING btree (position_id);


--
-- Name: ix_position_tags_tag_id; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_position_tags_tag_id ON public.position_tags USING btree (tag_id);


--
-- Name: ix_position_volatility_calculation_date; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_position_volatility_calculation_date ON public.position_volatility USING btree (calculation_date);


--
-- Name: ix_position_volatility_lookup; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_position_volatility_lookup ON public.position_volatility USING btree (position_id, calculation_date);


--
-- Name: ix_position_volatility_position_id; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_position_volatility_position_id ON public.position_volatility USING btree (position_id);


--
-- Name: ix_positions_deleted_at; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_positions_deleted_at ON public.positions USING btree (deleted_at);


--
-- Name: ix_positions_exit_date; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_positions_exit_date ON public.positions USING btree (exit_date);


--
-- Name: ix_positions_inv_class_subtype; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_positions_inv_class_subtype ON public.positions USING btree (investment_class, investment_subtype);


--
-- Name: ix_positions_investment_class; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_positions_investment_class ON public.positions USING btree (investment_class);


--
-- Name: ix_positions_portfolio_id; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_positions_portfolio_id ON public.positions USING btree (portfolio_id);


--
-- Name: ix_positions_symbol; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_positions_symbol ON public.positions USING btree (symbol);


--
-- Name: ix_target_prices_portfolio_id; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_target_prices_portfolio_id ON public.portfolio_target_prices USING btree (portfolio_id);


--
-- Name: ix_target_prices_position_id; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_target_prices_position_id ON public.portfolio_target_prices USING btree (position_id);


--
-- Name: ix_target_prices_symbol; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_target_prices_symbol ON public.portfolio_target_prices USING btree (symbol);


--
-- Name: ix_target_prices_updated_at; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE INDEX ix_target_prices_updated_at ON public.portfolio_target_prices USING btree (updated_at);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: sigmasight
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: agent_messages fk_agent_messages_conversation_id_agent_conversations; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.agent_messages
    ADD CONSTRAINT fk_agent_messages_conversation_id_agent_conversations FOREIGN KEY (conversation_id) REFERENCES public.agent_conversations(id) ON DELETE CASCADE;


--
-- Name: ai_insights fk_ai_insights_cache_source_id_ai_insights; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.ai_insights
    ADD CONSTRAINT fk_ai_insights_cache_source_id_ai_insights FOREIGN KEY (cache_source_id) REFERENCES public.ai_insights(id);


--
-- Name: ai_insights fk_ai_insights_portfolio_id_portfolios; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.ai_insights
    ADD CONSTRAINT fk_ai_insights_portfolio_id_portfolios FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id);


--
-- Name: correlation_calculations fk_correlation_calculations_portfolio_id_portfolios; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.correlation_calculations
    ADD CONSTRAINT fk_correlation_calculations_portfolio_id_portfolios FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id);


--
-- Name: correlation_cluster_positions fk_correlation_cluster_positions_cluster_id_correlation_1482; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.correlation_cluster_positions
    ADD CONSTRAINT fk_correlation_cluster_positions_cluster_id_correlation_1482 FOREIGN KEY (cluster_id) REFERENCES public.correlation_clusters(id);


--
-- Name: correlation_cluster_positions fk_correlation_cluster_positions_position_id_positions; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.correlation_cluster_positions
    ADD CONSTRAINT fk_correlation_cluster_positions_position_id_positions FOREIGN KEY (position_id) REFERENCES public.positions(id);


--
-- Name: correlation_clusters fk_correlation_clusters_correlation_calculation_id_corr_40a6; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.correlation_clusters
    ADD CONSTRAINT fk_correlation_clusters_correlation_calculation_id_corr_40a6 FOREIGN KEY (correlation_calculation_id) REFERENCES public.correlation_calculations(id);


--
-- Name: export_history fk_export_history_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.export_history
    ADD CONSTRAINT fk_export_history_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: factor_correlations fk_factor_correlations_factor_1_id_factor_definitions; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.factor_correlations
    ADD CONSTRAINT fk_factor_correlations_factor_1_id_factor_definitions FOREIGN KEY (factor_1_id) REFERENCES public.factor_definitions(id);


--
-- Name: factor_correlations fk_factor_correlations_factor_2_id_factor_definitions; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.factor_correlations
    ADD CONSTRAINT fk_factor_correlations_factor_2_id_factor_definitions FOREIGN KEY (factor_2_id) REFERENCES public.factor_definitions(id);


--
-- Name: factor_exposures fk_factor_exposures_factor_id_factor_definitions; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.factor_exposures
    ADD CONSTRAINT fk_factor_exposures_factor_id_factor_definitions FOREIGN KEY (factor_id) REFERENCES public.factor_definitions(id);


--
-- Name: factor_exposures fk_factor_exposures_portfolio_id_portfolios; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.factor_exposures
    ADD CONSTRAINT fk_factor_exposures_portfolio_id_portfolios FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id);


--
-- Name: market_risk_scenarios fk_market_risk_scenarios_portfolio_id_portfolios; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.market_risk_scenarios
    ADD CONSTRAINT fk_market_risk_scenarios_portfolio_id_portfolios FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id);


--
-- Name: modeling_session_snapshots fk_modeling_session_snapshots_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.modeling_session_snapshots
    ADD CONSTRAINT fk_modeling_session_snapshots_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: pairwise_correlations fk_pairwise_correlations_correlation_calculation_id_cor_fe6e; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.pairwise_correlations
    ADD CONSTRAINT fk_pairwise_correlations_correlation_calculation_id_cor_fe6e FOREIGN KEY (correlation_calculation_id) REFERENCES public.correlation_calculations(id);


--
-- Name: portfolio_snapshots fk_portfolio_snapshots_portfolio_id_portfolios; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.portfolio_snapshots
    ADD CONSTRAINT fk_portfolio_snapshots_portfolio_id_portfolios FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id);


--
-- Name: portfolio_target_prices fk_portfolio_target_prices_created_by_users; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.portfolio_target_prices
    ADD CONSTRAINT fk_portfolio_target_prices_created_by_users FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: portfolio_target_prices fk_portfolio_target_prices_portfolio_id_portfolios; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.portfolio_target_prices
    ADD CONSTRAINT fk_portfolio_target_prices_portfolio_id_portfolios FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id) ON DELETE CASCADE;


--
-- Name: portfolio_target_prices fk_portfolio_target_prices_position_id_positions; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.portfolio_target_prices
    ADD CONSTRAINT fk_portfolio_target_prices_position_id_positions FOREIGN KEY (position_id) REFERENCES public.positions(id) ON DELETE CASCADE;


--
-- Name: portfolios fk_portfolios_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.portfolios
    ADD CONSTRAINT fk_portfolios_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: position_factor_exposures fk_position_factor_exposures_factor_id_factor_definitions; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_factor_exposures
    ADD CONSTRAINT fk_position_factor_exposures_factor_id_factor_definitions FOREIGN KEY (factor_id) REFERENCES public.factor_definitions(id);


--
-- Name: position_factor_exposures fk_position_factor_exposures_position_id_positions; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_factor_exposures
    ADD CONSTRAINT fk_position_factor_exposures_position_id_positions FOREIGN KEY (position_id) REFERENCES public.positions(id);


--
-- Name: position_greeks fk_position_greeks_position_id_positions; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_greeks
    ADD CONSTRAINT fk_position_greeks_position_id_positions FOREIGN KEY (position_id) REFERENCES public.positions(id);


--
-- Name: position_interest_rate_betas fk_position_interest_rate_betas_portfolio_id_portfolios; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_interest_rate_betas
    ADD CONSTRAINT fk_position_interest_rate_betas_portfolio_id_portfolios FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id);


--
-- Name: position_interest_rate_betas fk_position_interest_rate_betas_position_id_positions; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_interest_rate_betas
    ADD CONSTRAINT fk_position_interest_rate_betas_position_id_positions FOREIGN KEY (position_id) REFERENCES public.positions(id);


--
-- Name: position_market_betas fk_position_market_betas_portfolio_id_portfolios; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_market_betas
    ADD CONSTRAINT fk_position_market_betas_portfolio_id_portfolios FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id);


--
-- Name: position_market_betas fk_position_market_betas_position_id_positions; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_market_betas
    ADD CONSTRAINT fk_position_market_betas_position_id_positions FOREIGN KEY (position_id) REFERENCES public.positions(id);


--
-- Name: position_tags fk_position_tags_assigned_by_users; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_tags
    ADD CONSTRAINT fk_position_tags_assigned_by_users FOREIGN KEY (assigned_by) REFERENCES public.users(id);


--
-- Name: position_tags fk_position_tags_position_id_positions; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_tags
    ADD CONSTRAINT fk_position_tags_position_id_positions FOREIGN KEY (position_id) REFERENCES public.positions(id) ON DELETE CASCADE;


--
-- Name: position_tags fk_position_tags_tag_id_tags_v2; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_tags
    ADD CONSTRAINT fk_position_tags_tag_id_tags_v2 FOREIGN KEY (tag_id) REFERENCES public.tags_v2(id) ON DELETE CASCADE;


--
-- Name: position_volatility fk_position_volatility_position_id_positions; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.position_volatility
    ADD CONSTRAINT fk_position_volatility_position_id_positions FOREIGN KEY (position_id) REFERENCES public.positions(id);


--
-- Name: positions fk_positions_portfolio_id_portfolios; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.positions
    ADD CONSTRAINT fk_positions_portfolio_id_portfolios FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id);


--
-- Name: stress_test_results fk_stress_test_results_portfolio_id_portfolios; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.stress_test_results
    ADD CONSTRAINT fk_stress_test_results_portfolio_id_portfolios FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id);


--
-- Name: stress_test_results fk_stress_test_results_scenario_id_stress_test_scenarios; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.stress_test_results
    ADD CONSTRAINT fk_stress_test_results_scenario_id_stress_test_scenarios FOREIGN KEY (scenario_id) REFERENCES public.stress_test_scenarios(id);


--
-- Name: tags_v2 fk_tags_v2_archived_by_users; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.tags_v2
    ADD CONSTRAINT fk_tags_v2_archived_by_users FOREIGN KEY (archived_by) REFERENCES public.users(id);


--
-- Name: tags_v2 fk_tags_v2_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: sigmasight
--

ALTER TABLE ONLY public.tags_v2
    ADD CONSTRAINT fk_tags_v2_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict ymBVC8A5dfCfYbx5LNywuXgxN1dB0wkzU4yfoHIKX4rPHvtaEPFildHI6NBRiTB

