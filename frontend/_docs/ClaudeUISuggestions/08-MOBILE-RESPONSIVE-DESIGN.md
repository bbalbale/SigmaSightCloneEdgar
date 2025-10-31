# Mobile & Responsive Design Patterns

**Document Version**: 1.0
**Last Updated**: October 30, 2025

---

## Overview

SigmaSight must be fully functional on desktop (≥1024px), tablet (768-1023px), and mobile (<768px) devices. This document specifies responsive patterns and mobile-specific optimizations.

---

## Breakpoints

```css
/* Mobile First Approach */
--mobile: 0px       /* <768px */
--tablet: 768px     /* 768-1023px */
--desktop: 1024px   /* ≥1024px */
--wide: 1440px      /* ≥1440px */
```

---

## Mobile Navigation (< 768px)

### Bottom Navigation Bar

```
┌────────────────────────────────┐
│                                │
│     Content Area               │
│     (scrollable)               │
│                                │
│                                │
├────────────────────────────────┤
│ [🏠]  [📊]  [⚠]  [✨]  [☰]   │  ← Fixed bottom
└────────────────────────────────┘
```

**Icons**:
1. 🏠 Home (Command Center)
2. 📊 Positions
3. ⚠ Risk Analytics
4. ✨ AI Copilot
5. ☰ More (Organize, Settings, etc.)

**Implementation**:
```typescript
<BottomNavigation
  items={[
    { value: 'command-center', label: 'Home', icon: <HomeIcon /> },
    { value: 'positions', label: 'Positions', icon: <ChartIcon /> },
    { value: 'risk', label: 'Risk', icon: <AlertIcon /> },
    { value: 'ai', label: 'AI', icon: <SparkleIcon />, badge: 3 },
    { value: 'more', label: 'More', icon: <MenuIcon /> }
  ]}
  activeValue="command-center"
  onChange={(value) => navigate(value)}
/>
```

**Position**: Fixed at bottom, always visible
**Height**: 56px (iOS safe area aware)
**Accessibility**: Large tap targets (44x44px minimum)

---

## Mobile Layouts

### Command Center (Mobile)

```
┌──────────────────────────────────┐
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃ Portfolio Health: 82/100   ┃ │  ← Collapsed hero
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
│                                  │
│ ← Swipeable Metrics Cards →     │
│ ┌──────────────┐                │
│ │ Net Worth    │                │
│ │ $500,000     │                │
│ │ +2.5% MTD ↑ │                │
│ └──────────────┘                │
│     ● ○ ○ ○  ← Pagination dots  │
│                                  │
│ ✨ AI Insights (3)  [Expand ▼] │  ← Collapsed by default
│                                  │
│ Sector Exposure    [Expand ▼]  │  ← Collapsed
│                                  │
│ Top Positions      [Expand ▼]  │  ← Show top 3, rest collapsed
│ 1. NVDA  $88K  +15.8%           │
│ 2. TSLA  $40K  -5.2%            │
│ 3. META  $75K  +12.8%           │
│ [View All 60 More →]            │
│                                  │
│ Recent Activity    [Expand ▼]  │  ← Collapsed
└──────────────────────────────────┘
```

**Key Changes from Desktop**:
- Single column layout (all cards stack)
- Swipeable metric cards (horizontal scroll)
- Sections collapsed by default (tap to expand)
- Only top 3 positions shown, "View All" button
- Smaller fonts, compact spacing

---

### Positions (Mobile)

```
┌──────────────────────────────────┐
│ [All][Long][Short][Options][…]  │  ← Scrollable tabs
│                                  │
│ [🔍 Search]  [Filters ▼]        │
│                                  │
│ 63 positions  •  +$24.5K (+5.1%)│  ← Summary bar
│                                  │
│ ┌────────────────────────────┐  │
│ │ NVDA  •  $88,000           │  │  ← Compact card
│ │ +$12,000 (+15.8%) 🟢      │  │
│ │ [Actions ▾]                │  │  ← Collapsed menu
│ └────────────────────────────┘  │
│                                  │
│ ┌────────────────────────────┐  │
│ │ TSLA  •  $40,000  SHORT    │  │
│ │ -$2,100 (-5.2%) 🔴        │  │
│ │ [Actions ▾]                │  │
│ └────────────────────────────┘  │
│                                  │
│ ... (scroll for more)            │
└──────────────────────────────────┘
```

