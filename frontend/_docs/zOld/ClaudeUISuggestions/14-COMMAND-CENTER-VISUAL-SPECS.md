# Command Center - Visual Design Specifications (Tailwind)

**Document Version**: 1.0
**Last Updated**: October 31, 2025
**Status**: Ready for Development

---

## Design System Overview

**Design Philosophy**: Professional, Bloomberg-inspired information density. Flat design (no gradients/shadows), high contrast, scannable typography, consistent spacing.

**Color Strategy**: Dark mode preferred for professionals, light mode available. Neutral grays, semantic colors (green/red for P&L), minimal decorative colors.

---

## Typography System

```css
/* Font Stack */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

/* Type Scale (Tailwind classes) */
--text-xs: text-xs (12px)          /* Tertiary info, labels */
--text-sm: text-sm (14px)          /* Secondary text, table cells */
--text-base: text-base (16px)      /* Body text, default */
--text-lg: text-lg (18px)          /* Section headers */
--text-xl: text-xl (20px)          /* Card labels */
--text-2xl: text-2xl (24px)        /* Hero metric values */
--text-3xl: text-3xl (30px)        /* Page titles */

/* Font Weights */
--font-normal: font-normal (400)   /* Body text */
--font-medium: font-medium (500)   /* Card labels, headers */
--font-semibold: font-semibold (600) /* Emphasis, buttons */
--font-bold: font-bold (700)       /* Hero values, important numbers */

/* Line Heights */
--leading-tight: leading-tight (1.25)   /* Numbers, compact text */
--leading-normal: leading-normal (1.5)  /* Body text */
--leading-relaxed: leading-relaxed (1.625) /* Descriptive text */
```

**Tabular Numbers**: Use `tabular-nums` for all numeric columns (ensures alignment).

---

## Color Palette

### Dark Mode (Primary)

```css
/* Backgrounds */
--bg-primary: bg-slate-950       /* #020617 - Page background */
--bg-secondary: bg-slate-900     /* #0f172a - Card background */
--bg-tertiary: bg-slate-800      /* #1e293b - Hover states */
--bg-elevated: bg-slate-900      /* Modals, overlays */

/* Borders */
--border-primary: border-slate-700   /* #334155 - Card borders */
--border-secondary: border-slate-600 /* #475569 - Dividers */

/* Text */
--text-primary: text-slate-50     /* #f8fafc - Primary text */
--text-secondary: text-slate-400  /* #94a3b8 - Secondary text */
--text-tertiary: text-slate-500   /* #64748b - Tertiary/muted */

/* Semantic Colors */
--text-positive: text-emerald-400  /* #34d399 - Gains, positive P&L */
--text-negative: text-red-400      /* #f87171 - Losses, negative P&L */
--text-warning: text-amber-400     /* #fbbf24 - Warnings, alerts */
--text-info: text-blue-400         /* #60a5fa - Informational */

/* Accents */
--accent-primary: bg-blue-600      /* #2563eb - CTAs, primary buttons */
--accent-hover: bg-blue-700        /* #1d4ed8 - Button hover */
```

### Light Mode (Secondary)

```css
/* Backgrounds */
--bg-primary: bg-white            /* #ffffff - Page background */
--bg-secondary: bg-slate-50       /* #f8fafc - Card background */
--bg-tertiary: bg-slate-100       /* #f1f5f9 - Hover states */

/* Borders */
--border-primary: border-slate-200   /* #e2e8f0 - Card borders */
--border-secondary: border-slate-300 /* #cbd5e1 - Dividers */

/* Text */
--text-primary: text-slate-900    /* #0f172a - Primary text */
--text-secondary: text-slate-600  /* #475569 - Secondary text */
--text-tertiary: text-slate-500   /* #64748b - Tertiary/muted */

/* Semantic Colors */
--text-positive: text-emerald-600  /* #059669 - Gains */
--text-negative: text-red-600      /* #dc2626 - Losses */
--text-warning: text-amber-600     /* #d97706 - Warnings */
--text-info: text-blue-600         /* #2563eb - Informational */
```

