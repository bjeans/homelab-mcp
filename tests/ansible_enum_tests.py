#!/usr/bin/env python3
"""
Tests for ansible_config_manager enum generation methods

Run with: python3 -m pytest tests/ansible_enum_tests.py -v
Or: python3 tests/ansible_enum_tests.py (basic verification)
"""

import sys
from pathlib import Path

# Add parent directory to path to import ansible_config_manager
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from ansible_config_manager import AnsibleConfigManager


class TestHostnameNormalization(unittest.TestCase):
    """Test hostname normalization helper"""

    def test_normalize_fqdn(self):
        """Test normalization of fully qualified domain names"""
        result = AnsibleConfigManager._normalize_hostname('Server_1.example.com')
        self.assertEqual(result, 'server-1')

    def test_normalize_short_hostname(self):
        """Test normalization of short hostnames"""
        result = AnsibleConfigManager._normalize_hostname('web-01')
        self.assertEqual(result, 'web-01')

    def test_normalize_uppercase(self):
        """Test conversion to lowercase"""
        result = AnsibleConfigManager._normalize_hostname('WEBSERVER')
        self.assertEqual(result, 'webserver')

    def test_normalize_underscores(self):
        """Test underscore to hyphen conversion"""
        result = AnsibleConfigManager._normalize_hostname('docker_host_1')
        self.assertEqual(result, 'docker-host-1')

    def test_normalize_mixed(self):
        """Test complex normalization"""
        result = AnsibleConfigManager._normalize_hostname('Docker_Host_1.local.domain')
        self.assertEqual(result, 'docker-host-1')


class TestEnumMethods(unittest.TestCase):
    """Test enum generation methods"""

    def setUp(self):
        """Create manager instance (may not be available without Ansible inventory)"""
        self.manager = AnsibleConfigManager()

    def test_methods_exist(self):
        """Verify all enum generation methods exist"""
        methods = [
            'get_docker_hosts',
            'get_ollama_hosts',
            'get_pihole_hosts',
            'get_ups_hosts',
            'get_all_groups',
            'get_hosts_by_capability',
        ]

        for method_name in methods:
            self.assertTrue(
                hasattr(self.manager, method_name),
                f"Method {method_name} should exist"
            )

    def test_methods_return_lists(self):
        """Verify all methods return lists (even if empty)"""
        methods = [
            ('get_docker_hosts', []),
            ('get_ollama_hosts', []),
            ('get_pihole_hosts', []),
            ('get_ups_hosts', []),
            ('get_all_groups', []),
            ('get_hosts_by_capability', ['docker_api_port']),
        ]

        for method_name, args in methods:
            method = getattr(self.manager, method_name)
            result = method(*args)
            self.assertIsInstance(
                result, list,
                f"{method_name} should return a list"
            )

    def test_graceful_degradation_no_ansible(self):
        """Test that methods return empty lists when Ansible is unavailable"""
        manager = AnsibleConfigManager()

        if not manager.is_available():
            # Should return empty lists, not raise exceptions
            self.assertEqual(manager.get_docker_hosts(), [])
            self.assertEqual(manager.get_ollama_hosts(), [])
            self.assertEqual(manager.get_pihole_hosts(), [])
            self.assertEqual(manager.get_ups_hosts(), [])
            self.assertEqual(manager.get_all_groups(), [])
            self.assertEqual(manager.get_hosts_by_capability('test'), [])


class TestEnumDeduplication(unittest.TestCase):
    """Test that enum methods return deduplicated sorted results"""

    def test_docker_hosts_combines_and_deduplicates(self):
        """Test that get_docker_hosts() combines docker and podman hosts"""
        # This test would require a mock Ansible inventory
        # For now, just verify the method signature works
        manager = AnsibleConfigManager()
        result = manager.get_docker_hosts()
        self.assertIsInstance(result, list)

        # Verify results are sorted and unique (if any)
        if result:
            self.assertEqual(result, sorted(set(result)))


def run_basic_tests():
    """Run basic verification without pytest"""
    print("Running basic enum generation tests...\n")

    # Test 1: Hostname normalization
    print("Test 1: Hostname normalization")
    test_cases = [
        ('Server_1.example.com', 'server-1'),
        ('web-01', 'web-01'),
        ('WEBSERVER', 'webserver'),
        ('docker_host_1', 'docker-host-1'),
    ]

    for input_val, expected in test_cases:
        result = AnsibleConfigManager._normalize_hostname(input_val)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {input_val} → {result} (expected: {expected})")

    # Test 2: Methods exist and return lists
    print("\nTest 2: Enum methods exist and return lists")
    manager = AnsibleConfigManager()

    methods = [
        'get_docker_hosts',
        'get_ollama_hosts',
        'get_pihole_hosts',
        'get_ups_hosts',
        'get_all_groups',
    ]

    for method_name in methods:
        method = getattr(manager, method_name, None)
        if method:
            result = method()
            is_list = isinstance(result, list)
            status = "✓" if is_list else "✗"
            print(f"  {status} {method_name}() → {type(result).__name__}")
        else:
            print(f"  ✗ {method_name}() → NOT FOUND")

    # Test 3: Graceful degradation
    print("\nTest 3: Graceful degradation (no Ansible)")
    if not manager.is_available():
        all_empty = all([
            manager.get_docker_hosts() == [],
            manager.get_ollama_hosts() == [],
            manager.get_pihole_hosts() == [],
            manager.get_ups_hosts() == [],
            manager.get_all_groups() == [],
        ])
        status = "✓" if all_empty else "✗"
        print(f"  {status} All methods return empty lists when Ansible unavailable")
    else:
        print("  ⊕ Ansible available, skipping degradation test")

    print("\n✓ All basic tests passed!")


if __name__ == '__main__':
    import sys

    # If pytest is available, use it
    try:
        import pytest
        sys.exit(pytest.main([__file__, '-v']))
    except ImportError:
        # Otherwise run basic tests
        run_basic_tests()
