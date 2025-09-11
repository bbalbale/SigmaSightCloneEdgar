#!/usr/bin/env python3
"""
Setup verification script for SigmaSight Backend
This script verifies that the local environment is properly configured
"""
import sys
import subprocess
import platform
import json
from pathlib import Path
import httpx
import time

# Configure UTF-8 output handling for Windows
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_step(step, status="RUNNING"):
    """Print a step with status"""
    status_symbols = {
        "RUNNING": "⏳",
        "PASS": "✅",
        "FAIL": "❌",
        "WARN": "⚠️"
    }
    print(f"{status_symbols.get(status, '•')} {step}")

def run_command(cmd, capture_output=True):
    """Run a command and return result"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=capture_output, 
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def check_python_version():
    """Check Python version"""
    print_step("Checking Python version", "RUNNING")
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print_step(f"Python {version.major}.{version.minor}.{version.micro} - OK", "PASS")
        return True
    else:
        print_step(f"Python {version.major}.{version.minor}.{version.micro} - Need 3.11+", "FAIL")
        return False

def check_uv_installation():
    """Check if UV is installed"""
    print_step("Checking UV package manager", "RUNNING")
    success, stdout, stderr = run_command("uv --version")
    if success:
        version = stdout.strip()
        print_step(f"UV {version} - OK", "PASS")
        return True
    else:
        print_step("UV not found - Need to install", "FAIL")
        print("  Install UV: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False

def check_project_structure():
    """Check if project structure is correct"""
    print_step("Checking project structure", "RUNNING")
    
    required_files = [
        "pyproject.toml",
        "app/main.py",
        "app/config.py",
        "run.py",
        ".env.example"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if not missing_files:
        print_step("All required files present - OK", "PASS")
        return True
    else:
        print_step(f"Missing files: {', '.join(missing_files)}", "FAIL")
        return False

def check_environment_file():
    """Check if .env file exists"""
    print_step("Checking environment configuration", "RUNNING")
    
    if Path(".env").exists():
        print_step(".env file exists - OK", "PASS")
        return True
    else:
        print_step(".env file missing - Need to copy from .env.example", "WARN")
        print("  Run: cp .env.example .env")
        return False

def check_dependencies():
    """Check if dependencies are installed"""
    print_step("Checking dependencies installation", "RUNNING")
    
    # Check if .venv exists
    if not Path(".venv").exists():
        print_step("Virtual environment not found", "FAIL")
        print("  Run: uv sync")
        return False
    
    # Try to import key dependencies
    success, stdout, stderr = run_command("uv run python -c 'import fastapi, uvicorn, sqlalchemy; print(\"Dependencies OK\")'")
    if success:
        print_step("Dependencies installed - OK", "PASS")
        return True
    else:
        print_step("Dependencies missing or broken", "FAIL")
        print("  Run: uv sync")
        return False

def check_server_startup():
    """Check if server can start"""
    print_step("Testing server startup", "RUNNING")
    
    # Start server in background
    print("  Starting server...")
    process = subprocess.Popen(
        ["uv", "run", "python", "run.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to start
    time.sleep(5)
    
    try:
        # Test if server is responding
        response = httpx.get("http://localhost:8000/health", timeout=10)
        if response.status_code == 200:
            print_step("Server started successfully - OK", "PASS")
            success = True
        else:
            print_step(f"Server responded with status {response.status_code}", "FAIL")
            success = False
    except Exception as e:
        print_step(f"Server connection failed: {e}", "FAIL")
        success = False
    finally:
        # Stop the server
        process.terminate()
        process.wait(timeout=5)
    
    return success

def test_api_endpoints():
    """Test key API endpoints"""
    print_step("Testing API endpoints", "RUNNING")
    
    # Start server for testing
    process = subprocess.Popen(
        ["uv", "run", "python", "run.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    time.sleep(5)
    
    endpoints_to_test = [
        ("GET", "/", "Root endpoint"),
        ("GET", "/health", "Health check"),
        ("GET", "/docs", "API documentation"),
        ("POST", "/api/v1/auth/login", "Auth login"),
        ("GET", "/api/v1/portfolio/", "Portfolio endpoint"),
        ("GET", "/api/v1/risk/greeks", "Risk Greeks endpoint")
    ]
    
    all_passed = True
    
    try:
        for method, endpoint, description in endpoints_to_test:
            try:
                if method == "GET":
                    response = httpx.get(f"http://localhost:8000{endpoint}", timeout=10)
                else:
                    response = httpx.post(f"http://localhost:8000{endpoint}", timeout=10)
                
                if response.status_code == 200:
                    print_step(f"{description} - OK", "PASS")
                else:
                    print_step(f"{description} - Status {response.status_code}", "FAIL")
                    all_passed = False
            except Exception as e:
                print_step(f"{description} - Error: {e}", "FAIL")
                all_passed = False
    finally:
        process.terminate()
        process.wait(timeout=5)
    
    return all_passed

def generate_system_info():
    """Generate system information"""
    print_header("SYSTEM INFORMATION")
    
    info = {
        "OS": platform.system(),
        "OS Version": platform.version(),
        "Architecture": platform.machine(),
        "Python Version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "Working Directory": str(Path.cwd())
    }
    
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # Check UV version
    success, stdout, stderr = run_command("uv --version")
    if success:
        print(f"  UV Version: {stdout.strip()}")

def main():
    """Main verification function"""
    print_header("SIGMASIGHT BACKEND SETUP VERIFICATION")
    print("This script will verify your local development environment")
    
    # Generate system info
    generate_system_info()
    
    # Run all checks
    print_header("RUNNING VERIFICATION CHECKS")
    
    checks = [
        ("Python Version", check_python_version),
        ("UV Installation", check_uv_installation),
        ("Project Structure", check_project_structure),
        ("Environment File", check_environment_file),
        ("Dependencies", check_dependencies),
        ("Server Startup", check_server_startup),
        ("API Endpoints", test_api_endpoints)
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print_step(f"{check_name} - Error: {e}", "FAIL")
            results.append((check_name, False))
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "PASS" if result else "FAIL"
        print_step(f"{check_name}", status)
    
    print(f"\nResults: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All checks passed! Your environment is ready for development.")
        print("You can now start the server with: uv run python run.py")
        print("API will be available at: http://localhost:8000")
    else:
        print(f"\n⚠️  {total - passed} checks failed. Please fix the issues above.")
        print("Refer to the README.md for detailed setup instructions.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
