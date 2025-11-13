#!/usr/bin/env python3
"""
Pre-Publication Security Checklist
Run this script before pushing to GitHub to verify no sensitive data is included
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional, Dict, List, Set

# Define script_dir once at module level
script_dir = Path(__file__).parent.parent

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header(text):
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}{text}{RESET}")
    print(f"{BOLD}{'='*70}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓{RESET} {text}")

def print_error(text):
    print(f"{RED}✗{RESET} {text}")

def print_warning(text):
    print(f"{YELLOW}⚠{RESET} {text}")

def load_ansible_inventory() -> Optional[Dict[str, Set[str]]]:
    """
    Load Ansible inventory to extract real hostnames and IP addresses.
    Returns a dict with 'ips' and 'hostnames' sets, or None if not available.
    """
    try:
        # Try to load from .env first
        env_path = script_dir / '.env'
        ansible_inventory_path = None
        
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('ANSIBLE_INVENTORY_PATH='):
                        ansible_inventory_path = line.split('=', 1)[1].strip().strip('"\'')
                        break
        
        # If not in .env, check for default location
        if not ansible_inventory_path:
            default_path = script_dir / 'ansible_hosts.yml'
            if default_path.exists():
                ansible_inventory_path = str(default_path)
        
        if not ansible_inventory_path or not Path(ansible_inventory_path).exists():
            return None
        
        # Parse the YAML inventory
        import yaml
        with open(ansible_inventory_path, 'r') as f:
            inventory = yaml.safe_load(f)
        
        ips = set()
        hostnames = set()
        domains = set()
        
        def extract_host_info(data):
            """Recursively extract IPs and hostnames from inventory structure"""
            if isinstance(data, dict):
                # Check for hosts
                if 'hosts' in data:
                    for hostname, host_data in data['hosts'].items():
                        # Add hostname
                        hostnames.add(hostname)
                        
                        # Extract domain if hostname has one
                        if '.' in hostname:
                            domain = '.'.join(hostname.split('.')[1:])
                            if domain:
                                domains.add(domain)
                        
                        # Extract IP addresses
                        if isinstance(host_data, dict):
                            if 'ansible_host' in host_data:
                                ips.add(host_data['ansible_host'])
                            if 'ip' in host_data:
                                ips.add(host_data['ip'])
                            if 'address' in host_data:
                                ips.add(host_data['address'])
                
                # Recurse into children
                if 'children' in data:
                    for child in data['children'].values():
                        extract_host_info(child)
                
                # Recurse into any other dicts
                for value in data.values():
                    if isinstance(value, dict):
                        extract_host_info(value)
        
        # Start extraction from root
        if inventory:
            extract_host_info(inventory)
        
        return {
            'ips': ips,
            'hostnames': hostnames,
            'domains': domains
        }
        
    except ImportError:
        print_warning("PyYAML not installed - skipping Ansible inventory check")
        print_warning("Install with: pip install pyyaml")
        return None
    except Exception as e:
        print_warning(f"Could not load Ansible inventory: {e}")
        return None

def check_file_exists(filepath):
    """Check if a file exists"""
    return Path(filepath).exists()

def check_file_in_gitignore(filename, gitignore_content):
    """Check if a filename is in gitignore"""
    return filename in gitignore_content

def scan_for_ips(content, filename):
    """Scan content for private IP addresses"""
    # Pattern for private IP addresses
    ip_pattern = r'\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b'
    matches = re.findall(ip_pattern, content)
    
    # Filter out example IPs
    real_ips = [ip for ip in matches if not ip.startswith('192.168.1.') and not ip.startswith('10.0.1.')]
    return real_ips

def scan_for_api_keys(content, filename):
    """Scan content for potential API keys and sensitive data"""
    # Common patterns for API keys and sensitive data
    patterns = [
        r'api[_-]?key["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']',
        r'token["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']',
        r'password["\']?\s*[:=]\s*["\']([^"\']{8,})["\']',
        r'secret["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{16,})["\']',
        r'auth["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{16,})["\']',
        # GitHub URLs with actual usernames
        r'https://github\.com/([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)',
        # Notion URLs with actual IDs
        r'https://www\.notion\.so/([a-zA-Z0-9]{32})',
        # Email addresses
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    ]
    
    found_items = []
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            # Skip common example patterns
            if any(example in match.lower() for example in [
                'example.com', 'your-username', 'your-api-key', 
                'placeholder', 'template', 'sample', 'demo'
            ]):
                continue
            found_items.append(match)
    
    return found_items

def check_sensitive_files():
    """Check for sensitive files that shouldn't be committed"""
    print_header("Checking for Sensitive Files")
    
    issues = []
    
    # Read .gitignore
    gitignore_path = script_dir / '.gitignore'
    if gitignore_path.exists():
        with open(gitignore_path, 'r') as f:
            gitignore_content = f.read()
    else:
        print_error(".gitignore not found!")
        return False
    
    # Files that MUST be in .gitignore
    required_ignored = [
        '.env',
        'PROJECT_INSTRUCTIONS.md',
        'ansible_hosts.yml',
        'CLAUDE_CUSTOM.md'
    ]
    
    for filename in required_ignored:
        if check_file_in_gitignore(filename, gitignore_content):
            print_success(f"{filename} is in .gitignore")
        else:
            print_error(f"{filename} is NOT in .gitignore!")
            issues.append(f"{filename} must be added to .gitignore")
    
    # Files that should exist but not be committed
    sensitive_files = [
        ('.env', '.env should exist but not be committed'),
        ('PROJECT_INSTRUCTIONS.md', 'Your customized instructions (not the .example)'),
        ('ansible_hosts.yml', 'Your real inventory (not the .example)'),
        ('CLAUDE_CUSTOM.md', 'Your customized Claude guide with homelab-specific details')
    ]
    
    print()
    for filename, description in sensitive_files:
        filepath = script_dir / filename
        if filepath.exists():
            print_warning(f"{filename} exists - {description}")
            if not check_file_in_gitignore(filename, gitignore_content):
                issues.append(f"{filename} exists but is not in .gitignore!")
        else:
            print_success(f"{filename} does not exist (good for public repo)")
    
    # Example files that SHOULD exist
    print()
    example_files = [
        '.env.example',
        'PROJECT_INSTRUCTIONS.example.md',
        'ansible_hosts.example.yml',
        'CLAUDE_CUSTOM.example.md'
    ]
    
    for filename in example_files:
        if check_file_exists(script_dir / filename):
            print_success(f"{filename} exists")
        else:
            print_error(f"{filename} is missing!")
            issues.append(f"{filename} should be included as template")
    
    return len(issues) == 0

