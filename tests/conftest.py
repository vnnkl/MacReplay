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

@pytest.fixture
def mock_db_with_channels(mocker):
    """Create a mock database with test channel data including duplicates."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    
    # Sample channel data with duplicates and various genres/portals
    test_channels = [
        # Portal 1 channels
        {
            'portal': 'portal1', 'channel_id': '101', 'portal_name': 'Test Portal 1',
            'name': 'CNN', 'custom_name': '', 'number': '1', 'custom_number': '',
            'genre': 'News', 'custom_genre': '', 'logo': 'cnn.png',
            'enabled': 1, 'custom_epg_id': '', 'fallback_channel': ''
        },
        {
            'portal': 'portal1', 'channel_id': '102', 'portal_name': 'Test Portal 1',
            'name': 'ESPN', 'custom_name': '', 'number': '2', 'custom_number': '',
            'genre': 'Sports', 'custom_genre': '', 'logo': 'espn.png',
            'enabled': 1, 'custom_epg_id': '', 'fallback_channel': ''
        },
        {
            'portal': 'portal1', 'channel_id': '103', 'portal_name': 'Test Portal 1',
            'name': 'CNN', 'custom_name': '', 'number': '3', 'custom_number': '',
            'genre': 'News', 'custom_genre': '', 'logo': 'cnn2.png',
            'enabled': 1, 'custom_epg_id': '', 'fallback_channel': ''
        },
        # Portal 2 channels
        {
            'portal': 'portal2', 'channel_id': '201', 'portal_name': 'Test Portal 2',
            'name': 'HBO', 'custom_name': '', 'number': '4', 'custom_number': '',
            'genre': 'Movies', 'custom_genre': '', 'logo': 'hbo.png',
            'enabled': 1, 'custom_epg_id': '', 'fallback_channel': ''
        },
        {
            'portal': 'portal2', 'channel_id': '202', 'portal_name': 'Test Portal 2',
            'name': 'CNN', 'custom_name': '', 'number': '5', 'custom_number': '',
            'genre': 'News', 'custom_genre': '', 'logo': 'cnn3.png',
            'enabled': 1, 'custom_epg_id': '', 'fallback_channel': ''
        },
        {
            'portal': 'portal2', 'channel_id': '203', 'portal_name': 'Test Portal 2',
            'name': 'Discovery', 'custom_name': '', 'number': '6', 'custom_number': '',
            'genre': 'Documentary', 'custom_genre': '', 'logo': 'disc.png',
            'enabled': 0, 'custom_epg_id': '', 'fallback_channel': ''
        },
        # Disabled duplicate (should not count as duplicate)
        {
            'portal': 'portal1', 'channel_id': '104', 'portal_name': 'Test Portal 1',
            'name': 'ESPN', 'custom_name': '', 'number': '7', 'custom_number': '',
            'genre': 'Sports', 'custom_genre': '', 'logo': 'espn2.png',
            'enabled': 0, 'custom_epg_id': '', 'fallback_channel': ''
        },
    ]
    
    # Setup mock to handle multiple fetchall() and fetchone() calls
    # Track call counts to return different results
    fetchall_call_count = [0]
    fetchone_call_count = [0]
    
    def fetchall_side_effect():
        call_num = fetchall_call_count[0]
        fetchall_call_count[0] += 1
        
        # First call: main data query
        if call_num == 0:
            return test_channels
        # Second call: duplicate counts query
        elif call_num == 1:
            return [
                {'channel_name': 'CNN', 'count': 3},  # 3 enabled CNNs
                {'channel_name': 'ESPN', 'count': 1},  # Only 1 enabled ESPN
            ]
        # Subsequent calls
        else:
            return []
    
    def fetchone_side_effect():
        call_num = fetchone_call_count[0]
        fetchone_call_count[0] += 1
        
        # First call: total count
        if call_num == 0:
            return {0: len(test_channels)}  # Support both dict and index access
        # Second call: filtered count  
        elif call_num == 1:
            return {0: len(test_channels)}
        else:
            return {0: 0}
    
    mock_cursor.fetchall.side_effect = fetchall_side_effect
    mock_cursor.fetchone.side_effect = fetchone_side_effect
    
    mocker.patch('app.get_db_connection', return_value=mock_conn)
    
    return mock_conn, mock_cursor, test_channels
