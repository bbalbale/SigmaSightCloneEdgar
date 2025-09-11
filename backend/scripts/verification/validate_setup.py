#!/usr/bin/env python3
"""
Universal Setup Validation Script
Cross-platform validation that works on Windows, Mac, and Linux
"""
import os
import sys
import subprocess
import platform
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_command(cmd: List[str], capture_output=True) -> Tuple[bool, str]:
    """Run a command and return (success, output)"""
    try:
        if capture_output:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0, result.stdout + result.stderr
        else:
            result = subprocess.run(cmd, timeout=30)
            return result.returncode == 0, ""
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)

def check_python() -> Tuple[bool, str]:
    """Check Python version"""
    success, output = run_command([sys.executable, "--version"])
    if success:
        version = output.strip()
        # Check if version is 3.11+
        try:
            version_parts = version.split()[1].split(".")
            major, minor = int(version_parts[0]), int(version_parts[1])
            if major >= 3 and minor >= 11:
                return True, f"✅ {version}"
            else:
                return False, f"❌ {version} (need Python 3.11+)"
        except:
            return False, f"❌ Could not parse version: {version}"
    return False, "❌ Python not found"

def check_uv() -> Tuple[bool, str]:
    """Check UV package manager"""
    success, output = run_command(["uv", "--version"])
    if success:
        return True, f"✅ {output.strip()}"
    return False, "❌ UV not installed"

def check_docker() -> Tuple[bool, str]:
    """Check Docker installation and status"""
    # Check if docker command exists
    success, output = run_command(["docker", "--version"])
    if not success:
        return False, "❌ Docker not installed"
    
    docker_version = output.strip()
    
    # Check if Docker daemon is running
    success, output = run_command(["docker", "ps"])
    if success:
        return True, f"✅ {docker_version} (running)"
    else:
        return False, f"⚠️ {docker_version} (daemon not running)"

def check_database() -> Tuple[bool, str]:
    """Check PostgreSQL container"""
    success, output = run_command(["docker", "ps", "--filter", "name=postgres", "--format", "table {{.Names}}\t{{.Status}}"])
    if success and "postgres" in output:
        lines = output.strip().split('\n')
        if len(lines) > 1:  # Header + at least one container
            status_line = lines[1]
            # Handle both tab and space separators
            parts = status_line.split('\t') if '\t' in status_line else status_line.split()
            if len(parts) >= 2:
                status = parts[1] if '\t' in status_line else ' '.join(parts[1:])
                if "Up" in status:
                    return True, f"✅ PostgreSQL container running ({status})"
                else:
                    return False, f"❌ PostgreSQL container not running ({status})"
            elif "Up" in status_line:
                return True, f"✅ PostgreSQL container running"
    return False, "❌ PostgreSQL container not found"

def check_env_file() -> Tuple[bool, str]:
    """Check .env file exists and has required keys"""
    env_path = Path(".env")
    if not env_path.exists():
        return False, "❌ .env file not found"
    
    try:
        with open(env_path) as f:
            content = f.read()
        
        required_keys = ["DATABASE_URL", "SECRET_KEY", "POLYGON_API_KEY"]
        missing_keys = []
        
        for key in required_keys:
            if f"{key}=" not in content:
                missing_keys.append(key)
        
        if missing_keys:
            return False, f"❌ Missing keys: {', '.join(missing_keys)}"
        
        return True, "✅ .env file configured"
    except Exception as e:
        return False, f"❌ Error reading .env: {e}"

def check_virtual_env() -> Tuple[bool, str]:
    """Check virtual environment"""
    venv_path = Path(".venv")
    if not venv_path.exists():
        return False, "❌ Virtual environment not found"
    
    # Check if key packages are installed
    success, output = run_command(["uv", "pip", "list"])
    if success:
        if "fastapi" in output.lower():
            return True, "✅ Virtual environment with dependencies"
        else:
            return False, "❌ Virtual environment missing dependencies"
    
    return False, "❌ Could not check virtual environment"

def check_api_server() -> Tuple[bool, str]:
    """Check if API server is responding"""
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                return True, "✅ API server responding"
        return False, f"❌ API server unhealthy (status: {response.status_code})"
    except ImportError:
        # Fallback to curl if requests not available
        success, output = run_command(["curl", "-s", "http://localhost:8000/health"])
        if success and "healthy" in output:
            return True, "✅ API server responding"
        return False, "❌ API server not responding"
    except Exception as e:
        return False, f"❌ Cannot reach API server: {e}"

def check_demo_users() -> Tuple[bool, str]:
    """Check if demo users exist"""
    try:
        # Try to import and check database
        from dotenv import load_dotenv
        load_dotenv()
        
        import asyncio
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        async def check_users():
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                return False, "❌ DATABASE_URL not set"
            
            engine = create_async_engine(database_url)
            try:
                async with engine.connect() as conn:
                    result = await conn.execute(text("SELECT COUNT(*) FROM users WHERE email LIKE '%@sigmasight.com'"))
                    count = result.scalar()
                    if count >= 3:
                        return True, f"✅ {count} demo users found"
                    else:
                        return False, f"❌ Only {count} demo users found (need 3)"
            except Exception as e:
                return False, f"❌ Database error: {e}"
            finally:
                await engine.dispose()
        
        return asyncio.run(check_users())
        
    except Exception as e:
        return False, f"❌ Error checking demo users: {e}"

def main():
    """Main validation function"""
    print("🔍 SigmaSight Setup Validation")
    print("=" * 50)
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Working Directory: {os.getcwd()}")
    print()
    
    # Define all checks
    checks = [
        ("Python 3.11+", check_python),
        ("UV Package Manager", check_uv),
        ("Docker", check_docker),
        ("PostgreSQL Database", check_database),
        ("Environment File", check_env_file),
        ("Virtual Environment", check_virtual_env),
        ("API Server", check_api_server),
        ("Demo Users", check_demo_users),
    ]
    
    # Run all checks
    results = []
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        print(f"Checking {name}...", end=" ")
        try:
            success, message = check_func()
            results.append((name, success, message))
            if success:
                passed += 1
            print(message)
        except Exception as e:
            message = f"❌ Check failed: {e}"
            results.append((name, False, message))
            print(message)
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Validation Summary: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All checks passed! SigmaSight is ready to use.")
        print("\n💡 Next steps:")
        print("   • Visit http://localhost:8000/docs for API documentation")
        print("   • Use demo credentials: demo_individual@sigmasight.com / demo12345")
        return 0
    else:
        print(f"⚠️ {total - passed} issues need to be resolved:")
        for name, success, message in results:
            if not success:
                print(f"   • {name}: {message}")
        
        print("\n🔧 Suggested fixes:")
        if any("Docker" in r[0] and not r[1] for r in results):
            print("   • Start Docker Desktop and wait for it to fully load")
        if any("PostgreSQL" in r[0] and not r[1] for r in results):
            print("   • Run: docker-compose up -d")
        if any("API Server" in r[0] and not r[1] for r in results):
            print("   • Run: uv run uvicorn app.main:app --reload")
        if any("Demo Users" in r[0] and not r[1] for r in results):
            print("   • Run: uv run python scripts/setup_minimal_demo.py")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())