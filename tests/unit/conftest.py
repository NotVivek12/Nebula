"""
Unit test conftest — no database required.

Unit tests import app modules directly without starting the FastAPI app
or connecting to any external service.
"""

import os

# Override environment BEFORE any app imports to prevent DB/Redis connections
os.environ["ENVIRONMENT"] = "development"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-32-chars-long-ok"
os.environ["POSTGRES_SERVER"] = "localhost"
os.environ["POSTGRES_DB"] = "nebula_test"
os.environ["REDIS_HOST"] = "localhost"
os.environ["WHATSAPP_APP_SECRET"] = "test_app_secret_for_hmac_testing"
os.environ["WHATSAPP_VERIFY_TOKEN"] = "test_verify_token"
