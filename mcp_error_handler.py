#!/usr/bin/env python3
"""
MCP Error Handler Utility
Provides centralized error handling and user-friendly error messages for MCP servers
"""

import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any


class MCPErrorClassifier:
    """Classifies and formats errors with actionable remediation guidance"""

    # HTTP status code mappings
    HTTP_ERROR_MESSAGES = {
        400: {
            "type": "Bad Request",
            "description": "The request was malformed or invalid",
            "remediation": "Check the request parameters and ensure they match the API specification.",
        },
        401: {
            "type": "Authentication Failed",
            "description": "Invalid or missing credentials",
            "remediation": "Verify your API key/password is correct. Check the environment variable is set properly in .env file.",
        },
        403: {
            "type": "Authorization Failed",
            "description": "Valid credentials but insufficient permissions",
            "remediation": "Ensure the API key/account has the required permissions for this operation.",
        },
        404: {
            "type": "Not Found",
            "description": "The requested resource or endpoint does not exist",
            "remediation": "Verify the endpoint URL and resource identifier are correct.",
        },
        429: {
            "type": "Rate Limited",
            "description": "Too many requests sent in a given timeframe",
            "remediation": "Wait a few moments before retrying. Consider increasing cache duration.",
        },
        500: {
            "type": "Server Error",
            "description": "The service encountered an internal error",
            "remediation": "Check the service logs for details. The service may need to be restarted.",
        },
        502: {
            "type": "Bad Gateway",
            "description": "The service received an invalid response from upstream",
            "remediation": "Check if upstream services are running. Verify network connectivity between services.",
        },
        503: {
            "type": "Service Unavailable",
            "description": "The service is temporarily unavailable",
            "remediation": "Check if the service is running. Try: systemctl status <service-name>",
        },
        504: {
            "type": "Gateway Timeout",
            "description": "The service did not respond in time",
            "remediation": "The service may be overloaded. Check service health and consider increasing timeout values.",
        },
    }

    # Common error patterns in subprocess/API responses
    ERROR_PATTERNS = {
        "invalid_api_key": {
            "patterns": [
                r"invalid.*api.*key",
                r"unauthorized.*api.*key",
                r"authentication.*failed",
                r"invalid.*credentials",
            ],
            "type": "Authentication Failed",
            "remediation": "Verify your API key is correct and has not expired.",
        },
        "connection_refused": {
            "patterns": [
                r"connection.*refused",
                r"failed.*to.*connect",
                r"no.*route.*to.*host",
            ],
            "type": "Connection Failed",
            "remediation": "Ensure the service is running and accessible. Check firewall rules and network connectivity.",
        },
        "timeout": {
            "patterns": [
                r"timeout",
                r"timed.*out",
                r"deadline.*exceeded",
            ],
            "type": "Timeout",
            "remediation": "The service is not responding in time. Check service health and network latency.",
        },
        "certificate_error": {
            "patterns": [
                r"certificate.*verify.*failed",
                r"ssl.*error",
                r"tls.*handshake",
            ],
            "type": "Certificate Error",
            "remediation": "SSL/TLS certificate validation failed. Check certificate validity or disable SSL verification for local services.",
        },
        "not_found": {
            "patterns": [
                r"not.*found",
                r"does.*not.*exist",
                r"no.*such.*file",
            ],
            "type": "Resource Not Found",
            "remediation": "The requested resource does not exist. Verify the resource identifier or path.",
        },
    }

    @classmethod
    def classify_http_error(cls, status_code: int) -> Dict[str, str]:
        """
        Classify HTTP status code and return error details

        Args:
            status_code: HTTP status code

        Returns:
            Dict with type, description, and remediation
        """
        return cls.HTTP_ERROR_MESSAGES.get(
            status_code,
            {
                "type": f"HTTP {status_code}",
                "description": f"The service returned HTTP status {status_code}",
                "remediation": "Check the service documentation for details about this status code.",
            },
        )

    @classmethod
    def classify_text_error(cls, error_text: str) -> Optional[Dict[str, str]]:
        """
        Classify error based on text patterns

        Args:
            error_text: Error message text to analyze

        Returns:
            Dict with type and remediation if pattern matched, None otherwise
        """
        error_text_lower = error_text.lower()

        for error_name, error_info in cls.ERROR_PATTERNS.items():
            for pattern in error_info["patterns"]:
                if re.search(pattern, error_text_lower, re.IGNORECASE):
                    return {
                        "type": error_info["type"],
                        "remediation": error_info["remediation"],
                        "pattern_matched": error_name,
                    }

        return None

    @classmethod
    def format_error_message(
        cls,
        service_name: str,
        error_type: str,
        message: str,
        remediation: str,
        status_code: Optional[int] = None,
        details: Optional[str] = None,
        hostname: Optional[str] = None,
    ) -> str:
        """
        Format a comprehensive error message for users

        Args:
            service_name: Name of the service (e.g., "Pi-hole", "Unifi")
            error_type: Type of error (e.g., "Authentication Failed")
            message: Main error message
            remediation: Actionable guidance for the user
            status_code: Optional HTTP status code
            details: Optional technical details
            hostname: Optional hostname/endpoint

        Returns:
            Formatted error message string
        """
        # Build status indicator
        status_indicator = f" ({status_code})" if status_code else ""

        # Build header
        output = f"✗ {service_name} {error_type}{status_indicator}\n\n"

        # Add main message
        output += f"{message}\n\n"

        # Add hostname if provided
        if hostname:
            output += f"Host: {hostname}\n\n"

        # Add remediation with arrow for visibility
        output += f"→ {remediation}\n"

        # Add technical details if provided
        if details:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            output += f"\nTechnical details: {details} (at {timestamp})\n"

        return output

    @classmethod
    def format_http_error(
        cls,
        service_name: str,
        status_code: int,
        response_text: Optional[str] = None,
        hostname: Optional[str] = None,
        custom_remediation: Optional[str] = None,
    ) -> str:
        """
        Format HTTP error with standard messaging

        Args:
            service_name: Name of the service
            status_code: HTTP status code
            response_text: Optional response body text
            hostname: Optional hostname
            custom_remediation: Optional custom remediation to override default

        Returns:
            Formatted error message
        """
        error_info = cls.classify_http_error(status_code)

        # Use custom remediation if provided
        remediation = custom_remediation or error_info["remediation"]

        # Build message
        message = error_info["description"]
        if response_text:
            # Truncate long responses
            truncated_text = (
                response_text[:200] + "..."
                if len(response_text) > 200
                else response_text
            )
            details = f"Server response: {truncated_text}"
        else:
            details = None

        return cls.format_error_message(
            service_name=service_name,
            error_type=error_info["type"],
            message=message,
            remediation=remediation,
            status_code=status_code,
            details=details,
            hostname=hostname,
        )

    @classmethod
    def format_connection_error(
        cls,
        service_name: str,
        hostname: str,
        port: Optional[int] = None,
        error_type: str = "Connection Failed",
        additional_guidance: Optional[str] = None,
    ) -> str:
        """
        Format connection error with network troubleshooting guidance

        Args:
            service_name: Name of the service
            hostname: Hostname or IP that failed to connect
            port: Optional port number
            error_type: Type of connection error
            additional_guidance: Optional additional remediation steps

        Returns:
            Formatted error message
        """
        host_display = f"{hostname}:{port}" if port else hostname

        base_remediation = f"Ensure {service_name} is running and accessible at {host_display}."

        # Add network troubleshooting commands
        if port:
            base_remediation += f"\n→ Test connectivity: nc -zv {hostname} {port}"
            base_remediation += f"\n→ Check firewall: sudo iptables -L | grep {port}"

        # Add service-specific guidance
        if additional_guidance:
            base_remediation += f"\n→ {additional_guidance}"

        return cls.format_error_message(
            service_name=service_name,
            error_type=error_type,
            message=f"Unable to connect to {host_display}",
            remediation=base_remediation,
            hostname=host_display,
        )

    @classmethod
    def format_timeout_error(
        cls,
        service_name: str,
        hostname: str,
        port: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
    ) -> str:
        """
        Format timeout error

        Args:
            service_name: Name of the service
            hostname: Hostname that timed out
            port: Optional port number
            timeout_seconds: Optional timeout duration

        Returns:
            Formatted error message
        """
        host_display = f"{hostname}:{port}" if port else hostname
        timeout_msg = (
            f" (after {timeout_seconds}s)" if timeout_seconds else ""
        )

        return cls.format_error_message(
            service_name=service_name,
            error_type="Timeout",
            message=f"Connection to {host_display} timed out{timeout_msg}",
            remediation=f"The service is not responding. Check if {service_name} is running and not overloaded.\n→ Check service status and logs for performance issues.",
            hostname=host_display,
        )