---

## Spacing System

```css
/* Consistent Spacing Scale (Tailwind) */
--space-1: 0.25rem (4px)    /* Tight spacing */
--space-2: 0.5rem (8px)     /* Small gaps */
--space-3: 0.75rem (12px)   /* Default gap */
--space-4: 1rem (16px)      /* Card padding */
--space-6: 1.5rem (24px)    /* Section spacing */
--space-8: 2rem (32px)      /* Large sections */
--space-12: 3rem (48px)     /* Page sections */

/* Component-Specific */
Card padding: p-4 (16px all sides)
Card gap: gap-6 (24px between cards)
Table cell padding: px-3 py-2 (12px horizontal, 8px vertical)
Button padding: px-4 py-2 (16px horizontal, 8px vertical)
```

---

## Component Specs

### Hero Metrics Row

**Layout**:
```tsx
<div className="grid grid-cols-6 gap-4 mb-6">
  {/* 6 equal-width columns, 16px gap between cards */}
</div>
```

**Individual Metric Card**:
```tsx
<div className="bg-slate-900 border border-slate-700 rounded-lg p-4">
  {/* Label */}
  <div className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-2">
    Equity Balance
  </div>

  {/* Primary Value */}
  <div className="text-2xl font-bold text-slate-50 tabular-nums mb-1">
    $2,847,392
  </div>

  {/* Secondary Context */}
  <div className="text-sm text-emerald-400 tabular-nums">
    +$124K MTD ↑
  </div>
</div>
```

**Tailwind Classes**:
- Container: `bg-slate-900 border border-slate-700 rounded-lg p-4`
- Label: `text-xs font-medium text-slate-400 uppercase tracking-wide mb-2`
- Value: `text-2xl font-bold text-slate-50 tabular-nums mb-1`
- Context (positive): `text-sm text-emerald-400 tabular-nums`
- Context (negative): `text-sm text-red-400 tabular-nums`
- Context (neutral): `text-sm text-slate-400 tabular-nums`

**Responsive**:
- Desktop: `grid-cols-6` (all 6 visible)
- Tablet: `grid-cols-6` (may need horizontal scroll wrapper `overflow-x-auto`)
- Mobile: `flex overflow-x-auto snap-x` (swipeable, 2 visible at a time)

---

### Holdings Table

**Table Container**:
```tsx
<div className="bg-slate-900 border border-slate-700 rounded-lg overflow-hidden">
  {/* Header */}
  <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
    <h2 className="text-lg font-semibold text-slate-50">Holdings</h2>
    <div className="flex gap-2">
      <input
        type="search"
        placeholder="Search..."
        className="px-3 py-1.5 text-sm bg-slate-800 border border-slate-600 rounded"
      />
      <button className="px-3 py-1.5 text-sm bg-slate-800 border border-slate-600 rounded hover:bg-slate-700">
        ↓ CSV
      </button>
    </div>
  </div>

  {/* Table */}
  <div className="overflow-x-auto">
    <table className="w-full text-sm">
      {/* ... */}
    </table>
  </div>
</div>
```

