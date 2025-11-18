import pytest
import sys
import os
from unittest.mock import MagicMock

# Add the project root to the path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_config(mocker):
    # Mock the configuration related functions in app.py
    mocker.patch('app.loadConfig', return_value={})
    
    mock_settings = {
        "stream method": "ffmpeg",
        "ffmpeg command": "-re -i <url> pipe:",
        "ffmpeg timeout": "5",
        "test streams": "false", # Disable stream testing for unit tests to speed them up
        "try all macs": "false",
        "username": "admin",
        "password": "password",
        "enable security": "false"
    }
    mocker.patch('app.getSettings', return_value=mock_settings)
    
    mock_portals = {
        "portal1": {
            "enabled": "true",
            "name": "Test Portal",
            "url": "http://example.com",
            "macs": {"00:00:00:00:00:00": "2025-01-01"},
            "streams per mac": "1",
            "proxy": None,
            "custom channel names": {"123": "Test Channel"},
            # fallback channels format: { "fallback_channel_id": "primary_channel_name" }
            # This means channel with ID '456' is the fallback for channel named "Test Channel"
            "fallback channels": {"456": "Test Channel"}
        }
    }
    mocker.patch('app.getPortals', return_value=mock_portals)
    
    # Prevent saving during tests
    mocker.patch('app.savePortals')
    mocker.patch('app.saveSettings')
    
    return mock_portals, mock_settings

