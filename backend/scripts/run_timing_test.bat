@echo off
echo Starting timing test...
cd /d C:\Users\BenBalbale\CascadeProjects\SigmaSight\backend
echo Current directory: %CD%
set DATABASE_URL=postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway
echo DATABASE_URL set
echo Running test...
uv run python scripts/test_factor_timing.py --date 2025-12-18
echo Test complete with exit code: %ERRORLEVEL%
