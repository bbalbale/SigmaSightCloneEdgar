/**
 * Strategy and Tag Type Definitions
 *
 * This file contains all TypeScript types for the Strategy and Tag system.
 *
 * Architecture:
 * - Strategies ARE positions (virtual positions)
 * - Every position belongs to exactly ONE strategy
 * - Tags label strategies (not individual positions)
 * - Standalone strategies: auto-created, contain 1 position
 * - Multi-leg strategies: user-created, contain 2+ positions
 */

// ============================================================================
// Strategy Types
// ============================================================================

/**
 * Strategy Types - Defines the strategy pattern
 */
export type StrategyType =
  | 'standalone'       // Single position (auto-created)
  | 'covered_call'     // Long stock + short call
  | 'protective_put'   // Long stock + long put
  | 'iron_condor'      // Bull put spread + bear call spread
  | 'straddle'         // Long call + long put (same strike)
  | 'strangle'         // Long call + long put (different strikes)
  | 'butterfly'        // Options spread (1-2-1 ratio)
  | 'pairs_trade'      // Long + short correlated positions
  | 'custom';          // User-defined multi-leg strategy

/**
 * Position data within a strategy
 */
export interface StrategyPosition {
  id: string;
  symbol: string;
  position_type: string;
  quantity: number;
  cost_basis?: number;
  current_price?: number;
  unrealized_pnl?: number;
  investment_class?: 'PUBLIC' | 'OPTIONS' | 'PRIVATE';
}

/**
 * Tag applied to a strategy
 */
export interface StrategyTag {
  id: string;
  name: string;
  color: string;
  description?: string | null;
}

/**
 * Strategy list item (used in portfolio views)
 */
export interface StrategyListItem {
  id: string;
  portfolio_id: string;
  name: string;
  strategy_type: StrategyType;
  is_synthetic: boolean;
  position_count?: number | null;
  tags?: StrategyTag[] | null;
  direction?: 'LONG' | 'SHORT' | 'LC' | 'LP' | 'SC' | 'SP' | 'NEUTRAL' | null;
  primary_investment_class?: 'PUBLIC' | 'OPTIONS' | 'PRIVATE' | null;
  created_at: string;
  updated_at: string;
}

/**
 * Full strategy details (includes positions and tags)
 */
export interface StrategyDetail {
  id: string;
  portfolio_id: string;
  name: string;
  strategy_type: StrategyType;
  is_synthetic: boolean;
  direction?: 'LONG' | 'SHORT' | 'LC' | 'LP' | 'SC' | 'SP' | 'NEUTRAL' | null;
  primary_investment_class?: 'PUBLIC' | 'OPTIONS' | 'PRIVATE' | null;
  created_at: string;
  updated_at: string;
  positions: StrategyPosition[];
  tags?: StrategyTag[];
  metrics?: StrategyMetrics;
}

/**
 * Aggregated metrics for a strategy
 */
export interface StrategyMetrics {
  total_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
  daily_return?: number;
  daily_return_percent?: number;
  // Greeks (for options strategies)
  delta?: number;
  gamma?: number;
  theta?: number;
  vega?: number;
  // Risk metrics
  position_count: number;
  max_loss?: number;
  max_profit?: number;
  break_even_prices?: number[];
}

/**
 * Strategy detection result
 */
export interface StrategyDetection {
  positions: string[];           // Position IDs that form the strategy
  strategy_type: StrategyType;   // Detected strategy type
  confidence: number;            // Detection confidence (0-1)
  name_suggestion: string;       // Suggested strategy name
}

// ============================================================================
// Strategy Request/Response Types
// ============================================================================

/**
 * Create new strategy request
 */
export interface CreateStrategyRequest {
  portfolio_id: string;
  name: string;
  strategy_type: StrategyType;
  position_ids?: string[];
}

/**
 * Update strategy request
 */
export interface UpdateStrategyRequest {
  name?: string;
  strategy_type?: StrategyType;
}

/**
 * Combine positions into strategy request
 */
export interface CombineStrategyRequest {
  portfolio_id: string;
  position_ids: string[];
  name: string;
  strategy_type: StrategyType;
}

/**
 * List strategies response
 */
export interface ListStrategiesResponse {
  strategies: StrategyListItem[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Detect strategies response
 */
export interface DetectStrategiesResponse {
  detections: StrategyDetection[];
  total_detected: number;
}

// ============================================================================
// Tag Types
// ============================================================================

/**
 * Tag item (user-scoped organizational labels)
 */
export interface TagItem {
  id: string;
  user_id: string;
  name: string;
  color: string;
  description?: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Create tag request
 */
export interface CreateTagRequest {
  name: string;
  color?: string;
  description?: string | null;
}

/**
 * Update tag request
 */
export interface UpdateTagRequest {
  name?: string;
  color?: string;
  description?: string | null;
}

/**
 * Batch tag update item
 */
export interface BatchTagUpdate {
  tag_id: string;
  name?: string;
  color?: string;
  description?: string | null;
}

/**
 * Tag with strategy count
 */
export interface TagWithCount extends TagItem {
  strategy_count: number;
}

/**
 * Default tag colors
 */
export const DEFAULT_TAG_COLORS = [
  '#EF4444', // Red
  '#F59E0B', // Orange
  '#10B981', // Green
  '#3B82F6', // Blue
  '#8B5CF6', // Purple
  '#EC4899', // Pink
  '#14B8A6', // Teal
  '#F97316', // Orange
] as const;

/**
 * Default tag names (created on first use)
 */
export const DEFAULT_TAG_NAMES = [
  'High Priority',
  'Growth',
  'Income',
  'Hedging',
  'Speculation',
  'Long Term',
  'Short Term',
  'Research',
] as const;

// ============================================================================
// Filter and Query Types
// ============================================================================

/**
 * Strategy list filter options
 */
export interface StrategyListOptions {
  portfolioId: string;
  tagIds?: string[];
  tagMode?: 'any' | 'all';
  strategyType?: StrategyType;
  includePositions?: boolean;
  includeTags?: boolean;
  limit?: number;
  offset?: number;
}

/**
 * Tag list filter options
 */
export interface TagListOptions {
  includeArchived?: boolean;
  sortBy?: 'name' | 'created_at' | 'updated_at';
  sortOrder?: 'asc' | 'desc';
}

// ============================================================================
// UI Component Props Types
// ============================================================================

/**
 * Strategy card component props
 */
export interface StrategyCardProps {
  strategy: StrategyListItem | StrategyDetail;
  children: React.ReactNode;
  tags?: StrategyTag[];
  onExpand?: () => void;
  isExpanded?: boolean;
  onEditTags?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  showAggregates?: boolean;
  className?: string;
}

/**
 * Tag selector component props
 */
export interface TagSelectorProps {
  strategyId: string;
  selectedTags: StrategyTag[];
  onTagsChange: (tags: StrategyTag[]) => void;
  className?: string;
}

/**
 * Tag manager component props
 */
export interface TagManagerProps {
  onTagCreated?: (tag: TagItem) => void;
  onTagUpdated?: (tag: TagItem) => void;
  onTagDeleted?: (tagId: string) => void;
  className?: string;
}

/**
 * Strategy list component props
 */
export interface StrategyListProps {
  portfolioId: string;
  filters?: StrategyListOptions;
  onStrategyClick?: (strategy: StrategyListItem) => void;
  className?: string;
}