def sanitize_sensitive_data(text: str, patterns: Optional[list] = None) -> str:
    """
    Sanitize sensitive data from log messages

    Args:
        text: Text to sanitize
        patterns: Optional list of additional regex patterns to redact

    Returns:
        Sanitized text with sensitive data replaced by ***
    """
    if not text:
        return text

    # Default patterns for common sensitive data
    default_patterns = [
        (r"(api[_-]?key[=:\s]+)[^\s&]+", r"\1***"),  # API keys
        (r"(password[=:\s]+)[^\s&]+", r"\1***"),  # Passwords
        (r"(token[=:\s]+)[^\s&]+", r"\1***"),  # Tokens
        (r"(secret[=:\s]+)[^\s&]+", r"\1***"),  # Secrets
        (r"(authorization:\s*bearer\s+)[^\s]+", r"\1***"),  # Bearer tokens
        (r"(sid[=:\s]+)[^\s&]+", r"\1***"),  # Session IDs
    ]

    # Add custom patterns if provided
    all_patterns = default_patterns + (patterns or [])

    sanitized = text
    for pattern, replacement in all_patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    return sanitized


def log_error_with_context(
    logger: logging.Logger,
    message: str,
    error: Optional[Exception] = None,
    context: Optional[Dict[str, Any]] = None,
    sanitize: bool = True,
) -> None:
    """
    Log error with contextual information

    Args:
        logger: Logger instance
        message: Error message
        error: Optional exception object
        context: Optional dict of contextual information (URL, params, etc.)
        sanitize: Whether to sanitize sensitive data (default True)
    """
    # Build log message
    log_parts = [message]

    # Add context
    if context:
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        if sanitize:
            context_str = sanitize_sensitive_data(context_str)
        log_parts.append(f"Context: {context_str}")

    # Add exception details
    if error:
        log_parts.append(f"Exception: {type(error).__name__}: {str(error)}")

    full_message = " | ".join(log_parts)

    # Log with appropriate level
    if error:
        logger.error(full_message, exc_info=True)
    else:
        logger.error(full_message)