**Table Structure**:
```tsx
<table className="w-full text-sm">
  {/* Header Row - Sticky */}
  <thead className="bg-slate-800 sticky top-0 z-10">
    <tr>
      <th className="px-3 py-2 text-left text-xs font-medium text-slate-400 uppercase tracking-wide">
        Position
      </th>
      <th className="px-3 py-2 text-right text-xs font-medium text-slate-400 uppercase tracking-wide">
        Quantity
      </th>
      {/* ... repeat for all columns */}
    </tr>
  </thead>

  {/* Body Rows */}
  <tbody className="divide-y divide-slate-700">
    <tr className="hover:bg-slate-800 cursor-pointer transition-colors">
      {/* Position Cell */}
      <td className="px-3 py-3 font-medium text-slate-50">
        <div className="flex items-center gap-2">
          <span>NVDA</span>
          {/* Optional: SHORT badge for short positions */}
        </div>
      </td>

      {/* Quantity Cell */}
      <td className="px-3 py-3 text-right tabular-nums text-slate-300">
        1,200
      </td>

      {/* Today's Price */}
      <td className="px-3 py-3 text-right tabular-nums text-slate-300">
        $740.20
      </td>

      {/* Target Price */}
      <td className="px-3 py-3 text-right tabular-nums text-slate-300">
        $895.00
      </td>

      {/* Market Value */}
      <td className="px-3 py-3 text-right tabular-nums font-medium text-slate-50">
        $888,240
      </td>

      {/* Weight - with visual bar */}
      <td className="px-3 py-3 text-right">
        <div className="flex items-center justify-end gap-2">
          <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div className="h-full bg-blue-500" style={{ width: '31.2%' }}></div>
          </div>
          <span className="tabular-nums text-slate-300">31.2%</span>
        </div>
      </td>

      {/* P&L Today - color coded */}
      <td className="px-3 py-3 text-right tabular-nums text-emerald-400">
        +$12,240
      </td>

      {/* P&L Total - color coded */}
      <td className="px-3 py-3 text-right tabular-nums text-emerald-400">
        +$142,350
      </td>

      {/* Return % - color coded */}
      <td className="px-3 py-3 text-right tabular-nums font-medium text-emerald-400">
        +19.1%
      </td>

      {/* Target Return */}
      <td className="px-3 py-3 text-right tabular-nums font-medium text-slate-50">
        25%
      </td>

      {/* Beta */}
      <td className="px-3 py-3 text-right tabular-nums text-slate-300">
        1.85
      </td>

      {/* Actions */}
      <td className="px-3 py-3 text-right">
        <div className="flex items-center justify-end gap-2">
          <button className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded">
            AI
          </button>
          <button className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 rounded">
            •••
          </button>
        </div>
      </td>
    </tr>
  </tbody>
</table>
```

**Tailwind Classes Summary**:
- Table: `w-full text-sm`
- Header: `bg-slate-800 sticky top-0 z-10`
- Header Cell: `px-3 py-2 text-left text-xs font-medium text-slate-400 uppercase tracking-wide`
- Body Row: `hover:bg-slate-800 cursor-pointer transition-colors`
- Body Row Divider: `divide-y divide-slate-700`
- Body Cell (left-align): `px-3 py-3 text-slate-300`
- Body Cell (right-align): `px-3 py-3 text-right tabular-nums text-slate-300`
- Body Cell (emphasis): Add `font-medium text-slate-50`
- Positive P&L: `text-emerald-400`
- Negative P&L: `text-red-400`

**Column Alignment**:
- Left: Position
- Right: All numeric columns (Quantity, Prices, Value, Weight, P&L, Return, Beta)
- Right: Actions

**Sortable Headers**:
```tsx
<th className="px-3 py-2 text-right text-xs font-medium text-slate-400 uppercase tracking-wide cursor-pointer hover:text-slate-300 group">
  <div className="flex items-center justify-end gap-1">
    <span>Market Value</span>
    <svg className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity">
      {/* Sort icon */}
    </svg>
  </div>
</th>
```

---

### Risk Metrics Row

**Layout** (same as Hero Metrics):
```tsx
<div className="grid grid-cols-5 gap-4 mt-6">
  {/* 5 equal-width columns */}
</div>
```

**Individual Risk Metric Card**:
```tsx
<div className="bg-slate-900 border border-slate-700 rounded-lg p-4">
  {/* Label */}
  <div className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-2">
    Portfolio Beta
  </div>

  {/* Primary Value */}
  <div className="text-2xl font-bold text-slate-50 tabular-nums mb-1">
    1.32
  </div>

  {/* Context/Interpretation */}
  <div className="text-xs text-amber-400">
    High risk
  </div>

  {/* Optional: AI Explain Button */}
  <button className="mt-2 text-xs text-blue-400 hover:text-blue-300">
    ? Explain
  </button>
</div>
```

