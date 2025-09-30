# SigmaSight Multi-Page Implementation - Master Guide

**Purpose**: Master index and quick reference for all implementation documents
**Audience**: AI coding agents with limited context windows
**Last Updated**: September 29, 2025
**Current Status**: Phase 1 Complete ✅ - Core infrastructure implemented

---

## 🚀 Implementation Progress

### ✅ Phase 1: Core Setup & State Management (COMPLETE)
**Completed on**: September 29, 2025

#### What's Been Built:
1. **Portfolio Store** (`src/stores/portfolioStore.ts`)
   - Global portfolio ID management with Zustand
   - localStorage persistence
   - Helper functions for non-React access

2. **Auth Providers** (`app/providers.tsx`)
   - Authentication context wrapper
   - Portfolio initialization on login
   - Protected route handling

3. **Navigation System**
   - `NavigationDropdown.tsx` - Dropdown menu with all 6 pages
   - `NavigationHeader.tsx` - Header component with branding
   - Updated `layout.tsx` with providers and navigation

4. **UI Components**
   - Installed ShadCN dropdown-menu component
   - Integrated with existing UI system

### 🔄 Phase 2: Data Hooks (PENDING)
- [ ] Create usePositions hook
- [ ] Create useStrategies hook
- [ ] Create useTags hook

### 📄 Phase 3-6: Pages & Containers (PENDING)
- [ ] Public Positions page
- [ ] Private Positions page
- [ ] Organize page
- [ ] AI Chat page
- [ ] Settings page

---

## 📚 Document Index

### Core Documents

1. **[01-MultiPage-Architecture-Overview.md](./01-MultiPage-Architecture-Overview.md)**
   - Architecture patterns and principles
   - Directory structure
   - Service layer overview
   - Authentication flow
   - Implementation phases
   - **When to read**: START HERE - before any implementation

