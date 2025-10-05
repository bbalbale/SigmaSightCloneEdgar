# 🪟 Windows Setup Guide for SigmaSight Backend

> **Last Updated**: 2025-08-26
> **Current Phase**: 3.0 - API Development (30% complete)  
> **API Status**: Raw Data APIs 100% operational at `/api/v1/data/`

This guide will help you set up the SigmaSight backend on Windows with minimal technical knowledge.

## 📋 What You'll Need

- Windows 10 or 11
- About 30 minutes
- Internet connection
- Administrator access on your computer

## 🎯 Overview

We'll install these tools in order:
1. **Python** - The programming language
2. **Git** - To download the code
3. **Docker Desktop** - To run the database
4. **UV** - To manage Python packages

---

## Step 1: Install Python 🐍

1. **Download Python:**
   - Go to https://python.org/downloads/
   - Click the big yellow "Download Python 3.11.x" button
   - Save the installer

2. **Install Python:**
   - Double-click the downloaded file
   - ⚠️ **IMPORTANT**: Check ✅ "Add Python 3.11 to PATH" at the bottom
   - Click "Install Now"
   - Wait for installation to complete
   - Click "Close"

3. **Verify Python:**
   - Press `Windows + R`
   - Type `cmd` and press Enter
   - In the black window, type: `python --version`
   - You should see: `Python 3.11.x`
   - Type `exit` to close

---

## Step 2: Install Git 📦

1. **Download Git:**
   - Go to https://git-scm.com/download/win
   - The download should start automatically
   - If not, click "64-bit Git for Windows Setup"

2. **Install Git:**
   - Double-click the downloaded file
   - Click "Next" on all screens (default settings are fine)
   - Click "Install"
   - Click "Finish"

3. **Verify Git:**
   - Open a new Command Prompt (Windows + R, type `cmd`, Enter)
   - Type: `git --version`
   - You should see: `git version 2.x.x`

---

## Step 3: Install Docker Desktop 🐳

1. **Download Docker Desktop:**
   - Go to https://www.docker.com/products/docker-desktop/
   - Click "Download for Windows"
   - Save the installer

2. **Install Docker Desktop:**
   - Double-click "Docker Desktop Installer.exe"
   - Follow the installation wizard
   - ⚠️ **IMPORTANT**: When prompted, ensure "Use WSL 2" is selected
   - Click "Ok" and wait for installation
   - **Restart your computer** when prompted

3. **Start Docker Desktop:**
   - After restart, Docker Desktop should start automatically
   - If not, find "Docker Desktop" in Start Menu and click it
   - Wait for Docker to fully start (whale icon in system tray turns green)
   - You might see a tutorial - you can skip it

4. **Verify Docker:**
   - Open Command Prompt
   - Type: `docker --version`
   - You should see: `Docker version 2x.x.x`

---

## Step 4: Install UV Package Manager 📚

1. **Open PowerShell as Administrator:**
   - Right-click the Start button
   - Click "Windows PowerShell (Admin)"
   - Click "Yes" if prompted

2. **Install UV:**
   - Copy and paste this command:
   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   - Press Enter
   - Wait for installation to complete

3. **Close and Reopen PowerShell:**
   - Type `exit` and press Enter
   - Open a regular PowerShell (not as admin)

4. **Verify UV:**
   - Type: `uv --version`
   - You should see: `uv 0.x.x`

---

## Step 5: Download SigmaSight Code 💻