**Stress Test Card** (special layout - 2 lines):
```tsx
<div className="bg-slate-900 border border-slate-700 rounded-lg p-4">
  <div className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-2">
    Stress Test
  </div>

  <div className="text-sm text-slate-400 mb-1">
    ±1% Market:
  </div>

  <div className="flex items-baseline gap-2">
    <span className="text-lg font-bold text-emerald-400 tabular-nums">
      +$37.5K
    </span>
    <span className="text-slate-500">/</span>
    <span className="text-lg font-bold text-red-400 tabular-nums">
      -$39.2K
    </span>
  </div>
</div>
```

---

### AI Insight Modal

**Modal Container**:
```tsx
<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
  <div className="bg-slate-900 border border-slate-700 rounded-lg shadow-2xl w-full max-w-lg mx-4">
    {/* Header */}
    <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
      <h3 className="text-lg font-semibold text-slate-50">
        NVIDIA (NVDA) - AI Analysis
      </h3>
      <button className="text-slate-400 hover:text-slate-300">
        <svg className="w-5 h-5"><!-- X icon --></svg>
      </button>
    </div>

    {/* Content */}
    <div className="px-6 py-4 space-y-3">
      <div className="flex items-start gap-3">
        <span className="text-slate-400 mt-0.5">•</span>
        <p className="text-sm text-slate-300 leading-relaxed">
          Your largest position at 31% of portfolio
        </p>
      </div>
      {/* Repeat for 3-5 insights */}
    </div>

    {/* Footer */}
    <div className="px-6 py-4 border-t border-slate-700 flex items-center justify-end gap-3">
      <button className="px-4 py-2 text-sm bg-slate-800 hover:bg-slate-700 text-slate-300 rounded">
        Dismiss
      </button>
      <button className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded">
        View Full Analysis
      </button>
    </div>
  </div>
</div>
```

**Tailwind Classes**:
- Backdrop: `fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm`
- Modal: `bg-slate-900 border border-slate-700 rounded-lg shadow-2xl w-full max-w-lg mx-4`
- Header: `px-6 py-4 border-b border-slate-700`
- Content: `px-6 py-4 space-y-3`
- Insight Item: `flex items-start gap-3`
- Bullet: `text-slate-400`
- Insight Text: `text-sm text-slate-300 leading-relaxed`
- Footer: `px-6 py-4 border-t border-slate-700 flex items-center justify-end gap-3`
- Primary Button: `px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded`
- Secondary Button: `px-4 py-2 text-sm bg-slate-800 hover:bg-slate-700 text-slate-300 rounded`

---

### Key Findings Section (Collapsible)

**Collapsed State**:
```tsx
<div className="bg-slate-900 border border-slate-700 rounded-lg p-4 mb-6">
  <button className="w-full flex items-center justify-between hover:opacity-80 transition-opacity">
    <div className="flex items-center gap-2">
      <span className="text-lg">✨</span>
      <span className="text-sm font-medium text-slate-50">KEY FINDINGS</span>
      <span className="text-xs font-semibold text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full">
        3
      </span>
    </div>
    <svg className="w-4 h-4 text-slate-400 transition-transform">
      {/* Chevron down icon */}
    </svg>
  </button>
</div>
```

**Expanded State**:
```tsx
<div className="bg-slate-900 border border-slate-700 rounded-lg p-4 mb-6">
  <button className="w-full flex items-center justify-between hover:opacity-80 transition-opacity mb-4">
    {/* Same header as collapsed */}
  </button>

  <div className="space-y-3 pl-7">
    {/* Warning Insight */}
    <div className="flex items-start gap-3">
      <span className="text-amber-400 mt-0.5">⚠</span>
      <p className="text-sm text-slate-300 leading-relaxed">
        Tech concentration increased to 45% (from 38% last week) - consider rebalancing
      </p>
    </div>

    {/* Info Insight */}
    <div className="flex items-start gap-3">
      <span className="text-blue-400 mt-0.5">ℹ</span>
      <p className="text-sm text-slate-300 leading-relaxed">
        Portfolio beta rose from 1.18 to 1.32 - increased market sensitivity
      </p>
    </div>

    {/* Success Insight */}
    <div className="flex items-start gap-3">
      <span className="text-emerald-400 mt-0.5">✓</span>
      <p className="text-sm text-slate-300 leading-relaxed">
        8 of 12 positions are above target price - strong performance
      </p>
    </div>
  </div>
</div>
```