2. **[07-Services-Reference.md](./07-Services-Reference.md)**
   - Complete reference for all 11 existing services
   - Service methods and usage examples
   - API endpoints mapping
   - Usage patterns
   - Critical rules (DO/DON'T)
   - **When to read**: Before writing any API code

3. **[08-Implementation-Checklist.md](./08-Implementation-Checklist.md)**
   - Step-by-step implementation guide
   - Phase-by-phase breakdown
   - Verification steps
   - File creation checklist
   - Testing guidelines
   - **When to read**: During implementation for tracking progress

### Page-Specific Guides

4. **[02-PublicPositions-Implementation.md](./02-PublicPositions-Implementation.md)**
   - Public positions page guide
   - Hook creation (usePositions)
   - Component creation (PositionSummary, PositionsTable)
   - Investment class filtering
   - **When to implement**: Phase 3, Week 2

5. **[03-PrivatePositions-Implementation.md](./03-PrivatePositions-Implementation.md)**
   - Private positions page guide
   - Reusing public positions components
   - Only 2 new files needed
   - **When to implement**: Phase 3, Week 2

6. **[04-Organize-Implementation.md](./04-Organize-Implementation.md)**
   - Organize page guide (strategies + tags)
   - Hook creation (useStrategies, useTags)
   - Strategy and tag management
   - Two-column layout
   - **When to implement**: Phase 4, Week 2-3

7. **[05-AIChat-Implementation.md](./05-AIChat-Implementation.md)**
   - AI Chat page guide
   - Reusing existing ChatInterface
   - SSE streaming details
   - Portfolio context integration
   - **When to implement**: Phase 5, Week 3

8. **[06-Settings-Implementation.md](./06-Settings-Implementation.md)**
   - Settings page guide
   - User settings form
   - Portfolio settings form
   - Export functionality
   - Three-tab layout
   - **When to implement**: Phase 6, Week 3

---

## 🎯 Quick Start Guide

### For AI Agents Starting Fresh

**Step 1**: Read Architecture Overview
```
Read: 01-MultiPage-Architecture-Overview.md
Focus: Architecture Pattern, Directory Structure, Key Principles
```

**Step 2**: Review Services Reference
```
Read: 07-Services-Reference.md
Focus: Available Services, Usage Patterns, Critical Rules
```

**Step 3**: Follow Implementation Checklist
```
Read: 08-Implementation-Checklist.md
Follow: Phase 1 → Phase 2 → Phase 3 → etc.
```

**Step 4**: Implement Each Page
```
Read: Page-specific guides (02-06)
Implement: Hook → Components → Container → Page
```

---

## 🏗️ Architecture Summary

### Hybrid Architecture Approach

**Existing Pages (Keep As-Is):**
- Portfolio page: Already refactored to modular pattern (~230 lines)
- Uses hooks directly in page file
- Working well, no changes needed

**New Pages (Container Pattern):**
```
Thin Route (5-15 lines)
    ↓ imports
Container (150-250 lines)
    ↓ uses
Hooks + Components
    ↓ call
Services (existing!)
    ↓ through
API Proxy
    ↓ to
Backend (FastAPI)
```

### Directory Structure
```
app/
├── portfolio/                 # ✅ EXISTING - Keep as-is (modular pattern)
├── providers.tsx              # 🆕 Auth context & global state
├── layout.tsx                 # 📝 Add providers & navigation
├── public-positions/          # 🆕 New route (container pattern)
├── private-positions/         # 🆕 New route (container pattern)
├── organize/                  # 🆕 New route (container pattern)
├── ai-chat/                   # 🆕 New route (container pattern)
└── settings/                  # 🆕 New route (container pattern)

src/
├── stores/
│   └── portfolioStore.ts     # 🆕 Zustand store for portfolio ID
├── containers/                # 🆕 New folder (5 containers)
├── components/
│   ├── navigation/
│   │   └── NavigationDropdown.tsx # 🆕 Dropdown menu (6 pages)
│   ├── positions/            # ✅ Reuse existing components
│   ├── strategies/           # 🆕 Strategy components
│   ├── tags/                 # 🆕 Tag components
│   └── settings/             # 🆕 Settings components
├── hooks/
│   ├── usePositions.ts       # 🆕 Positions hook
│   ├── useStrategies.ts      # 🆕 Strategies hook
│   └── useTags.ts            # 🆕 Tags hook
└── services/                  # ✅ Keep all existing (11 services)
```

### State Management
- **Portfolio ID**: Stored in Zustand (no URL params)
- **User Auth**: React Context in providers.tsx
- **Portfolio Switching**: Logout required (no in-app switching)
- **Navigation**: Dropdown menu with all 6 pages

---

## 📊 Implementation Stats

### Files to Create
- **Core Setup**: 3 files (providers, portfolioStore, NavigationDropdown)
- **Hooks**: 3 files
- **Components**: 6-8 files (reusing existing position components)
- **Containers**: 5 files
- **Pages**: 5 files (thin wrappers)
- **Modified**: 1 file (layout.tsx)
- **Existing**: 1 file kept as-is (portfolio page)
- **TOTAL**: 22-24 new + 1 modified = **23-25 files**

### Services Used
- **apiClient**: Base HTTP client (all pages use this)
- **authManager**: Authentication (providers use this)
- **portfolioResolver**: Portfolio ID (providers use this)
- **strategiesApi**: Strategies (Organize page)
- **tagsApi**: Tags (Organize page)
- **chatService**: Chat (AI Chat page, via ChatInterface)
- **chatAuthService**: Chat auth (AI Chat page, via ChatInterface)

### Implementation Time (Revised for Hybrid Approach)
- **Phase 1** (Core Setup & State): 2 days
  - Zustand portfolioStore
  - Providers with auth context
  - NavigationDropdown component
- **Phase 2** (Hooks): 1 day (simpler with Zustand)
- **Phase 3** (Position Pages): 2 days (reusing components)
- **Phase 4** (Organize): 2 days
- **Phase 5** (AI Chat): 1 day (reusing ChatInterface)
- **Phase 6** (Settings): 2 days
- **Phase 7** (Testing): 3 days
- **TOTAL**: ~11-13 days (portfolio page already done)

---

## 🔑 Key Principles

### Always Remember

1. **Client-Side Only**
   - All pages use `'use client'`
   - No React Server Components
   - No `'server-only'` imports

2. **Use Existing Services**
   - ALL API calls through services
   - NEVER direct `fetch()` calls
   - Check Services-Reference.md first

3. **Thin Page Files**
   - Pages are 5-15 lines max
   - Just import and render container
   - No business logic in pages

4. **Use portfolioResolver**
   - NEVER hardcode portfolio IDs
   - Always use resolver service
   - Cache clearing on logout

5. **Follow the Pattern**
   - Hook → Components → Container → Page
   - Data in hooks, UI in components
   - Composition in containers

---

## ⚠️ Common Mistakes

### ❌ Things to Avoid

1. **Direct API Calls**
   ```typescript
   // ❌ WRONG
   fetch('http://localhost:8000/api/v1/data/positions')
   
   // ✅ CORRECT
   import { apiClient } from '@/services/apiClient'
   apiClient.get('/api/v1/data/positions')
   ```

2. **Hardcoded IDs**
   ```typescript
   // ❌ WRONG
   const portfolioId = '1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe'
   
   // ✅ CORRECT
   import { portfolioResolver } from '@/services/portfolioResolver'
   const portfolioId = await portfolioResolver.getUserPortfolioId()
   ```

3. **Recreating Services**
   ```typescript
   // ❌ WRONG
   class NewApiService { ... }
   
   // ✅ CORRECT
   import strategiesApi from '@/services/strategiesApi'
   ```

4. **Fat Page Files**
   ```typescript
   // ❌ WRONG - 200 lines in page.tsx
   export default function Page() {
     const [data, setData] = useState([])
     useEffect(() => { /* 100 lines */ }, [])
     return <div>{/* 100 lines */}</div>
   }
   
   // ✅ CORRECT - 8 lines in page.tsx
   export default function Page() {
     return <PageContainer />
   }
   ```

5. **Missing 'use client'**
   ```typescript
   // ❌ WRONG - No directive
   export default function Page() { ... }
   
   // ✅ CORRECT - Has directive
   'use client'
   export default function Page() { ... }
   ```

---

## 📋 Pre-Implementation Checklist

Before starting any implementation, verify:

- [ ] I have read 01-MultiPage-Architecture-Overview.md
- [ ] I have read 07-Services-Reference.md
- [ ] I understand the Hook → Container → Page pattern
- [ ] I know which services exist (11 total)
- [ ] I will NOT make direct fetch() calls
- [ ] I will NOT hardcode portfolio IDs
- [ ] I will use existing services
- [ ] I will keep pages thin (5-15 lines)
- [ ] I will use 'use client' directive
- [ ] I have 08-Implementation-Checklist.md ready

---

## 🎓 Learning Path

### For New AI Agents

**Day 1**: Architecture Understanding
- Read: 01-MultiPage-Architecture-Overview.md
- Understand: Client-side architecture, directory structure
- Review: Existing services and their purposes

**Day 2**: Service Mastery
- Read: 07-Services-Reference.md
- Learn: All 11 services and their methods
- Practice: Service usage patterns

**Day 3-5**: Core Setup
- Follow: Phase 1 of checklist
- Create: Providers and navigation
- Test: Authentication flow

**Week 2**: Position Pages
- Follow: Phase 2-3 of checklist
- Read: 02-PublicPositions-Implementation.md
- Read: 03-PrivatePositions-Implementation.md
- Implement: Hooks, components, containers, pages

**Week 3**: Organization & Chat
- Follow: Phase 4-5 of checklist
- Read: 04-Organize-Implementation.md
- Read: 05-AIChat-Implementation.md
- Implement: Strategy/tag management, chat interface

**Week 4**: Settings & Testing
- Follow: Phase 6-7 of checklist
- Read: 06-Settings-Implementation.md
- Implement: Settings pages
- Complete: Full testing

---

## 🔍 Troubleshooting Guide

### Issue: Service not found
**Solution**: Check 07-Services-Reference.md for correct import path

### Issue: Portfolio ID is null
**Solution**: 
1. Check authentication (user logged in?)
2. Verify portfolioResolver.getUserPortfolioId() called
3. Check backend has portfolio for user

### Issue: API call fails
**Solution**:
1. Verify backend is running (localhost:8000)
2. Check proxy configuration
3. Verify service is being used (not direct fetch)
4. Check authentication token is valid

### Issue: Page shows blank
**Solution**:
1. Check browser console for errors
2. Verify 'use client' directive present
3. Check container is imported correctly
4. Verify hooks return data

### Issue: Component not found
**Solution**:
1. Check file path is correct
2. Verify component is exported
3. Check import statement uses '@/' alias

---

## 📞 Quick Reference

### File Naming Conventions
- Pages: lowercase with hyphens (`public-positions/page.tsx`)
- Components: PascalCase (`PositionsTable.tsx`)
- Hooks: camelCase with 'use' prefix (`usePositions.ts`)
- Containers: PascalCase with 'Container' suffix (`PublicPositionsContainer.tsx`)

### Import Aliases
```typescript
'@/services/*'     // Services
'@/components/*'   // Components
'@/hooks/*'        // Hooks
'@/containers/*'   // Containers
'@/lib/*'          // Utilities
'@/app/*'          // App files
```

### Service Import Patterns
```typescript
// Default export
import { apiClient } from '@/services/apiClient'
import { authManager } from '@/services/authManager'

// Named default
import strategiesApi from '@/services/strategiesApi'
import tagsApi from '@/services/tagsApi'
```

---

## ✅ Success Criteria

### Implementation Complete When:
- [ ] All 25 new files created
- [ ] All 5 pages accessible via navigation
- [ ] All pages use existing services
- [ ] No direct fetch() calls anywhere
- [ ] No hardcoded portfolio IDs
- [ ] All loading states work
- [ ] All error states handled
- [ ] Authentication flow works
- [ ] Data filtering works correctly
- [ ] Exports download properly
- [ ] Chat streams correctly
- [ ] All tests pass
- [ ] No console errors
- [ ] Performance acceptable

---

## 📖 Document Sizes

To keep context windows manageable:

| Document | Lines | Purpose | When to Read |
|----------|-------|---------|--------------|
| 01-Architecture | ~400 | Overview & patterns | First, always |
| 02-PublicPositions | ~400 | Position page guide | Week 2 |
| 03-PrivatePositions | ~300 | Private page guide | Week 2 |
| 04-Organize | ~500 | Organize page guide | Week 2-3 |
| 05-AIChat | ~350 | Chat page guide | Week 3 |
| 06-Settings | ~500 | Settings page guide | Week 3 |
| 07-Services | ~600 | Services reference | Before API code |
| 08-Checklist | ~600 | Implementation guide | Throughout |
| 00-Master (this) | ~400 | Index & summary | Reference |

**Total**: ~3,450 lines across 9 documents  
**Average**: ~380 lines per document  
**Fits**: Most AI agent context windows

---

## 🚀 Getting Started

### Step 1: Orient Yourself
```
Read this document (00-Master-Summary.md) completely
Understand the document structure
Know which doc to read when
```

### Step 2: Understand Architecture
```
Read: 01-MultiPage-Architecture-Overview.md
Time: 10-15 minutes
Focus: Pattern, structure, principles
```

### Step 3: Learn Services
```
Read: 07-Services-Reference.md
Time: 15-20 minutes
Focus: What exists, how to use it
```

### Step 4: Start Implementation
```
Read: 08-Implementation-Checklist.md
Follow: Phase by phase
Use: Page guides as needed
```

---

## 💡 Tips for Success

1. **Read Documents in Order**
   - Don't skip the architecture overview
   - Services reference saves time later
   - Page guides when you reach that phase

2. **Test Incrementally**
   - Complete each phase before moving on
   - Verify services work before using them
   - Test components individually

3. **Use Existing Code**
   - All 11 services already exist
   - ChatInterface already works
   - UI components already styled

4. **Keep It Simple**
   - Follow the established pattern
   - Don't over-engineer
   - Thin pages, focused components

5. **Verify Service Usage**
   - Check Services-Reference.md frequently
   - Never assume a service doesn't exist
   - Use existing services, don't recreate

---

## 📝 Final Notes

### These Documents Replace
- ❌ SigmaSight-MultiPage-ClientSide-Guide.md (too big, outdated)
- ❌ SigmaSight-MultiPage-Integration-Guide.md (too big, outdated)
- ❌ SigmaSight-MultiPage-ThinRoutes-Guide.md (too big, outdated)

### These Documents Are
- ✅ Right-sized for AI agents (<600 lines each)
- ✅ Accurate to current architecture
- ✅ Service-focused (not direct API calls)
- ✅ Client-side only (FastAPI backend)
- ✅ Organized by phase and feature

### Remember
**The key to success is using existing services, not recreating functionality!**

---

## Summary

**Total Documents**: 9  
**Implementation Pattern**: Hook → Components → Container → Page  
**Core Principle**: Always use existing services  
**Total Files**: 27 (25 new + 2 modified)  
**Implementation Time**: 3-4 weeks  
**Success Key**: Read docs, use services, follow pattern
