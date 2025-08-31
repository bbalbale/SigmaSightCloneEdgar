# Portfolio Analysis Dashboard - Comprehensive Design Breakdown

## MISSION OVERVIEW
Create a 95% replica of a modern portfolio analysis dashboard with comprehensive financial visualization while maintaining the existing chat bar functionality.

## CURRENT STATE ANALYSIS
- ✅ Header with SigmaSight branding and navigation
- ✅ Chat input bar centered with financial risk questions
- ✅ 5 exposure cards: Long, Short, Gross, Net Exposure, Total P&L
- ❌ Missing comprehensive dashboard sections below the cards

## ENHANCED DASHBOARD REQUIREMENTS

### 1. PORTFOLIO OVERVIEW SECTION (Top Priority)
**Layout**: 2x2 grid below existing exposure cards
- **Portfolio Value Chart**: Line chart showing portfolio value over time (30d, 90d, 1Y views)
- **Asset Allocation Pie Chart**: Breakdown by asset class (Stocks, Bonds, Options, Cash)
- **Geographic Allocation**: World map or bar chart by regions
- **Sector Allocation**: Donut chart by GICS sectors

### 2. PERFORMANCE ANALYTICS SECTION
**Layout**: Full-width dashboard with tabs
- **Performance Metrics Table**: Sharpe ratio, Sortino ratio, Max drawdown, Beta
- **Risk Metrics Chart**: VaR (Value at Risk) trends over time
- **Benchmark Comparison**: Line chart comparing portfolio vs S&P 500, custom benchmarks
- **Volatility Analysis**: Rolling volatility chart with customizable periods

### 3. POSITIONS AND HOLDINGS SECTION
**Layout**: Data table with advanced filtering
- **Top Positions Table**: Symbol, Quantity, Market Value, % of Portfolio, Unrealized P&L
- **Recent Transactions**: Buy/Sell history with pagination
- **Position Details**: Expandable rows showing Greeks, DTE, Delta hedging status
- **Correlation Matrix**: Heatmap of position correlations

### 4. RISK ANALYSIS DASHBOARD
**Layout**: Interactive risk visualization
- **Factor Exposure Chart**: Bar chart showing factor loadings (Value, Growth, Size, etc)
- **Risk Contribution**: Treemap showing which positions contribute most to portfolio risk
- **Scenario Analysis**: Stress test results in different market conditions
- **Greeks Summary**: Total Delta, Gamma, Theta, Vega with visual indicators

### 5. MARKET DATA AND NEWS SECTION
**Layout**: Side-by-side widgets
- **Market Movers**: Top gainers/losers affecting portfolio positions
- **Economic Calendar**: Upcoming events that may impact positions
- **News Feed**: Relevant financial news filtered by portfolio holdings
- **Market Indices Widget**: Real-time S&P 500, NASDAQ, VIX values

## DESIGN SYSTEM SPECIFICATIONS

