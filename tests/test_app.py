import pytest
from unittest.mock import MagicMock, patch

def test_home_redirect(client, mock_config):
    """Test that the home page redirects to /portals"""
    response = client.get('/')
    assert response.status_code == 302
    assert '/portals' in response.location

def test_channel_fallback_unbound_local_error(client, mock_config, mocker):
    """
    Regression test for UnboundLocalError:
    Simulate a scenario where the primary channel lookup fails (no channels returned),
    and ensure the fallback logic doesn't crash when accessing 'channelName'.
    """
    # Mock stb.getToken to return a token
    mocker.patch('stb.getToken', return_value="mock_token")
    # Mock stb.getProfile to succeed
    mocker.patch('stb.getProfile')
    # Mock stb.getAllChannels to return None (simulating failure/down portal)
    mocker.patch('stb.getAllChannels', return_value=None)
    
    # We expect a 503 because we haven't set up a working fallback stream in this specific mock scenario,
    # but crucially, we do NOT expect an UnboundLocalError (500).
    response = client.get('/play/portal1/999')
    
    assert response.status_code == 503
    assert b"No streams available" in response.data

def test_channel_success_path(client, mock_config, mocker):
    """Test the happy path where a channel is found and streamed."""
    mocker.patch('stb.getToken', return_value="mock_token")
    mocker.patch('stb.getProfile')
    
    mock_channels = [
        {"id": 123, "name": "Test Channel", "cmd": "ffmpeg http://stream.url", "number": 1}
    ]
    mocker.patch('stb.getAllChannels', return_value=mock_channels)
    
    # Mock subprocess.Popen for ffmpeg streaming
    # Popen is used as a context manager, so we need to handle __enter__
    mock_process = MagicMock()
    mock_process.__enter__.return_value = mock_process
    mock_process.__exit__.return_value = None
    
    mock_process.stdout.read.side_effect = [b"fake_video_data", b""] # Return data then EOF
    mock_process.poll.return_value = 0
    
    mocker.patch('subprocess.Popen', return_value=mock_process)
    
    # Request the channel (123 matches the mock data and custom channel name in conftest)
    response = client.get('/play/portal1/123')
    
    assert response.status_code == 200
    assert response.mimetype == "application/octet-stream"
    # We should get the streamed data
    # For streaming responses, the test client might not buffer automatically depending on configuration
    # Using get_data() ensures we read the content
    assert b"fake_video_data" in response.get_data()

def test_fallback_logic_works(client, mock_config, mocker):
    """Test that fallback logic is actually triggered and works when primary fails."""
    portals, settings = mock_config
    
    # 1. Primary lookup fails
    mocker.patch('stb.getToken', return_value="mock_token")
    mocker.patch('stb.getProfile')
    # First call (primary) returns None, Second call (fallback) returns valid channels
    
    # We need to be careful with how we mock getAllChannels because it's called in a loop.
    # The app logic: 
    #   - Iterates MACs for primary portal -> calls getAllChannels
    #   - Fails -> goes to fallback logic
    #   - Iterates portals for fallback -> calls getAllChannels
    
    def side_effect_get_channels(url, mac, token, proxy):
        # Check if this is the fallback call (you might need to distinguish based on args if URLs differed, 
        # but here we just toggle or return based on call count if simpler, or checking the portal URL).
        # Since we are using the same portal as its own fallback in this simple test setup (see conftest),
        # we can't easily distinguish by URL. 
        # Let's just say the first time it returns None, second time it returns the channel.
        pass

    # Easier approach: 
    # The channel '123' is in "custom channel names" as "Test Channel".
    # The fallback for '123' is "Fallback Channel".
    # Let's assume we request channel '123'.
    # Primary lookup for '123' fails.
    # Code checks fallbacks. '123' maps to "Fallback Channel".
    # Code looks for a channel named "Fallback Channel".
    
    # We'll setup the mock to return a list containing ONLY "Fallback Channel"
    # but we need to make sure the FIRST call (primary loop) returns something that DOES NOT contain ID '123'
    # AND the SECOND call (fallback loop) returns the fallback channel.
    
    # Primary loop: looks for ID '123'. 
    # Fallback loop: looks for channel with ID '456' (from conftest fallback config).
    # We configured conftest: "fallback channels": {"456": "Test Channel"}
    # So when "Test Channel" fails, it looks for ID 456.
    # We return a channel list with ID 456.

    # We return different lists for the two calls
    # 1. Primary loop: returns empty list. Fails to find channel.
    # 2. Fallback loop: returns list with ID 456. Success.
    
    fallback_channel = {"id": 456, "name": "Some Name", "cmd": "ffmpeg http://fallback.url", "number": 2}
    
    get_channels_mock = mocker.patch('stb.getAllChannels', side_effect=[[], [fallback_channel]])
    
    # Mock isMacFree to always return True so we don't get stuck on occupied check
    # Since we are mocking app.py functions, we can't easily mock the nested isMacFree.
    # But isMacFree checks 'occupied' global. We should ensure it's empty or handle it.
    # The default 'occupied' is empty, so isMacFree returns True.
    
    # Mock subprocess
    mock_process = MagicMock()
    mock_process.__enter__.return_value = mock_process
    mock_process.__exit__.return_value = None
    
    mock_process.stdout.read.side_effect = [b"fallback_data", b""]
    mock_process.poll.return_value = 0
    # testStream() checks returncode after communicate()
    mock_process.returncode = 0
    mocker.patch('subprocess.Popen', return_value=mock_process)

    response = client.get('/play/portal1/123')
    
    assert response.status_code == 200
    assert b"fallback_data" in response.get_data()

