"""Tests for app.py module."""

import pytest

from remote_mcp_server import app
from remote_mcp_server.mcp_server import lambda_handler as mcp_lambda_handler


class TestAppModule:
    """Test the app.py module functionality."""

    def test_lambda_handler_import(self):
        """Test that lambda_handler is properly imported."""
        # Should be able to import lambda_handler from app
        assert hasattr(app, "lambda_handler")

        # Should be the same function as the one in mcp_server
        assert app.lambda_handler is mcp_lambda_handler

    def test_all_exports(self):
        """Test __all__ exports."""
        assert hasattr(app, "__all__")
        assert "lambda_handler" in app.__all__
        assert len(app.__all__) == 1

    def test_backward_compatibility(self):
        """Test that app.py provides backward compatibility."""
        # This tests that existing code using app.lambda_handler still works
        from remote_mcp_server.app import lambda_handler

        # Should be callable
        assert callable(lambda_handler)

        # Should be the same function
        assert lambda_handler is mcp_lambda_handler

    def test_module_docstring(self):
        """Test that module has proper docstring."""
        assert app.__doc__ is not None
        assert "AWS Lambda handler" in app.__doc__
        # The actual docstring says "imports from the new MCP server"
        assert "MCP server" in app.__doc__