**Mobile-Specific Features**:
- Compact position cards (less detail, tap to expand)
- Filters in bottom sheet modal (not inline dropdowns)
- Swipe left on card → Quick actions (Tag, Delete, etc.)
- Infinite scroll (not pagination)

---

## Mobile Interaction Patterns

### 1. Bottom Sheets

**Use Case**: Modals, filters, position details

```
┌──────────────────────────────────┐
│ Positions List                   │  ← Dimmed background
│ ...                              │
├══════════════════════════════════┤
│ [─]  NVDA Position Details       │  ← Bottom sheet
│ ─────────────────────────────    │
│ Market Value: $88,000            │
│ P&L: +$12,000 (+15.8%)          │
│ Beta: 1.85  Volatility: 32%     │
│ [Analyze Risk] [AI Explain]      │
└──────────────────────────────────┘
```

**Behavior**:
- Slides up from bottom (not full-screen modal)
- Drag handle at top for dismissing
- Swipe down to close
- Backdrop dimmed, tap to close

---

### 2. Swipe Gestures

**Horizontal Swipe** (Metric Cards):
```
← Swipe Left/Right →

[Net Worth] → [Net Exposure] → [Gross] → [P&L]
```

**Swipe Actions** (Position Cards):
```
← Swipe Left on position card

┌────────────────────────────────┐
│ NVDA  $88K  +15.8%             │ ← Swipe left
│                 [Tag] [Delete] │ ← Actions revealed
└────────────────────────────────┘
```

---

### 3. Pull-to-Refresh

**Standard Mobile Pattern**:
```
Pull down from top → Spinner appears → Refresh data
```

**Implementation**:
```typescript
<PullToRefresh onRefresh={async () => await refetchData()}>
  <CommandCenterContent />
</PullToRefresh>
```

---

### 4. Sticky Headers

**Keep key info visible while scrolling**:

```
┌──────────────────────────────────┐
│ Portfolio: $500K  +$12.5K  [AI] │  ← Sticky header
├──────────────────────────────────┤
│                                  │
│     (Scrollable content)         │
│                                  │
│     ...                          │
└──────────────────────────────────┘
```

---

## Tablet Layouts (768-1023px)

### 2-Column Layouts

**Command Center (Tablet)**:
```
┌────────────────────┬───────────────────┐
│ Portfolio Health   │ AI Insights       │
│ ────────────────── │ ─────────────     │
│ Score: 82/100      │ ⚠ Tech conc...    │
│ ...                │ ℹ Volatility...   │
├────────────────────┼───────────────────┤
│ Sector Exposure    │ Factor Exposures  │
│ ────────────────── │ ─────────────     │
│ Tech: 45% +15%     │ Growth: +2.1σ     │
│ ...                │ ...               │
└────────────────────┴───────────────────┘
```

**2-column grid**: 50/50 or 60/40 splits
**Collapsible sections**: Still available, but more expanded by default

---

### Split View (iPad Landscape)

**Positions + Details Side Panel**:
```
┌──────────────────────┬────────────────────────┐
│ Positions List       │ NVDA Details           │
│ ──────────────────── │ ──────────────────     │
│ [NVDA]  ─────→       │ Market Value: $88K     │
│  TSLA                │ P&L: +$12K (+15.8%)    │
│  META                │ Beta: 1.85             │
│  ...                 │ Factor Exposures:      │
│                      │ • Growth: +2.3σ        │
│                      │ • Momentum: +1.8σ      │
│                      │ [Full Analysis →]      │
└──────────────────────┴────────────────────────┘
```

**Interaction**: Click position → Side panel opens, doesn't navigate away

---

## Responsive Components

### MetricCard (Responsive)

**Desktop**:
```
┌────────────────────┐
│ NET WORTH          │
│ $500,000           │
│ +$12,500 (+2.5%) ↑│
│ +$38,200 (+8.2%) ↑│  ← YTD shown
│ [Sparkline chart]  │
└────────────────────┘
```

**Mobile**:
```
┌──────────────┐
│ Net Worth    │
│ $500K        │
│ +2.5% MTD ↑ │  ← Only MTD, YTD hidden
└──────────────┘
```