---

## Micro-interactions & States

### Hover States
```css
/* Card hover (if interactive) */
.hover\:bg-slate-800:hover { background-color: #1e293b; }

/* Button hover */
.hover\:bg-blue-700:hover { background-color: #1d4ed8; }

/* Table row hover */
.hover\:bg-slate-800:hover { background-color: #1e293b; }

/* Link hover */
.hover\:text-blue-300:hover { color: #93c5fd; }
```

### Focus States (Accessibility)
```css
/* Button focus */
.focus\:outline-none:focus { outline: none; }
.focus\:ring-2:focus { box-shadow: 0 0 0 2px ... }
.focus\:ring-blue-500:focus { --tw-ring-color: #3b82f6; }
.focus\:ring-offset-2:focus { --tw-ring-offset-width: 2px; }
.focus\:ring-offset-slate-900:focus { --tw-ring-offset-color: #0f172a; }
```

### Active/Selected States
```css
/* Selected table row */
.bg-blue-500\/10 { background-color: rgb(59 130 246 / 0.1); }
.border-blue-500 { border-color: #3b82f6; }

/* Active button */
.active\:scale-95:active { transform: scale(0.95); }
```

### Transitions
```css
/* Standard transition */
.transition-colors { transition-property: color, background-color, border-color; }
.duration-200 { transition-duration: 200ms; }

/* Transform transition */
.transition-transform { transition-property: transform; }

/* Opacity transition */
.transition-opacity { transition-property: opacity; }
```

---

## Responsive Breakpoints

```css
/* Mobile First Approach */
/* Default: Mobile (<768px) */

/* Tablet (≥768px) */
@media (min-width: 768px) {
  /* Example: 2-column grid */
  .md\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

/* Desktop (≥1024px) */
@media (min-width: 1024px) {
  /* Example: 6-column hero metrics */
  .lg\:grid-cols-6 { grid-template-columns: repeat(6, minmax(0, 1fr)); }
}

/* Wide (≥1440px) */
@media (min-width: 1440px) {
  /* Example: Increased spacing */
  .xl\:gap-6 { gap: 1.5rem; }
}
```

**Mobile Adaptations**:
- Hero metrics: `flex overflow-x-auto snap-x snap-mandatory` (swipeable)
- Holdings table: Replace with card view (stack vertically)
- Risk metrics: `flex flex-col gap-4` (stack vertically)

---

## Icons & Visual Elements

