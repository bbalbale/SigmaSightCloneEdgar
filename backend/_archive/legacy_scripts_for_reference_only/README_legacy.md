# Legacy Scripts Reference

These scripts are provided for REFERENCE ONLY. Do not copy them directly.

## Purpose
- Extract business logic and mathematical calculations
- Understand data transformation patterns
- Learn API integration approaches
- Reference calculation methodologies

## Migration Guidelines
1. **Extract Core Logic**: Focus on mathematical formulas and business rules
2. **Modernize Architecture**: Replace S3/Parquet with PostgreSQL
3. **Use Async Patterns**: Convert synchronous code to async FastAPI services
4. **Add Type Safety**: Implement with type hints and Pydantic models
5. **Improve Error Handling**: Add comprehensive logging and recovery

## Key Transformations
- Excel → CSV input format
- S3/Parquet → PostgreSQL storage
- Synchronous → Async operations
- Scripts → Service classes
- Global state → Dependency injection

## DO NOT:
- Copy infrastructure code (S3, Parquet operations)
- Use global variables or state
- Implement synchronous blocking operations
- Include legacy authentication methods