**Implementation**:
```typescript
<MetricCard
  title="Net Worth"
  value={500000}
  change={{ amount: 12500, percentage: 2.5, period: 'MTD' }}
  ytdChange={{ amount: 38200, percentage: 8.2 }}  // Hidden on mobile
  sparkline={dailyValues}  // Hidden on mobile
  responsive={{
    mobile: { hideYTD: true, hideSparkline: true },
    tablet: { hideYTD: false, hideSparkline: true },
    desktop: { hideYTD: false, hideSparkline: false }
  }}
/>
```

---

### PositionCard (Responsive)

**Desktop**: Expanded with all details
**Tablet**: Medium detail (some fields hidden)
**Mobile**: Compact (symbol, value, P&L only, tap to expand)

---

## Touch Optimization

### Tap Targets

**Minimum Size**: 44x44px (Apple HIG, WCAG AAA)

**Examples**:
- Buttons: 48px height minimum
- Nav items: 56px height
- List items: 64px height
- Icons: 24x24px with 44x44px tap area

### Spacing

**Mobile-specific spacing**:
- Increased padding for touch: 16px minimum
- Gaps between tappable elements: 8px minimum
- Edge margins: 16px (not flush to screen edges)

---

## Performance Optimization

### Mobile-Specific

**Lazy Loading**:
- Load above-the-fold content first
- Lazy load images, charts below fold
- Infinite scroll for long lists (positions, activity feed)

**Reduced Motion**:
- Respect `prefers-reduced-motion` media query
- Disable animations for users who prefer less motion

**Image Optimization**:
- Serve smaller images on mobile (lower resolution)
- Use `<picture>` with responsive srcset

**Code Splitting**:
- Load mobile components separately from desktop
- Dynamic imports for heavy features (charts, modals)

---

## Accessibility

**Mobile Accessibility**:
- VoiceOver (iOS) and TalkBack (Android) support
- Screen reader announcements for state changes
- Keyboard navigation (Bluetooth keyboards on tablets)
- High contrast mode support

**Touch Accessibility**:
- Haptic feedback for actions (button press, swipe)
- Large font sizes (respect iOS/Android text size settings)
- Color blind friendly (don't rely solely on color)

---

## Testing Checklist

**Devices to Test**:
- ✅ iPhone 14/15 (Mobile Safari)
- ✅ iPad Pro (Safari, landscape + portrait)
- ✅ Samsung Galaxy S23 (Chrome)
- ✅ Android Tablet (Chrome)

**Browsers**:
- ✅ Safari (iOS/macOS)
- ✅ Chrome (Android/Desktop)
- ✅ Firefox (Desktop)
- ✅ Edge (Desktop)

**Orientation**:
- ✅ Portrait (primary for mobile)
- ✅ Landscape (tablets, some mobile use)

**Network Conditions**:
- ✅ 4G (good connection)
- ✅ 3G (slower connection)
- ✅ Offline (graceful degradation)

---

## Mobile-First CSS Example

```css
/* Mobile First (Default) */
.metric-card {
  width: 100%;
  padding: 16px;
  font-size: 14px;
}

.metric-card__ytd {
  display: none;  /* Hidden on mobile */
}

.metric-card__sparkline {
  display: none;  /* Hidden on mobile */
}

/* Tablet (≥768px) */
@media (min-width: 768px) {
  .metric-card {
    width: 50%;  /* 2-column grid */
    padding: 24px;
    font-size: 16px;
  }

  .metric-card__ytd {
    display: block;  /* Show YTD on tablet */
  }
}

/* Desktop (≥1024px) */
@media (min-width: 1024px) {
  .metric-card {
    width: 25%;  /* 4-column grid */
    padding: 32px;
  }

  .metric-card__sparkline {
    display: block;  /* Show sparkline on desktop */
  }
}
```

---

## Summary

**Mobile Strategy**: Full functionality, optimized UX
- Bottom navigation for primary actions
- Swipeable cards, pull-to-refresh, bottom sheets
- Collapsed sections by default, expand on tap
- Large tap targets, touch-optimized spacing

**Tablet Strategy**: Hybrid (desktop features, mobile patterns)
- 2-column layouts, split views
- Some mobile patterns (bottom sheets, swipe gestures)
- More expanded by default than mobile

**Desktop Strategy**: Maximum information density
- Multi-column layouts, side panels, inline modals
- All features visible, minimal collapsing
- Keyboard shortcuts, hover states

**Next**: See `09-IMPLEMENTATION-ROADMAP.md` for week-by-week execution plan.
