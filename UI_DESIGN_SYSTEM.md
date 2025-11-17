# SigmaSight UI Design System

> **Last Updated**: 2025-11-17
> **Version**: 1.0
> **Purpose**: Complete UI design system reference for replicating SigmaSight's visual design in other applications

---

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [Typography](#typography)
3. [Color System](#color-system)
4. [Spacing & Layout](#spacing--layout)
5. [Components](#components)
6. [Dark Mode](#dark-mode)
7. [Responsive Design](#responsive-design)
8. [Common Patterns](#common-patterns)

---

## Design Philosophy

SigmaSight uses a **clean, professional financial interface** with:
- **Modern minimalism**: Clean lines, ample whitespace, subtle shadows
- **Data-first design**: Metrics and numbers take visual priority
- **Professional color palette**: Neutral grays with strategic use of green/red for financial data
- **Mobile-first responsive**: Optimized for both desktop and mobile experiences
- **Dark mode by default**: Professional dark theme with light mode support

---

## Typography

### Font Family

```css
/* Primary Font: Inter (Google Fonts) */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
```

**Usage**:
- `--font-sans`: Inter (body text, UI elements)
- `--font-mono`: System monospace for tabular numbers

### Font Sizes

```css
/* Typography Scale */
--text-xs: 0.75rem;      /* 12px - Labels, badges */
--text-sm: 0.875rem;     /* 14px - Secondary text */
--text-base: 1rem;       /* 16px - Body text */
--text-lg: 1.125rem;     /* 18px - Subheadings */
--text-xl: 1.25rem;      /* 20px - Headings */
--text-2xl: 1.5rem;      /* 24px - Large values */
--text-3xl: 1.875rem;    /* 30px - Hero text */
```

### Font Weights

```css
--font-normal: 400;      /* Regular body text */
--font-medium: 500;      /* Emphasis, labels */
--font-semibold: 600;    /* Buttons, headings */
--font-bold: 700;        /* Values, important data */
```

### Letter Spacing

```css
--tracking-tight: -0.025em;   /* Large headings */
--tracking-normal: 0;         /* Body text */
--tracking-wide: 0.05em;      /* Uppercase labels */
```

### Common Typography Patterns

**Section Headers** (uppercase labels):
```css
font-size: 10px;
font-weight: 600;
text-transform: uppercase;
letter-spacing: 0.05em;
color: var(--text-secondary);
```

**Metric Values** (large numbers):
```css
font-size: 24px;
font-weight: 700;
font-family: var(--font-mono);
font-variant-numeric: tabular-nums;
color: var(--text-primary);
```

**Metric Labels**:
```css
font-size: 12px;
font-weight: 500;
text-transform: uppercase;
letter-spacing: 0.05em;
color: var(--text-secondary);
```

---

## Color System

### Base Color Palette

```javascript
// SigmaSight Brand Colors (Tailwind config)
sigmasight: {
  primary: '#0066cc',      // Blue
  secondary: '#4f46e5',    // Indigo
  accent: '#06b6d4',       // Cyan
  success: '#10b981',      // Green
  warning: '#f59e0b',      // Amber
  error: '#ef4444',        // Red
  dark: '#1f2937',         // Gray-800
  light: '#f8fafc'         // Slate-50
}
```

### Semantic Colors (Dark Theme)

**Backgrounds**:
```css
--bg-primary: hsl(0, 0%, 3.9%);        /* #0a0a0a - Base background */
--bg-secondary: hsl(0, 0%, 14.9%);     /* #262626 - Cards, containers */
--bg-tertiary: hsl(0, 0%, 20%);        /* #333333 - Hover states */
--bg-elevated: hsl(0, 0%, 18%);        /* Raised elements */
```

**Text Colors**:
```css
--text-primary: hsl(0, 0%, 98%);       /* #fafafa - Primary text */
--text-secondary: hsl(0, 0%, 63.9%);   /* #a3a3a3 - Secondary text */
--text-tertiary: hsl(0, 0%, 45.1%);    /* #737373 - Muted text */
```

**Borders**:
```css
--border-primary: hsl(0, 0%, 14.9%);   /* #262626 - Default borders */
--border-secondary: hsl(0, 0%, 20%);   /* #333333 - Subtle dividers */
--border-accent: hsl(0, 0%, 30%);      /* Emphasized borders */
```

**Financial Data Colors**:
```css
--color-success: #34d399;    /* Emerald-400 - Positive values */
--color-error: #f87171;      /* Red-400 - Negative values */
--color-warning: #fbbf24;    /* Amber-400 - Warnings */
--color-info: #06b6d4;       /* Cyan-500 - Info */
--color-accent: #06b6d4;     /* Cyan-500 - Highlights */
```

### Card Design Tokens

```css
/* Position Cards */
--card-bg: hsl(215, 28%, 17%);           /* Slate-800 (dark) */
--card-bg-hover: hsl(215, 25%, 20%);     /* Slate-750 (dark hover) */
--card-border: hsl(215, 20%, 35%);       /* Slate-700 (dark) */
--card-text: hsl(0, 0%, 100%);           /* White (dark) */
--card-text-muted: hsl(215, 20%, 65%);   /* Slate-400 (dark) */
```

### Badge Colors

```css
/* Badge variants for section headers */
.badge-success {
  background-color: rgba(52, 211, 153, 0.1);
  color: #34d399;
}

.badge-error {
  background-color: rgba(248, 113, 113, 0.1);
  color: #f87171;
}

.badge-warning {
  background-color: rgba(251, 191, 36, 0.1);
  color: #fbbf24;
}

.badge-info {
  background-color: rgba(6, 182, 212, 0.1);
  color: #06b6d4;
}
```

---

## Spacing & Layout

### Spacing Scale

```css
/* Tailwind spacing scale used throughout */
0.5 = 0.125rem   /* 2px */
1   = 0.25rem    /* 4px */
2   = 0.5rem     /* 8px */
3   = 0.75rem    /* 12px */
4   = 1rem       /* 16px */
5   = 1.25rem    /* 20px */
6   = 1.5rem     /* 24px */
8   = 2rem       /* 32px */
12  = 3rem       /* 48px */
16  = 4rem       /* 64px */
```

### Common Spacing Patterns

**Container Padding**:
```css
/* Desktop */
padding-left: 1rem;    /* px-4 */
padding-right: 1rem;   /* px-4 */

/* Mobile */
padding-left: 1rem;    /* px-4 */
padding-right: 1rem;   /* px-4 */
```

**Card Padding**:
```css
--card-padding: 1.5rem;  /* 24px - p-6 */
```

**Section Spacing**:
```css
/* Between sections */
padding-bottom: 1.5rem;  /* pb-6 */

/* Between metric cards */
gap: 1rem;              /* gap-4 */
```

### Border Radius

```css
--radius: 0.5rem;              /* 8px - Base radius */
--border-radius: 0.5rem;       /* 8px - Card radius */

/* Variants */
border-radius: calc(var(--radius) - 2px);  /* md */
border-radius: calc(var(--radius) - 4px);  /* sm */
border-radius: var(--radius);              /* lg */
border-radius: 0.75rem;                    /* xl - 12px */
border-radius: 9999px;                     /* full - Pills/badges */
```

### Container Widths

```css
.container {
  width: 100%;
  margin: 0 auto;
  padding: 0 1rem;
  max-width: 1400px;  /* 2xl breakpoint */
}
```

### Grid Layouts

**Hero Metrics (6-column)**:
```css
.grid {
  display: grid;
  grid-template-columns: 1fr;                    /* Mobile */
  gap: 1rem;
}

@media (min-width: 768px) {
  .grid {
    grid-template-columns: repeat(3, 1fr);       /* Tablet */
  }
}

@media (min-width: 1024px) {
  .grid {
    grid-template-columns: repeat(6, 1fr);       /* Desktop */
  }
}
```

---

## Components

### Buttons

**Primary Button** (default):
```css
.button-primary {
  background: hsl(0, 0%, 98%);           /* White */
  color: hsl(0, 0%, 9%);                 /* Near black */
  padding: 0.5rem 1rem;                  /* py-2 px-4 */
  border-radius: 0.375rem;               /* rounded-md */
  font-size: 0.875rem;                   /* text-sm */
  font-weight: 500;                      /* font-medium */
  height: 2.25rem;                       /* h-9 */
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  transition: all 150ms;
}

.button-primary:hover {
  background: hsl(0, 0%, 88%);           /* 90% opacity */
}
```

**Secondary Button**:
```css
.button-secondary {
  background: hsl(0, 0%, 14.9%);
  color: hsl(0, 0%, 98%);
  border: 1px solid hsl(0, 0%, 14.9%);
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  height: 2.25rem;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.button-secondary:hover {
  background: hsl(0, 0%, 20%);
}
```

**Ghost Button**:
```css
.button-ghost {
  background: transparent;
  color: hsl(0, 0%, 98%);
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  height: 2.25rem;
}

.button-ghost:hover {
  background: hsl(0, 0%, 14.9%);
}
```

**Active State** (navigation):
```css
.button-active {
  background: hsl(0, 0%, 98%);
  color: hsl(0, 0%, 9%);
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
  border: 2px solid hsl(0, 0%, 98%);
}
```

**Button Sizes**:
```css
/* Small */
height: 2rem;          /* h-8 */
padding: 0 0.75rem;    /* px-3 */
font-size: 0.75rem;    /* text-xs */

/* Default */
height: 2.25rem;       /* h-9 */
padding: 0 1rem;       /* px-4 */
font-size: 0.875rem;   /* text-sm */

/* Large */
height: 2.5rem;        /* h-10 */
padding: 0 2rem;       /* px-8 */
font-size: 0.875rem;   /* text-sm */

/* Icon */
height: 2.25rem;       /* h-9 */
width: 2.25rem;        /* w-9 */
```

### Cards

**Base Card**:
```css
.card {
  background: hsl(0, 0%, 14.9%);
  border: 1px solid hsl(0, 0%, 14.9%);
  border-radius: 0.75rem;               /* rounded-xl */
  padding: 1.5rem;                      /* p-6 */
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
```

**Metric Card**:
```css
.metric-card {
  background: hsl(0, 0%, 14.9%);
  border: 1px solid hsl(0, 0%, 14.9%);
  border-radius: 0.5rem;
  padding: 0.75rem;                     /* p-3 */
  transition: all 200ms;
}

.metric-card:hover {
  background: hsl(0, 0%, 20%);
}
```

**Card Header**:
```css
.card-header {
  display: flex;
  flex-direction: column;
  padding: 1.5rem;                      /* p-6 */
  gap: 0.375rem;                        /* space-y-1.5 */
}
```

**Card Title**:
```css
.card-title {
  font-weight: 600;
  line-height: 1;
  letter-spacing: -0.025em;
}
```

**Card Description**:
```css
.card-description {
  font-size: 0.875rem;
  color: hsl(0, 0%, 63.9%);
}
```

### Inputs

**Text Input**:
```css
.input {
  display: flex;
  height: 2.25rem;                      /* h-9 */
  width: 100%;
  border-radius: 0.375rem;              /* rounded-md */
  border: 1px solid hsl(0, 0%, 14.9%);
  background: transparent;
  padding: 0.25rem 0.75rem;             /* py-1 px-3 */
  font-size: 0.875rem;                  /* text-sm */
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  transition: colors 150ms;
}

.input:focus {
  outline: none;
  box-shadow: 0 0 0 1px hsl(0, 0%, 3.9%);
}

.input::placeholder {
  color: hsl(0, 0%, 45.1%);
}

.input:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
```

### Badges

**Default Badge**:
```css
.badge {
  display: inline-flex;
  align-items: center;
  border-radius: 9999px;                /* rounded-full */
  border: 1px solid transparent;
  padding: 0.125rem 0.625rem;           /* py-0.5 px-2.5 */
  font-size: 0.75rem;                   /* text-xs */
  font-weight: 600;
  transition: colors 150ms;
}
```

**Badge Variants**:
```css
/* Primary */
.badge-primary {
  background: hsl(0, 0%, 98%);
  color: hsl(0, 0%, 9%);
}

/* Secondary */
.badge-secondary {
  background: hsl(0, 0%, 14.9%);
  color: hsl(0, 0%, 98%);
}

/* Success */
.badge-success {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

/* Warning */
.badge-warning {
  background: rgba(251, 191, 36, 0.1);
  color: #fbbf24;
}

/* Danger */
.badge-danger {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

/* Outline */
.badge-outline {
  background: transparent;
  color: hsl(0, 0%, 98%);
  border: 1px solid currentColor;
}
```

### Navigation Header

**Desktop Header** (sticky):
```css
.header {
  position: sticky;
  top: 0;
  z-index: 50;
  width: 100%;
  border-bottom: 1px solid hsl(0, 0%, 14.9%);
  background: hsla(0, 0%, 3.9%, 0.95);
  backdrop-filter: blur(8px);
  height: 3.5rem;                       /* h-14 */
}
```

**Logo**:
```css
.logo {
  color: #34d399;                       /* Emerald-400 */
  font-size: 1.25rem;                   /* text-xl */
  font-weight: 700;                     /* font-bold */
}

.brand-name {
  font-size: 1.125rem;                  /* text-lg */
  font-weight: 600;                     /* font-semibold */
}
```

**Navigation Items**:
```css
.nav-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 150ms;
}

.nav-item:hover {
  background: hsl(0, 0%, 14.9%);
  color: hsl(0, 0%, 98%);
}

.nav-item.active {
  background: hsl(0, 0%, 98%);
  color: hsl(0, 0%, 9%);
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
  border: 2px solid hsl(0, 0%, 98%);
}
```

### Bottom Navigation (Mobile)

```css
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 50;
  height: 3.5rem;                       /* h-14 */
  background: hsla(0, 0%, 3.9%, 0.95);
  backdrop-filter: blur(8px);
  border-top: 1px solid hsl(0, 0%, 14.9%);
  padding-bottom: env(safe-area-inset-bottom);
}

.bottom-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  flex: 1;
  min-height: 44px;                     /* Touch target */
}

.bottom-nav-icon {
  width: 1.25rem;                       /* w-5 */
  height: 1.25rem;                      /* h-5 */
}

.bottom-nav-label {
  font-size: 0.75rem;                   /* text-xs */
  font-weight: 500;
}
```

### Tables

**Table Container**:
```css
.table-wrapper {
  width: 100%;
  overflow-x: auto;
  border-radius: 0.5rem;
  border: 1px solid hsl(0, 0%, 14.9%);
}

.table {
  width: 100%;
  font-size: 0.875rem;
  color: hsl(0, 0%, 98%);
}
```

**Table Header**:
```css
.table thead {
  background: hsl(0, 0%, 20%);
  position: sticky;
  top: 0;
  z-index: 10;
}

.table th {
  padding: 0.5rem 0.75rem;
  text-align: left;
  font-size: 0.75rem;
  font-weight: 500;
  color: hsl(0, 0%, 63.9%);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid hsl(0, 0%, 14.9%);
}
```

**Table Body**:
```css
.table tbody tr {
  border-bottom: 1px solid hsl(0, 0%, 14.9%);
  transition: background 150ms;
}

.table tbody tr:hover {
  background: hsl(0, 0%, 20%);
}

.table td {
  padding: 0.75rem;
  color: hsl(0, 0%, 63.9%);
}

.table td.primary {
  color: hsl(0, 0%, 98%);
  font-weight: 500;
}
```

---

## Dark Mode

### CSS Variables Pattern

**Light Theme** (`:root`):
```css
:root {
  --background: 0 0% 100%;              /* White */
  --foreground: 0 0% 3.9%;              /* Near black */
  --card: 0 0% 100%;
  --card-foreground: 0 0% 3.9%;
  --primary: 0 0% 9%;
  --primary-foreground: 0 0% 98%;
  --border: 0 0% 89.8%;
  --ring: 0 0% 3.9%;
}
```

**Dark Theme** (`.dark`):
```css
.dark {
  --background: 0 0% 3.9%;              /* Near black */
  --foreground: 0 0% 98%;               /* White */
  --card: 0 0% 3.9%;
  --card-foreground: 0 0% 98%;
  --primary: 0 0% 98%;
  --primary-foreground: 0 0% 9%;
  --border: 0 0% 14.9%;
  --ring: 0 0% 83.1%;
}
```

**Usage in Components**:
```css
/* Use HSL with CSS variables */
background-color: hsl(var(--background));
color: hsl(var(--foreground));
border-color: hsl(var(--border));
```

---

## Responsive Design

### Breakpoints

```css
/* Tailwind default breakpoints */
sm: 640px     /* Small devices (landscape phones) */
md: 768px     /* Medium devices (tablets) */
lg: 1024px    /* Large devices (desktops) */
xl: 1280px    /* Extra large devices */
2xl: 1400px   /* Container max-width */
```

### Mobile-First Utilities

```css
/* Mobile-specific spacing */
--tap-target-min: 44px;              /* Minimum touch target */
--bottom-nav-height: 56px;
--spacing-mobile: 12px;
--spacing-desktop: 24px;
--text-mobile-sm: 12px;
--text-mobile-base: 14px;
```

### iOS Safe Area Support

```css
/* iOS notch support */
@supports (padding: env(safe-area-inset-bottom)) {
  .pb-safe {
    padding-bottom: env(safe-area-inset-bottom);
  }

  .pt-safe {
    padding-top: env(safe-area-inset-top);
  }
}
```

### Responsive Grid Example

```css
/* Mobile: Single column */
.grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

/* Tablet: 3 columns */
@media (min-width: 768px) {
  .grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* Desktop: 6 columns */
@media (min-width: 1024px) {
  .grid {
    grid-template-columns: repeat(6, 1fr);
  }
}
```

---

## Common Patterns

### Metric Card Pattern

**Structure**:
```html
<div class="metric-card">
  <div class="metric-label">Equity Balance</div>
  <div class="metric-value">$2.4M</div>
  <div class="metric-context positive">+12.5%</div>
</div>
```

**Styles**:
```css
.metric-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: var(--border-radius);
  padding: var(--card-padding);
  box-shadow: var(--shadow-sm);
}

.metric-label {
  font-size: var(--text-xs);
  font-weight: 500;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  margin-bottom: 0.5rem;
}

.metric-value {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  margin-bottom: 0.25rem;
}

.metric-context.positive { color: var(--color-success); }
.metric-context.negative { color: var(--color-error); }
.metric-context.neutral { color: var(--text-tertiary); }
```

### Section Header Pattern

```html
<div class="section-header">
  <span class="section-badge">12 Positions</span>
  <h2 class="section-title">Long Equity</h2>
</div>
```

```css
.section-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.section-badge {
  background: rgba(100, 116, 139, 0.1);
  color: hsl(215, 20%, 65%);
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: hsl(0, 0%, 98%);
}
```

### Hero Metrics Row Pattern

```html
<section class="px-4 pb-4">
  <div class="container mx-auto">
    <div class="themed-border overflow-hidden bg-secondary">
      <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-7">
        <!-- Metric cards here -->
      </div>
    </div>
  </div>
</section>
```

**Bordered Grid Metrics**:
```css
.themed-border {
  border: 1px solid var(--border-primary);
}

.themed-border-r {
  border-right: 1px solid var(--border-primary);
}
```

### Loading State Pattern

```css
.loading-card {
  background: var(--bg-secondary);
  padding: 1rem;
  border-radius: var(--border-radius);
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

### Hover Effects

**Lift on Hover**:
```css
.hover-lift {
  transition: transform 200ms ease, box-shadow 200ms ease;
}

.hover-lift:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3);
}
```

**Background Color Change**:
```css
.hover-bg {
  transition: background-color 150ms ease;
}

.hover-bg:hover {
  background-color: var(--bg-tertiary);
}
```

---

## Implementation Notes

### Tailwind CSS

SigmaSight uses **Tailwind CSS 3.x** with custom configuration:

```javascript
// tailwind.config.js
module.exports = {
  darkMode: ["class"],
  theme: {
    extend: {
      colors: {
        // Custom color system
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)'
      }
    }
  },
  plugins: [
    require("tailwindcss-animate"),
    require("@tailwindcss/typography")
  ]
}
```

### ShadCN/UI Components

Base component library: **ShadCN/UI** (Radix UI + Tailwind)
- All components use class-variance-authority (CVA)
- Consistent with design system tokens
- Fully customizable and theme-aware

### CSS Variables

All colors and tokens use CSS variables for easy theming:
- Defined in `globals.css`
- Organized by category (backgrounds, text, borders)
- Support both light and dark modes
- Can be overridden per-theme

---

## Quick Reference

### Most Common Classes

```css
/* Layout */
.container              /* Max-width container with padding */
.flex                  /* Flexbox */
.grid                  /* CSS Grid */

/* Spacing */
.px-4                  /* Padding horizontal 16px */
.py-2                  /* Padding vertical 8px */
.gap-4                 /* Grid/flex gap 16px */
.mb-4                  /* Margin bottom 16px */

/* Typography */
.text-sm               /* 14px */
.font-semibold         /* 600 weight */
.tracking-wide         /* Letter spacing */
.uppercase             /* Text transform */

/* Colors */
.text-primary          /* Primary text color */
.text-secondary        /* Secondary text color */
.bg-secondary          /* Secondary background */
.border-primary        /* Primary border color */

/* Utilities */
.rounded-md            /* 6px border radius */
.shadow                /* Box shadow */
.transition-colors     /* Color transitions */
```

---

## Export for Other Frameworks

### CSS Variables Export

```css
/* Copy this to any CSS file for theme support */
:root {
  --bg-primary: hsl(0, 0%, 3.9%);
  --bg-secondary: hsl(0, 0%, 14.9%);
  --text-primary: hsl(0, 0%, 98%);
  --text-secondary: hsl(0, 0%, 63.9%);
  --border-primary: hsl(0, 0%, 14.9%);
  --color-success: #34d399;
  --color-error: #f87171;
  --radius: 0.5rem;
  --font-sans: 'Inter', sans-serif;
}
```

### Component Class Names

All components follow BEM-like naming:
- `.metric-card`
- `.metric-label`
- `.metric-value`
- `.section-header`
- `.section-badge`

Can be easily ported to any framework (React, Vue, Angular, etc.)

---

**End of Design System Documentation**