1. **Create a folder for projects:**
   - Open File Explorer
   - Go to `C:\`
   - Right-click → New → Folder
   - Name it `Projects`

2. **Open Command Prompt in Projects folder:**
   - Navigate to `C:\Projects` in File Explorer
   - Click in the address bar
   - Type `cmd` and press Enter

3. **Download the code:**
   - Copy and paste this command:
   ```bash
   git clone https://github.com/elliottng/SigmaSight-BE.git
   ```
   - Press Enter
   - Wait for download to complete

4. **Navigate to the project:**
   ```bash
   cd SigmaSight-BE\backend
   ```

---

## Step 6: Set Up the Project 🔧

1. **Install Python packages:**
   ```bash
   uv sync
   ```
   - This creates a virtual environment and installs all dependencies
   - Wait for "Installed X packages" message

2. **Create clean configuration file:**
   ```bash
   echo # Database Configuration > .env
   echo DATABASE_URL=postgresql+asyncpg://sigmasight:sigmasight_dev@localhost:5432/sigmasight_db >> .env
   echo. >> .env
   echo # Market Data API Keys >> .env
   echo POLYGON_API_KEY=your_polygon_api_key_here >> .env
   echo FMP_API_KEY=your_fmp_api_key_here >> .env
   echo TRADEFEEDS_API_KEY=your_tradefeeds_api_key_here >> .env
   echo FRED_API_KEY=your_fred_api_key_here >> .env
   echo. >> .env
   echo # JWT Configuration >> .env
   echo JWT_SECRET_KEY=your_generated_secret_key_here >> .env
   echo. >> .env
   echo # Application Settings >> .env
   echo DEBUG=true >> .env
   echo ENVIRONMENT=development >> .env
   echo LOG_LEVEL=INFO >> .env
   ```
   - This creates a clean configuration file without conflicts

3. **Generate secure secret key:**
   - If you have Git Bash: `openssl rand -hex 32`
   - Or use any 64-character random string
   - Replace `your_generated_secret_key_here` in .env with the generated key

---

## Step 7: Start the Database 🗄️

1. **Start PostgreSQL database:**
   ```bash
   docker-compose up -d
   ```
   - This starts the database in the background
   - First time may take a few minutes to download

2. **Verify database is running:**
   ```bash
   docker ps
   ```
   - You should see a container named `backend_postgres_1` or similar

3. **Set up database tables (Professional Approach):**
   ```bash
   uv run python scripts/setup_dev_database_alembic.py
   ```
   - This uses proper Alembic migrations for professional development
   - When prompted, type `y` and press Enter to continue
   - Provides proper database versioning and rollback capabilities

4. **Create demo users (bulletproof method):**
   ```bash
   set PYTHONIOENCODING=utf-8 && uv run python scripts/setup_minimal_demo.py
   ```
   - This creates three demo accounts without async/sync issues:
     - demo_individual@sigmasight.com (password: demo12345)
     - demo_hnw@sigmasight.com (password: demo12345)  
     - demo_hedgefundstyle@sigmasight.com (password: demo12345)
   - **Note**: The `set PYTHONIOENCODING=utf-8` prevents Unicode display errors on Windows

---

## Step 8: Start SigmaSight API Server 🚀

1. **Start the FastAPI application:**
   ```bash
   uv run python run.py
   ```
   
   **Expected output:**
   ```
   INFO:     Started server process [12345]
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
   ```

2. **Verify it's working:**
   - Open your web browser
   - Go to http://localhost:8000/health
   - You should see: `{"status": "healthy"}`

3. **View API Documentation:**
   - Go to http://localhost:8000/docs
   - You'll see all available API endpoints
   - The Raw Data APIs (`/api/v1/data/`) are 100% complete and ready for testing

4. **Test Authentication:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/login" ^
     -H "Content-Type: application/json" ^
     -d "{\"email\": \"demo_individual@sigmasight.com\", \"password\": \"demo12345\"}"
   ```
   - Save the `access_token` from the response for testing other endpoints

5. **Validate Complete Setup:
   ```bash
   set PYTHONIOENCODING=utf-8 && uv run python scripts/validate_setup.py
   ```
   - This checks all components are working correctly
   - You should see "📊 Validation Summary: 8/8 checks passed"

---

## 📝 Daily Usage

After initial setup, here's how to start SigmaSight each day:

1. **Start Docker Desktop** (if not already running)
   - Look for whale icon in system tray

2. **Open Command Prompt**
   - Navigate to project: `cd C:\Projects\SigmaSight-BE\backend`

3. **Start the database:**
   ```bash
   docker-compose up -d
   ```

4. **Option A: Start API Server Only**
   ```bash
   uv run python run.py
   ```

