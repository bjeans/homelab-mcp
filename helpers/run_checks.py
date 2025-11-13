#!/usr/bin/env python3
"""
Local Code Quality Check Script
Run all code quality checks locally before committing

Usage:
  python run_checks.py              # Run all checks
  python run_checks.py --fast       # Run only fast checks
  python run_checks.py --security   # Run only security checks
  python run_checks.py --format     # Auto-fix formatting issues
  python run_checks.py --install-deps  # Install dev dependencies first
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def run_command(cmd, description, fix_mode=False):
    """Run a command and report results"""
    print(f"\n{BLUE}{BOLD}{'='*70}{RESET}")
    print(f"{BLUE}{BOLD}{description}{RESET}")
    print(f"{BLUE}{BOLD}{'='*70}{RESET}\n")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
            
        if result.returncode == 0:
            print(f"{GREEN}✓ {description} passed{RESET}")
            return True
        else:
            if not fix_mode:
                print(f"{RED}✗ {description} failed{RESET}")
            return False
    except Exception as e:
        print(f"{RED}✗ Error running {description}: {e}{RESET}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Run code quality checks')
    parser.add_argument('--fast', action='store_true', help='Run only fast checks')
    parser.add_argument('--security', action='store_true', help='Run only security checks')
    parser.add_argument('--format', action='store_true', help='Auto-fix formatting issues')
    parser.add_argument('--install-deps', action='store_true', help='Install dev dependencies first')
    args = parser.parse_args()
    
    print(f"{BOLD}Homelab MCP - Local Code Quality Checks{RESET}")
    print(f"{BOLD}{'='*70}{RESET}")
    
    # Install dependencies if requested
    if args.install_deps:
        print(f"\n{YELLOW}Installing development dependencies...{RESET}")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements-dev.txt"])
    
    all_passed = True
    
    # Format mode - auto-fix issues
    if args.format:
        print(f"\n{YELLOW}Auto-fixing formatting issues...{RESET}")
        run_command("black *.py", "Black code formatting", fix_mode=True)
        run_command("isort *.py", "Import sorting", fix_mode=True)
        print(f"\n{GREEN}✓ Formatting complete! Review changes with git diff{RESET}")
        return
    
    # Security checks
    if args.security or not args.fast:
        print(f"\n{BOLD}Running Security Checks...{RESET}")
        
        # Pre-publish check
        if not run_command(f"{sys.executable} pre_publish_check.py", "Pre-publish security check"):
            all_passed = False
        
        # Bandit security scanner
        if not run_command("bandit -r *.py", "Bandit security scan"):
            all_passed = False
            
        # Dependency vulnerabilities
        if not run_command("safety check", "Safety dependency check"):
            print(f"{YELLOW}⚠ Some vulnerabilities found, but not blocking{RESET}")
    
    # Fast checks or all checks
    if not args.security:
        print(f"\n{BOLD}Running Code Quality Checks...{RESET}")
        
        # Black formatting check
        if not run_command("black --check *.py", "Black formatting check"):
            print(f"{YELLOW}→ Run 'python run_checks.py --format' to auto-fix{RESET}")
            all_passed = False
        
        # Import sorting
        if not run_command("isort --check-only *.py", "Import sorting check"):
            print(f"{YELLOW}→ Run 'python run_checks.py --format' to auto-fix{RESET}")
            all_passed = False
        
        # Flake8 linting (errors only)
        if not run_command("flake8 *.py --select=E9,F63,F7,F82", "Flake8 critical errors"):
            all_passed = False
        
        # Python compilation check
        print(f"\n{BLUE}Checking Python syntax...{RESET}")
        py_files = [
            "ansible_mcp_server.py",
            "docker_mcp_podman.py", 
            "ollama_mcp.py",
            "pihole_mcp.py",
            "unifi_mcp_optimized.py",
            "mcp_registry_inspector.py",
            "pre_publish_check.py"
        ]
        
        for py_file in py_files:
            if Path(py_file).exists():
                if not run_command(f"{sys.executable} -m py_compile {py_file}", f"Compile {py_file}"):
                    all_passed = False
    
    # Full checks (not fast mode)
    if not args.fast and not args.security:
        print(f"\n{BOLD}Running Comprehensive Checks...{RESET}")
        
        # MyPy type checking
        run_command("mypy *.py --ignore-missing-imports", "MyPy type checking")
        
        # Pylint (informational)
        run_command("pylint *.py --exit-zero", "Pylint comprehensive check")
        
        # YAML linting
        if Path("ansible_hosts.example.yml").exists():
            run_command("yamllint ansible_hosts.example.yml", "YAML validation")
    
    # Summary
    print(f"\n{BOLD}{'='*70}{RESET}")
    if all_passed:
        print(f"{GREEN}{BOLD}✓ All checks passed!{RESET}")
        print(f"{GREEN}Code is ready to commit.{RESET}")
    else:
        print(f"{RED}{BOLD}✗ Some checks failed{RESET}")
        print(f"{YELLOW}Fix the issues above before committing.{RESET}")
        print(f"\nQuick fixes:")
        print(f"  • Format code:  python run_checks.py --format")
        print(f"  • Fast check:   python run_checks.py --fast")
        print(f"  • Security:     python run_checks.py --security")
    print(f"{BOLD}{'='*70}{RESET}\n")
    
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