**Icon Library**: Lucide React (https://lucide.dev) or Heroicons

**Common Icons**:
- Sort: `ChevronUp`, `ChevronDown`, `ChevronsUpDown`
- Actions: `MoreVertical`, `Edit`, `Trash`, `Tag`
- Status: `TrendingUp`, `TrendingDown`, `AlertTriangle`, `Info`, `CheckCircle`
- Navigation: `ChevronLeft`, `ChevronRight`, `X`
- AI: `Sparkles`, `Bot`, `MessageCircle`

**Icon Sizing**:
- Small: `w-3 h-3` (12px) - Inline icons
- Medium: `w-4 h-4` (16px) - Button icons
- Large: `w-5 h-5` (20px) - Section headers
- XL: `w-6 h-6` (24px) - Feature icons

---

## Accessibility (WCAG AA)

**Color Contrast**:
- Text on dark background: White (#f8fafc) on Dark Slate (#0f172a) = 15.9:1 ✓
- Secondary text: Slate 400 (#94a3b8) on Dark Slate = 7.8:1 ✓
- Positive P&L: Emerald 400 (#34d399) on Dark Slate = 9.2:1 ✓
- Negative P&L: Red 400 (#f87171) on Dark Slate = 6.1:1 ✓

**Focus Indicators**:
- All interactive elements have visible focus ring
- Focus ring: 2px blue (#3b82f6) with 2px offset

**Keyboard Navigation**:
- Tab order: Hero metrics → Holdings table → Risk metrics → Modals
- Table navigation: Tab/Shift+Tab between rows, Arrow keys within row
- Escape: Close modals

**Screen Reader Support**:
- Semantic HTML (`<table>`, `<thead>`, `<tbody>`, `<th>`, `<td>`)
- ARIA labels on icon buttons: `aria-label="Sort by Market Value"`
- ARIA live regions for dynamic content updates

---

## Animation & Motion

**Reduce Motion** (respect user preference):
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

**Subtle Animations**:
- Table row hover: 200ms color transition
- Modal open: 150ms fade-in + scale (0.95 → 1)
- Collapsible expand: 200ms height transition
- Button press: 100ms scale (1 → 0.95)

**No Animations**:
- Page load (no splash screens, spinners minimized)
- Data updates (prefer instant updates over loading states)

---

## Loading States

**Skeleton Screens** (while data loading):
```tsx
<div className="bg-slate-900 border border-slate-700 rounded-lg p-4 animate-pulse">
  <div className="h-3 bg-slate-700 rounded w-24 mb-2"></div>
  <div className="h-8 bg-slate-700 rounded w-32 mb-1"></div>
  <div className="h-4 bg-slate-700 rounded w-20"></div>
</div>
```

**Spinner** (for actions):
```tsx
<svg className="animate-spin h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
</svg>
```

---

## Print Styles (Optional Future Enhancement)

```css
@media print {
  /* Hide interactive elements */
  .no-print { display: none; }

  /* Optimize for B&W printing */
  * { color: black !important; background: white !important; }

  /* Page breaks */
  .page-break-before { page-break-before: always; }
  .page-break-after { page-break-after: always; }
}
```

---

## Component Class Reference (Quick Copy)

**Hero Metric Card**:
```
bg-slate-900 border border-slate-700 rounded-lg p-4
  ├─ text-xs font-medium text-slate-400 uppercase tracking-wide mb-2
  ├─ text-2xl font-bold text-slate-50 tabular-nums mb-1
  └─ text-sm text-emerald-400 tabular-nums
```

**Table**:
```
w-full text-sm
  ├─ thead: bg-slate-800 sticky top-0 z-10
  │   └─ th: px-3 py-2 text-xs font-medium text-slate-400 uppercase tracking-wide
  └─ tbody: divide-y divide-slate-700
      └─ tr: hover:bg-slate-800 cursor-pointer transition-colors
          └─ td: px-3 py-3 tabular-nums text-slate-300
```

**Modal**:
```
fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm
  └─ bg-slate-900 border border-slate-700 rounded-lg shadow-2xl w-full max-w-lg mx-4
      ├─ Header: px-6 py-4 border-b border-slate-700
      ├─ Content: px-6 py-4 space-y-3
      └─ Footer: px-6 py-4 border-t border-slate-700
```

**Button (Primary)**:
```
px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded font-medium transition-colors
```

**Button (Secondary)**:
```
px-4 py-2 text-sm bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-600 transition-colors
```

---

## Summary

This design system provides:
- ✅ **Professional aesthetic** - Bloomberg-inspired, flat design, high information density
- ✅ **Consistent spacing** - 4/8/16/24px scale throughout
- ✅ **Semantic colors** - Clear meaning (green = good, red = bad, blue = action)
- ✅ **Accessible** - WCAG AA compliant, keyboard navigable, screen reader friendly
- ✅ **Responsive** - Mobile-first, adapts to all screen sizes
- ✅ **Copy-paste ready** - All Tailwind classes documented for quick implementation

**Next Steps**: Begin component development using these specs. Start with Hero Metrics Row, then Holdings Table, then Risk Metrics.