### Color Scheme (Modern Financial Dashboard)
- **Primary**: Deep blue (#1e40af) for key metrics and actions
- **Success**: Green (#16a34a) for positive P&L and gains
- **Danger**: Red (#dc2626) for losses and high risk
- **Warning**: Orange (#ea580c) for alerts and moderate risk
- **Neutral**: Gray scale (#6b7280, #9ca3af, #d1d5db) for secondary data
- **Background**: Light gray (#f9fafb) with white cards

### Typography
- **Headers**: Inter/System font, font-semibold, text-lg to text-2xl
- **Metrics**: Tabular numbers, font-bold, text-xl to text-3xl
- **Labels**: font-medium, text-sm, text-muted-foreground
- **Body**: Regular weight, text-sm to text-base

### Component Specifications

#### Enhanced Exposure Cards
- **Larger Size**: Increase padding and metric font size
- **Trend Indicators**: Add small sparkline charts or trend arrows
- **Color Coding**: Green for positive, red for negative values
- **Hover Effects**: Subtle shadow and scale on hover

#### Chart Components
- **Library**: Recharts for React integration
- **Responsive**: All charts must work on mobile and desktop
- **Interactive**: Tooltips, zoom, and hover states
- **Time Selectors**: 1D, 7D, 30D, 90D, 1Y buttons

#### Data Tables
- **Sorting**: All columns sortable
- **Filtering**: Search and filter capabilities
- **Pagination**: Show 10/25/50 rows options
- **Export**: CSV/Excel export functionality

### Layout Architecture

```
┌─────────────────────────────────────────────────────┐
│ Header (SigmaSight + Navigation)                    │
├─────────────────────────────────────────────────────┤
│ Chat Input Bar (PRESERVE)                          │
├─────────────────────────────────────────────────────┤
│ Exposure Cards Row (5 cards) - ENHANCE             │
├─────────────────────────────────────────────────────┤
│ Portfolio Overview Section (2x2 chart grid)        │
├─────────────────────────────────────────────────────┤
│ Performance Analytics (Tabbed interface)           │
├─────────────────────────────────────────────────────┤
│ Positions & Holdings (Data table + details)        │
├─────────────────────────────────────────────────────┤
│ Risk Analysis Dashboard (Interactive charts)       │
├─────────────────────────────────────────────────────┤
│ Market Data & News (Side-by-side widgets)         │
└─────────────────────────────────────────────────────┘
```

## RESPONSIVE DESIGN REQUIREMENTS

### Desktop (≥1024px)
- Full layout as described above
- 5 cards in a row for exposure metrics
- 2x2 grid for portfolio overview charts
- Side-by-side layout for market data section

### Tablet (768px - 1023px)
- 3 + 2 cards layout for exposure metrics
- 2x1 grid for portfolio overview, stack remaining charts
- Tabbed interface becomes scrollable
- Tables get horizontal scroll

### Mobile (<768px)
- Stack all exposure cards vertically
- All charts stack vertically
- Data tables become cards with key metrics
- Condensed navigation with hamburger menu

## SHADCN/UI COMPONENTS TO USE

### Core Components
- `Card`, `CardContent`, `CardHeader`, `CardTitle` - For all sections
- `Button` - For filters, actions, time selectors
- `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableCell` - Data tables
- `Tabs`, `TabsContent`, `TabsList`, `TabsTrigger` - Performance analytics
- `Badge` - For status indicators and labels
- `Dialog` - For position details and modals

### Data Visualization
- **Recharts Integration**: LineChart, BarChart, PieChart, AreaChart
- **Custom Components**: Correlation heatmap, Risk treemap, Factor exposure chart
- **Interactive Elements**: Tooltips, legends, zoom controls

## PLACEHOLDER DATA STRATEGY

### Mock Data Types
```typescript
interface PortfolioData {
  totalValue: number
  dailyChange: number
  percentageChange: number
  positions: Position[]
  performanceHistory: PerformancePoint[]
  riskMetrics: RiskMetrics
  factorExposure: FactorExposure[]
}
```

### Realistic Sample Data
- **Portfolio Value**: $2.5M - $15M range
- **Positions**: 15-50 holdings across asset classes
- **Historical Data**: 252 trading days (1 year)
- **Performance**: 8-15% annual return with realistic volatility
- **Sectors**: Technology, Healthcare, Financial, Energy, Consumer

## API INTEGRATION READINESS

### Component Structure
- Each chart/table component accepts props for data and loading states
- Error boundaries for API failures
- Loading skeletons for all components
- Graceful degradation when data is unavailable

### State Management
- Use React hooks for component-level state
- Prepare for data fetching with useEffect patterns
- Error handling and retry mechanisms
- Caching strategy for expensive calculations

This comprehensive design serves as the blueprint for creating a modern, professional portfolio analysis dashboard that matches industry standards while maintaining our existing chat functionality.