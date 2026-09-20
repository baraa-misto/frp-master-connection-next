"""FastAPI delivery boundary for the trusted backend shell."""

from frp_master_connection.api.app import app, create_app

__all__ = ("app", "create_app")