def check_documentation_files():
    """Check that documentation files exist"""
    print_header("Checking Documentation Files")
    
    issues = []
    
    required_docs = {
        'README.md': 'Main documentation',
        'SECURITY.md': 'Security guidelines',
        '.env.example': 'Environment variables template',
        'requirements.txt': 'Python dependencies',
        'PROJECT_INSTRUCTIONS.example.md': 'Claude instructions template',
        'ansible_hosts.example.yml': 'Ansible inventory template',
        'CLAUDE.md': 'Claude AI development guide (public)',
        'CLAUDE_CUSTOM.example.md': 'Claude customization template'
    }
    
    for filename, description in required_docs.items():
        filepath = script_dir / filename
        if filepath.exists():
            print_success(f"{filename} - {description}")
        else:
            print_error(f"{filename} is MISSING - {description}")
            issues.append(f"Missing {filename}")
    
    return len(issues) == 0

def scan_python_files():
    """Scan Python files for potential issues"""
    print_header("Scanning Python Files for Sensitive Data")
    
    issues = []
    
    python_files = list(script_dir.glob('*.py'))
    
    for py_file in python_files:
        if py_file.name == 'pre_publish_check.py':
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for hardcoded IPs (in non-example contexts)
            ips = scan_for_ips(content, py_file.name)
            if ips:
                print_warning(f"{py_file.name}: Found IP addresses - {', '.join(ips)}")
                print_warning("  → Verify these are example IPs only")
            
            # Check for potential API keys (basic check)
            keys = scan_for_api_keys(content, py_file.name)
            if keys:
                print_error(f"{py_file.name}: Potential API keys found!")
                issues.append(f"{py_file.name} may contain hardcoded credentials")
            
            # Check for common mistakes
            if 'your-api-key' not in content.lower() and 'api' in content.lower():
                if 'getenv' not in content and 'os.environ' not in content:
                    print_warning(f"{py_file.name}: Check that API keys use environment variables")
            
        except Exception as e:
            print_error(f"Error scanning {py_file.name}: {e}")
    
    if not issues:
        print_success("No obvious sensitive data found in Python files")
    
    return len(issues) == 0

