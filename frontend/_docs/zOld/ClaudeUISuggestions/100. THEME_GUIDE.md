# SigmaSight Theme System Guide

## Quick Start

The theme system is now live! You can switch between 4 visual themes without changing any code.

### How to Switch Themes

**Option 1: Click the floating 🎨 button** (bottom-right corner)
- Opens a theme picker
- Click any theme to preview it instantly
- Your choice persists across page refreshes

**Option 2: Press `T` key**
- Cycles through all 4 themes
- Works anywhere (except when typing in input fields)

**Option 3: Programmatically (for components)**
```typescript
import { useTheme } from '@/contexts/ThemeContext'

function MyComponent() {
  const { currentTheme, setTheme } = useTheme()

  return (
    <button onClick={() => setTheme('midnight-premium')}>
      Switch to Midnight
    </button>
  )
}
```

---

## Available Themes

### 1. **Bloomberg Classic** (Default)
- **Look**: High density, familiar blue accent, borders
- **Use case**: Your current style - dense information display
- **Key colors**:
  - Background: Dark slate (#020617)
  - Accent: Classic blue (#2563eb)
  - Borders: Visible borders (no shadows)

### 2. **Midnight Premium** (Recommended for 2025)
- **Look**: Modern navy, purple accent, soft shadows
- **Use case**: Professional yet modern, easy on eyes
- **Key colors**:
  - Background: Navy (#0A0E27)
  - Accent: Purple-blue (#635BFF - Stripe-inspired)
  - Shadows: Soft depth instead of borders

### 3. **Carbon Professional**
- **Look**: IBM-inspired, clean, high contrast
- **Use case**: Corporate, maximum readability
- **Key colors**:
  - Background: Carbon black (#161616)
  - Accent: IBM blue (#0F62FE)
  - Borders: Hybrid (borders + subtle shadows)

### 4. **Moonlight Elegant**
- **Look**: Deep purple-black, coral accent, softest on eyes
- **Use case**: Night mode, extended viewing sessions
- **Key colors**:
  - Background: Purple-black (#1A1A2E)
  - Accent: Coral pink (#E94560)
  - Shadows: Prominent depth

---

## How to Use Themes in Your Components

### Method 1: CSS Utility Classes (Easiest)

We've created utility classes that automatically adapt to the active theme:

```jsx
// Simple metric card using theme classes
<div className="themed-card">
  <div className="metric-label">Net Worth</div>
  <div className="metric-value">$2,847,392</div>
  <div className="metric-context positive">+$124K MTD ↑</div>
</div>
```

**Available Classes:**
- `themed-card` - Card with appropriate border/shadow
- `themed-card-shadow` - Card with shadow (no border)
- `bg-primary`, `bg-secondary`, `bg-tertiary` - Backgrounds
- `text-primary`, `text-secondary`, `text-tertiary` - Text colors
- `text-success`, `text-error`, `text-warning` - Semantic colors
- `themed-table` - Table with theme-aware styling
- `btn-accent`, `btn-secondary` - Themed buttons

See `src/styles/theme-utilities.css` for the full list.

### Method 2: CSS Variables (More Control)

Access theme values directly via CSS variables:

```jsx
<div style={{
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-primary)',
  borderRadius: 'var(--border-radius)',
  padding: 'var(--card-padding)',
  fontSize: 'var(--text-sm)',
  color: 'var(--text-primary)'
}}>
  Custom styled component
</div>
```

**Available CSS Variables:**

**Colors:**
- `--bg-primary`, `--bg-secondary`, `--bg-tertiary`, `--bg-elevated`
- `--border-primary`, `--border-secondary`, `--border-accent`
- `--text-primary`, `--text-secondary`, `--text-tertiary`
- `--color-success`, `--color-error`, `--color-warning`, `--color-info`
- `--color-accent`, `--color-accent-hover`, `--color-accent-subtle`

**Typography:**
- `--font-display`, `--font-body`, `--font-mono`
- `--text-xs` (11px), `--text-sm` (13px), `--text-base` (14px)
- `--text-lg` (16px), `--text-xl` (18px), `--text-2xl` (22px), `--text-3xl` (28px)
- `--tracking-tight`, `--tracking-normal`, `--tracking-wide`

**Visual:**
- `--border-radius` - Consistent corner rounding
- `--shadow-sm`, `--shadow-md`, `--shadow-lg` - Elevation shadows
- `--card-padding` - Standard card padding

### Method 3: TypeScript Theme Object (Advanced)

Access full theme configuration in code:

```typescript
import { useTheme } from '@/contexts/ThemeContext'

function AdvancedComponent() {
  const { theme } = useTheme()

  // Access any theme value
  console.log(theme.colors.accent)  // "#635BFF" for Midnight Premium
  console.log(theme.visual.borderStyle)  // "shadows" or "borders" or "hybrid"
  console.log(theme.typography.textSm)  // "0.8125rem"

  return <div>...</div>
}
```

---

## Migration Guide

### Converting Existing Components

**Before (Hardcoded Tailwind):**
```jsx
<div className="bg-slate-900 border border-slate-700 rounded-lg p-4">
  <div className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-2">
    Equity Balance
  </div>
  <div className="text-2xl font-bold text-slate-50 tabular-nums mb-1">
    $2,847,392
  </div>
</div>
```

**After (Theme-Aware - Option 1: Utility Classes):**
```jsx
<div className="themed-card">
  <div className="metric-label">
    Equity Balance
  </div>
  <div className="metric-value">
    $2,847,392
  </div>
</div>
```

**After (Theme-Aware - Option 2: CSS Variables):**
```jsx
<div style={{
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-primary)',
  borderRadius: 'var(--border-radius)',
  padding: 'var(--card-padding)'
}}>
  <div style={{
    fontSize: 'var(--text-xs)',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: 'var(--tracking-wide)',
    marginBottom: '0.5rem'
  }}>
    Equity Balance
  </div>
  <div style={{
    fontSize: 'var(--text-2xl)',
    fontWeight: 700,
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-mono)',
    marginBottom: '0.25rem'
  }}>
    $2,847,392
  </div>
</div>
```

---

## Font Sizes (Small for Density)

All themes use **small fonts** optimized for data density:

- **11px** (`--text-xs`) - Labels, tertiary info
- **13px** (`--text-sm`) - Table cells, body text
- **14px** (`--text-base`) - Default body text
- **16px** (`--text-lg`) - Section headers
- **18px** (`--text-xl`) - Card titles
- **22px** (`--text-2xl`) - Hero metric values
- **28px** (`--text-3xl`) - Page titles

This preserves your information density while improving aesthetics.

---

## Testing Each Theme

To test all themes quickly:

1. **Start the frontend**: `docker-compose up -d` or `npm run dev`
2. **Login** to any page
3. **Press `T`** repeatedly to cycle through all 4 themes
4. **Check**:
   - Background colors change
   - Accent colors change (buttons, links)
   - Shadows appear/disappear (Bloomberg Classic has none, others have shadows)
   - All text remains readable
   - Cards look distinct from background

---

## Next Steps

### Immediate: Try It Out
1. Navigate to `/portfolio` (or any page)
2. Click the 🎨 button bottom-right
3. Try each theme - see which you prefer
4. Press `T` to quickly cycle between themes

### Short-Term: Migrate Components
- Start with high-visibility pages (Portfolio, Command Center)
- Replace hardcoded Tailwind colors with theme utilities
- Test all 4 themes to ensure good contrast

### Long-Term: Customize Themes
- Edit `src/lib/themes.ts` to adjust colors
- Add new themes (just add to the `themes` object)
- Adjust font sizes if needed (currently optimized for density)

---

## Keyboard Shortcuts

- **`T`** - Cycle to next theme
- **`Cmd/Ctrl + K`** - (Future) Command palette to select theme

---

## FAQ

**Q: Will my existing components break?**
A: No. Existing components still work. Theme system is additive.

**Q: Can I keep Bloomberg Classic forever?**
A: Yes! It's the default. Users can choose their preference.

**Q: Which theme should I use?**
A: Start with **Midnight Premium** for a modern 2025 look. Keep Bloomberg Classic if you prefer familiarity.

**Q: Can I adjust font sizes?**
A: Yes! Edit `src/lib/themes.ts` → `typography` section for any theme.

**Q: How do I add a 5th theme?**
A: Add a new entry to `src/lib/themes.ts`, following the existing pattern. It'll appear in the theme picker automatically.

---

## Support

- **Theme system code**: `src/lib/themes.ts` (definitions), `src/contexts/ThemeContext.tsx` (provider)
- **Utility classes**: `src/styles/theme-utilities.css`
- **Selector UI**: `src/components/ThemeSelector.tsx`

Happy theming! 🎨
