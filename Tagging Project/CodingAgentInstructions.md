  1. Planning Documents (Start Here)

  PORTFOLIO_TAGGING_SYSTEM_PRD.md     # Complete system design with database schema
  SIGMASIGHT_UI_REFACTOR_PRD.md       # UI architecture and components
  IMPLEMENTATION_STRATEGY_PRD.md      # 3-week timeline and approach

  2. Backend Context

  backend/CLAUDE.md                   # Development commands and setup
  backend/AI_AGENT_REFERENCE.md       # Codebase architecture reference
  backend/API_AND_DATABASE_SUMMARY.md # Current database schema
  backend/alembic/versions/initial_schema.py  # Existing migration structure

  3. Frontend Context

  frontend/CLAUDE.md                  # Frontend setup and architecture
  frontend/app/portfolio/page.tsx     # Current portfolio page to refactor
  frontend/_docs/designinstructions/design-principles-example.md  # Design guidelines

  🎯 Instructions for New Agent

  Tell the new agent:

  Starting Point:

  1. Read IMPLEMENTATION_STRATEGY_PRD.md FIRST - it explains the 3-week plan
  2. Review PORTFOLIO_TAGGING_SYSTEM_PRD.md - Section 7 has the complete Alembic migration strategy
  3. Check SIGMASIGHT_UI_REFACTOR_PRD.md - Has all UI components specified

  Key Context:

  - Development environment - no production users, can make breaking changes
  - Every position needs a strategy (most will be "standalone")
  - Tags apply to strategies, not individual positions
  - Use ShadCN components exclusively for UI
  - 3-week aggressive timeline is possible because no backward compatibility needed

  First Implementation Steps:

  1. Backend Week 1: Run the Alembic migrations from Section 7.2 of PORTFOLIO_TAGGING_SYSTEM_PRD.md
  2. Frontend Week 1: Set up the navigation structure from SIGMASIGHT_UI_REFACTOR_PRD.md
  3. Can work in parallel since no production constraints

  Critical Decision Already Made:

  - Strategies are "virtual positions" that can be tagged
  - Every single position auto-creates a "standalone" strategy wrapper
  - This gives us a uniform data model with no special cases

  The new agent should start with IMPLEMENTATION_STRATEGY_PRD.md as it provides the roadmap, then use the other PRDs for detailed
  specifications. Good luck with the implementation!