def check_claude_custom_md():
    """Special check for CLAUDE_CUSTOM.md if it exists (should be gitignored)"""
    print_header("Checking CLAUDE_CUSTOM.md for Private Information")

    issues = []
    claude_custom_md = script_dir / 'CLAUDE_CUSTOM.md'

    if not claude_custom_md.exists():
        print_success("CLAUDE_CUSTOM.md does not exist (good for public repo)")
        return True

    # If it exists, check if it's gitignored
    gitignore_path = script_dir / '.gitignore'
    if gitignore_path.exists():
        with open(gitignore_path, 'r') as f:
            gitignore_content = f.read()

        if 'CLAUDE_CUSTOM.md' not in gitignore_content:
            print_error("CLAUDE_CUSTOM.md exists but is NOT in .gitignore!")
            issues.append("CLAUDE_CUSTOM.md must be added to .gitignore")
        else:
            print_success("CLAUDE_CUSTOM.md is properly gitignored")

    # If CLAUDE_CUSTOM.md exists, scan it for private information
    try:
        with open(claude_custom_md, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for real URLs
        github_urls = re.findall(r'https://github\.com/([a-zA-Z0-9_-]+)', content)
        notion_urls = re.findall(r'https://www\.notion\.so/([a-zA-Z0-9]{32})', content)

        if github_urls:
            real_github = [url for url in github_urls if url not in ['your-username', 'example-user']]
            if real_github:
                print_warning(f"CLAUDE_CUSTOM.md contains real GitHub URLs: {', '.join(real_github)}")

        if notion_urls:
            print_warning(f"CLAUDE_CUSTOM.md contains Notion URLs (likely private)")

        # Check for private IPs
        ips = scan_for_ips(content, 'CLAUDE_CUSTOM.md')
        if ips:
            print_warning(f"CLAUDE_CUSTOM.md contains IP addresses: {', '.join(ips)}")

        # Check for other sensitive data
        sensitive = scan_for_api_keys(content, 'CLAUDE_CUSTOM.md')
        if sensitive:
            print_warning(f"CLAUDE_CUSTOM.md may contain sensitive information")

    except Exception as e:
        print_error(f"Error scanning CLAUDE_CUSTOM.md: {e}")

    return len(issues) == 0

def check_claude_md_public():
    """Check that CLAUDE.md is public-ready (no homelab-specific details)"""
    print_header("Checking CLAUDE.md is Public-Ready")

    issues = []
    claude_md = script_dir / 'CLAUDE.md'

    if not claude_md.exists():
        print_error("CLAUDE.md does not exist (should be committed to public repo)")
        return False

    print_success("CLAUDE.md exists")

    # Scan for common homelab-specific patterns
    try:
        with open(claude_md, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for specific server names that shouldn't be in public version
        homelab_patterns = [
            (r'\bDell-Server\b', 'Dell-Server'),
            (r'\bHL16\b', 'HL16'),
            (r'\bServer-01\b', 'Server-01'),
        ]

        for pattern, name in homelab_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                print_error(f"CLAUDE.md contains homelab-specific reference: {name}")
                issues.append(f"Found {name} in CLAUDE.md")

        # Check for private IPs (should only have example IPs)
        ips = scan_for_ips(content, 'CLAUDE.md')
        suspicious_ips = [ip for ip in ips if not (
            ip.startswith('192.168.1.') or
            ip.startswith('10.0.1.') or
            ip.startswith('192.0.2.')  # RFC 5737 documentation range
        )]

        if suspicious_ips:
            print_error(f"CLAUDE.md contains non-example IPs: {', '.join(suspicious_ips)}")
            issues.append("CLAUDE.md contains real IP addresses")

        if not issues:
            print_success("CLAUDE.md appears public-ready (no homelab-specific details found)")

    except Exception as e:
        print_error(f"Error scanning CLAUDE.md: {e}")
        return False

    return len(issues) == 0

def scan_markdown_files():
    """Scan markdown files for real infrastructure details"""
    print_header("Scanning Markdown Files for Infrastructure Details")
    
    issues = []
    
    # Files to check (excluding the customized versions)
    md_files = [
        'README.md',
        'SECURITY.md',
        'PROJECT_INSTRUCTIONS.example.md',
        'ansible_hosts.example.yml'
    ]
    
    for filename in md_files:
        filepath = script_dir / filename
        if not filepath.exists():
            continue
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for private IPs that aren't examples
            ips = scan_for_ips(content, filename)
            suspicious_ips = [ip for ip in ips if not (
                ip.startswith('192.168.1.') or 
                ip.startswith('10.0.1.') or
                ip.startswith('172.16.')
            )]
            
            if suspicious_ips:
                print_error(f"{filename}: Found non-example IPs: {', '.join(suspicious_ips)}")
                issues.append(f"{filename} contains real IP addresses")
            else:
                print_success(f"{filename}: No real IP addresses found")
            
            # Check for common domain patterns
            if '.local' in content or 'home.' in content:
                # Count occurrences
                local_count = content.count('.local')
                home_count = content.count('home.')
                if filename == 'README.md' and (local_count > 3 or home_count > 0):
                    print_warning(f"{filename}: Contains .local or home. domains ({local_count + home_count} times)")
                    print_warning("  → Verify these are examples, not your real domains")
            
        except Exception as e:
            print_error(f"Error scanning {filename}: {e}")
    
    return len(issues) == 0

def scan_for_real_infrastructure(inventory_data: Optional[Dict[str, Set[str]]]):
    """
    Scan all code files for references to real infrastructure from Ansible inventory.
    This is a context-aware check that knows YOUR specific hostnames and IPs.
    """
    if not inventory_data:
        print_header("Scanning for Real Infrastructure Details")
        print_warning("Ansible inventory not found - skipping context-aware infrastructure scan")
        print_warning("To enable: Set ANSIBLE_INVENTORY_PATH in .env or create ansible_hosts.yml")
        return True
    
    print_header("Scanning for Real Infrastructure Details (Context-Aware)")
    print(f"Loaded {len(inventory_data['ips'])} IP addresses, " +
          f"{len(inventory_data['hostnames'])} hostnames, " +
          f"{len(inventory_data['domains'])} domains from inventory")
    
    issues = []
    
    # Files to check (exclude sensitive files that should already be gitignored)
    files_to_check = []
    
    # Python files
    files_to_check.extend([f for f in script_dir.glob('*.py') 
                          if f.name != 'pre_publish_check.py'])
    
    # Markdown files (all public ones - exclude gitignored CLAUDE_CUSTOM.md and PROJECT_INSTRUCTIONS.md)
    all_md_files = script_dir.glob('*.md')
    gitignored_md = {'CLAUDE_CUSTOM.md', 'PROJECT_INSTRUCTIONS.md'}
    for md_file in all_md_files:
        if md_file.name not in gitignored_md:
            files_to_check.append(md_file)
    
    # YAML example files
    files_to_check.extend(script_dir.glob('*.example.yml'))
    files_to_check.extend(script_dir.glob('*.example.yaml'))
    
    for file_path in files_to_check:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            found_issues = []
            
            # Check for real IP addresses
            for ip in inventory_data['ips']:
                if ip in content:
                    # Make sure it's not in a comment explaining what to replace
                    lines_with_ip = [line for line in content.split('\n') if ip in line]
                    # Filter out comments that are clearly examples
                    real_occurrences = [line for line in lines_with_ip 
                                       if not any(keyword in line.lower() 
                                                 for keyword in ['example', 'replace', 'your-ip', 
                                                               'placeholder', 'template'])]
                    if real_occurrences:
                        found_issues.append(f"Real IP address: {ip}")
            
            # Check for real hostnames
            for hostname in inventory_data['hostnames']:
                # Use word boundaries to avoid false positives
                pattern = r'\b' + re.escape(hostname) + r'\b'
                if re.search(pattern, content, re.IGNORECASE):
                    # Check if it's in a comment/example context
                    lines_with_hostname = [line for line in content.split('\n') 
                                          if re.search(pattern, line, re.IGNORECASE)]
                    real_occurrences = [line for line in lines_with_hostname 
                                       if not any(keyword in line.lower() 
                                                 for keyword in ['example', 'replace', 'your-host',
                                                               'placeholder', 'template', 'e.g.', 'i.e.'])]
                    if real_occurrences:
                        found_issues.append(f"Real hostname: {hostname}")
            
            # Check for real domain names (be careful with common domains)
            for domain in inventory_data['domains']:
                # Skip very common domains that might be coincidental
                if domain in ['local', 'com', 'net', 'org', 'home']:
                    continue
                pattern = r'\b' + re.escape(domain) + r'\b'
                if re.search(pattern, content, re.IGNORECASE):
                    lines_with_domain = [line for line in content.split('\n') 
                                        if re.search(pattern, line, re.IGNORECASE)]
                    real_occurrences = [line for line in lines_with_domain 
                                       if not any(keyword in line.lower() 
                                                 for keyword in ['example', 'replace', 'your-domain',
                                                               'placeholder', 'template'])]
                    if real_occurrences:
                        found_issues.append(f"Real domain: {domain}")
            
            if found_issues:
                print_error(f"{file_path.name}: Found real infrastructure details!")
                for issue in set(found_issues):  # Use set to avoid duplicates
                    print(f"  → {issue}")
                issues.append(f"{file_path.name} contains real infrastructure details")
            else:
                print_success(f"{file_path.name}: No real infrastructure details found")
                
        except Exception as e:
            print_warning(f"Error scanning {file_path.name}: {e}")
    
    if issues:
        print()
        print_error("❌ Found references to real infrastructure in files that will be committed!")
        print_error("These files should only contain example/placeholder data.")
    else:
        print()
        print_success("✅ No real infrastructure details found in public files")
    
    return len(issues) == 0

def final_reminders():
    """Print final reminders"""
    print_header("Final Pre-Publication Checklist")
    
    reminders = [
        "Review git history for accidentally committed secrets",
        "Ensure .env is NOT in git history (git rm --cached .env if needed)",
        "Ensure ansible_hosts.yml is NOT in git history (if you have one)",
        "Test with a fresh clone in a new directory",
        "Verify .gitignore is working (git status should not show sensitive files)",
        "Double-check that PROJECT_INSTRUCTIONS.md and CLAUDE_CUSTOM.md are gitignored",
        "Verify CLAUDE.md is public-ready (no homelab-specific details)",
        "Verify CLAUDE_CUSTOM.example.md exists and contains placeholder data only",
        "Context-aware check scanned for YOUR real IPs/hostnames (if inventory found)",
        "Review all commits for sensitive data before pushing",
        "Consider using 'git secrets' or similar tools",
        "Update GitHub repository description and tags",
        "Add topics/tags to GitHub repo for discoverability",
        "Consider adding LICENSE file if not present"
    ]
    
    for i, reminder in enumerate(reminders, 1):
        print(f"  {i}. {reminder}")
    
    print()

def main():
    """Run all checks"""
    print(f"{BOLD}Homelab MCP - Pre-Publication Security Check{RESET}")
    print(f"{BOLD}{'='*70}{RESET}")
    
    print(f"Checking directory: {script_dir}\n")
    
    # Load Ansible inventory for context-aware checking
    inventory_data = load_ansible_inventory()
    if inventory_data:
        print(f"✓ Loaded Ansible inventory with {len(inventory_data['ips'])} IPs, " +
              f"{len(inventory_data['hostnames'])} hosts, {len(inventory_data['domains'])} domains\n")
    
    all_passed = True
    
    # Run checks
    if not check_sensitive_files():
        all_passed = False

    if not check_documentation_files():
        all_passed = False

    if not check_claude_custom_md():
        all_passed = False

    if not check_claude_md_public():
        all_passed = False

    if not scan_python_files():
        all_passed = False
    
    if not scan_markdown_files():
        all_passed = False
    
    # NEW: Context-aware infrastructure scanning
    if not scan_for_real_infrastructure(inventory_data):
        all_passed = False
    
    # Final summary
    print_header("Summary")
    
    if all_passed:
        print_success("All checks passed! ✨")
        print_success("Review the warnings above and the final checklist before publishing.")
    else:
        print_error("Some checks FAILED! ⚠️")
        print_error("Fix the issues above before publishing to GitHub.")
    
    final_reminders()
    
    # Exit code
    sys.exit(0 if all_passed else 1)

if __name__ == '__main__':
    main()
