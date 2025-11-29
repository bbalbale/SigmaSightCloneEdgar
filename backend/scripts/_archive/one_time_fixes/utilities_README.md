# Utility Scripts

General purpose utility scripts.

## Key Scripts

- **calculate_comprehensive_storage.py** - Calculate storage requirements for analytics data

## Usage

### Calculate storage requirements:
```bash
cd backend
uv run python scripts/utilities/calculate_comprehensive_storage.py
```

This provides detailed analysis of:
- Database storage per table
- JSON report sizes
- Cache storage requirements
- Projected growth rates
- Storage optimization recommendations