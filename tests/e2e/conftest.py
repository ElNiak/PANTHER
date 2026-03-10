"""E2E test fixtures for PANTHER webapp."""

import pytest_asyncio
from nicegui.testing import user_simulation

from panther.webapp.app import create_app


@pytest_asyncio.fixture
async def user(tmp_path):
    """Yield a simulated User connected to a fresh PANTHER webapp."""
    async with user_simulation() as u:
        create_app(output_dir=str(tmp_path))
        yield u
