from typing import Any, Dict

"""Base configuration schemas for service plugins."""

from marshmallow import Schema, fields, post_load, validate


class BaseQUICConfigSchema(Schema):
    """This schema defines common configuration fields shared across all QUIC.
    implementations, reducing duplication in config schemas.
    """

    # Basic identification
    implementation = fields.Str(required=True, description="Implementation name")
    protocol = fields.Str(default="quic", description="Protocol name")
    role = fields.Str(
        required=True,
        validate=validate.OneOf(["client", "server"]),
        description="Service role",
    )

    # Network configuration
    host = fields.Str(default="localhost", description="Target host (for client)")
    port = fields.Int(
        default=4443,
        validate=validate.Range(min=1, max=65535),
        description="Port number",
    )

    # QUIC version
    version = fields.Str(
        default="rfc9000",
        validate=validate.OneOf(["rfc9000", "draft29", "draft27"]),
        description="QUIC version",
    )

    # Certificate configuration
    cert_dir = fields.Str(default="/opt/certs", description="Certificate directory")
    cert_file = fields.Str(
        default="/opt/certs/cert.pem", description="Certificate file"
    )
    key_file = fields.Str(default="/opt/certs/key.pem", description="Private key file")
    generate_new_certificates = fields.Bool(
        default=False, description="Generate new certificates"
    )

    # Logging configuration
    log_level = fields.Str(
        default="info",
        validate=validate.OneOf(["debug", "info", "warning", "error"]),
        description="Log level",
    )
    log_file = fields.Str(allow_none=True, description="Log file path")
    output_dir = fields.Str(default="/logs", description="Output directory")

    # Timeout configuration
    timeout = fields.Int(
        default=60, validate=validate.Range(min=1), description="Timeout in seconds"
    )

    # Build configuration (for compiled implementations)
    build_type = fields.Str(
        default="Release",
        validate=validate.OneOf(["Release", "Debug"]),
        description="Build type for compilation",
    )

    # Advanced options (implementations can extend these)
    extra_args = fields.List(
        fields.Str(), missing=[], description="Additional command-line arguments"
    )

    @post_load
    def make_config(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Post-process configuration data.

        Args:
            data: Validated configuration data
            **kwargs: Additional arguments

        Returns:
            Processed configuration dictionary
        """
        # Ensure paths use forward slashes
        for key in ["cert_dir", "cert_file", "key_file", "log_file", "output_dir"]:
            if key in data and data[key]:
                data[key] = data[key].replace("\\", "/")

        return data


class BaseServiceConfigSchema(Schema):
    """Base configuration schema for all service implementations.

    This schema can be used for non-QUIC protocols as well.
    """

    # Basic identification
    implementation = fields.Str(required=True, description="Implementation name")
    protocol = fields.Str(required=True, description="Protocol name")
    role = fields.Str(required=True, description="Service role")

    # Common configuration
    timeout = fields.Int(
        default=60, validate=validate.Range(min=1), description="Timeout in seconds"
    )

    # Logging
    log_level = fields.Str(
        default="info",
        validate=validate.OneOf(["debug", "info", "warning", "error"]),
        description="Log level",
    )
    output_dir = fields.Str(default="/logs", description="Output directory")

    # Extra arguments
    extra_args = fields.List(
        fields.Str(), missing=[], description="Additional command-line arguments"
    )


class QUICClientConfigSchema(BaseQUICConfigSchema):
    """Extended schema for QUIC client configurations."""

    # Client-specific fields
    target = fields.Str(required=True, description="Target server service name")

    # Request configuration
    request_file = fields.Str(
        allow_none=True, description="File to request from server"
    )
    max_data = fields.Int(
        allow_none=True,
        validate=validate.Range(min=1),
        description="Maximum data to transfer",
    )

    # Connection options
    enable_0rtt = fields.Bool(default=False, description="Enable 0-RTT connection")
    session_cache = fields.Str(
        allow_none=True, description="Session cache file for 0-RTT"
    )


class QUICServerConfigSchema(BaseQUICConfigSchema):
    """Extended schema for QUIC server configurations."""

    # Server-specific fields
    server_name = fields.Str(default="localhost", description="Server name for SNI")

    # Response configuration
    response_dir = fields.Str(default="/www", description="Directory for serving files")

    # Connection options
    enable_0rtt = fields.Bool(default=True, description="Enable 0-RTT support")
    max_clients = fields.Int(
        default=100,
        validate=validate.Range(min=1),
        description="Maximum concurrent clients",
    )