5. **Option B: Run Batch Processing and Generate Reports**
   ```bash
   # Process all portfolios and generate reports
   uv run python scripts/batch_processing/run_batch.py
   
   # View generated reports
   explorer reports  # Opens reports folder
   ```

6. **Find Portfolio IDs (if needed):**
   ```bash
   set PYTHONIOENCODING=utf-8 && uv run python scripts/list_portfolios.py
   ```

7. **Stop everything when done:**
   - Press `Ctrl + C` in Command Prompt to stop SigmaSight
   - Run `docker-compose down` to stop the database

---

## 🆘 Troubleshooting

### "python is not recognized"
- Python wasn't added to PATH during installation
- Reinstall Python and make sure to check "Add to PATH"

### "docker is not recognized"
- Docker Desktop isn't running
- Start Docker Desktop from Start Menu

### "Cannot connect to Docker daemon"
- Docker Desktop isn't fully started
- Wait for whale icon to turn green in system tray

### "uv is not recognized"
- Close and reopen Command Prompt after UV installation
- Try running in PowerShell instead

### Database connection errors
- Make sure Docker is running: `docker ps`
- Restart database: `docker-compose down` then `docker-compose up -d`

### Unicode/Encoding errors (emojis not displaying)
- Use `set PYTHONIOENCODING=utf-8 &&` before Python commands
- This is normal on older Windows terminals - the scripts will still work correctly

### Port 8000 already in use
- Another program is using port 8000
- Stop SigmaSight with Ctrl+C and try again

---

## 🎯 Quick Commands Reference

```bash
# Navigate to project
cd C:\Projects\SigmaSight-BE\backend

# Start database
docker-compose up -d

# Stop database
docker-compose down

# Start SigmaSight
uv run python run.py

# Update code from GitHub
git pull

# Install/update dependencies
uv sync

# Set up database with Alembic migrations
uv run alembic upgrade head
# Or use the automated script:
uv run python scripts/setup_dev_database_alembic.py

# Seed demo data (use minimal setup to avoid Unicode issues)
set PYTHONIOENCODING=utf-8 && uv run python scripts/setup_minimal_demo.py

# Run authentication tests
set PYTHONIOENCODING=utf-8 && uv run python scripts/test_auth.py

# Run batch processing and generate reports
set PYTHONIOENCODING=utf-8 && uv run python scripts/batch_processing/run_batch.py

# List all portfolios with IDs
set PYTHONIOENCODING=utf-8 && uv run python scripts/list_portfolios.py

# Validate setup
set PYTHONIOENCODING=utf-8 && uv run python scripts/validate_setup.py
```

---

## 🔤 Windows Unicode/Encoding Notes

**Why do some commands use `set PYTHONIOENCODING=utf-8 &&`?**

Windows Command Prompt has encoding limitations that can cause Unicode errors when scripts try to display emojis or special characters. The Python scripts will work correctly, but you might see encoding errors in the output.

**Solutions:**
1. **Recommended**: Use the `set PYTHONIOENCODING=utf-8 &&` prefix shown in commands above
2. **Alternative**: Use PowerShell instead of Command Prompt
3. **Alternative**: Use Windows Terminal (available from Microsoft Store)

**If you see Unicode errors:**
- The error messages look scary but the scripts are still working
- Just ignore the encoding errors - they don't affect functionality
- The important part is that the scripts complete successfully

---

## 💡 Tips

- Keep Docker Desktop running in the background
- Create a desktop shortcut to `C:\Projects\SigmaSight-BE\backend`
- Save commonly used commands in a text file for easy copy-paste
- The database data persists even after stopping Docker
- Use PowerShell or Windows Terminal for better Unicode support
- All scripts work correctly even if you see encoding error messages

---

## 📞 Need Help?

If you get stuck:
1. Take a screenshot of any error messages
2. Note which step you're on
3. Contact the development team

For more advanced workflows including batch processing and report generation, see:
- [Complete Workflow Guide](../COMPLETE_WORKFLOW_GUIDE.md) - End-to-end workflow from setup to reports
- [Quick Start Windows](../QUICK_START_WINDOWS.md) - Essential commands reference

Remember: Everyone was a beginner once. Take your time and follow each step carefully!
