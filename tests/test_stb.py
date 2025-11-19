import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import stb


class TestSTBFunctions:
    """Test suite for STB portal functions."""
    
    def test_getToken_success(self, mocker):
        """Test successful token retrieval."""
        # Mock the requests.Session.get
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "js": {
                "token": "test_token_123"
            }
        }
        
        mocker.patch.object(stb.s, 'get', return_value=mock_response)
        
        result = stb.getToken("http://example.com/portal.php", "00:1A:79:00:00:00")
        
        assert result == "test_token_123"
        stb.s.get.assert_called_once()
        
    def test_getToken_timeout(self, mocker):
        """Test token retrieval with timeout."""
        mocker.patch.object(stb.s, 'get', side_effect=requests.Timeout("Connection timed out"))
        
        result = stb.getToken("http://example.com/portal.php", "00:1A:79:00:00:00")
        
        assert result is None
        
    def test_getToken_request_exception(self, mocker):
        """Test token retrieval with request exception."""
        mocker.patch.object(stb.s, 'get', side_effect=requests.RequestException("Connection error"))
        
        result = stb.getToken("http://example.com/portal.php", "00:1A:79:00:00:00")
        
        assert result is None
        
    def test_getToken_invalid_response(self, mocker):
        """Test token retrieval with invalid JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "Invalid"}
        
        mocker.patch.object(stb.s, 'get', return_value=mock_response)
        
        result = stb.getToken("http://example.com/portal.php", "00:1A:79:00:00:00")
        
        assert result is None
    
    def test_getProfile_success(self, mocker):
        """Test successful profile retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "js": {
                "id": "123",
                "name": "Test User"
            }
        }
        
        mocker.patch.object(stb.s, 'get', return_value=mock_response)
        
        result = stb.getProfile(
            "http://example.com/portal.php",
            "00:1A:79:00:00:00",
            "test_token"
        )
        
        assert result == {"id": "123", "name": "Test User"}
        
    def test_getExpires_success(self, mocker):
        """Test successful expiry date retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "js": {
                "phone": "2025-12-31"
            }
        }
        
        mocker.patch.object(stb.s, 'get', return_value=mock_response)
        
        result = stb.getExpires(
            "http://example.com/portal.php",
            "00:1A:79:00:00:00",
            "test_token"
        )
        
        assert result == "2025-12-31"
        
    def test_getExpires_timeout(self, mocker):
        """Test expiry retrieval with timeout."""
        mocker.patch.object(stb.s, 'get', side_effect=requests.Timeout("Connection timed out"))
        
        result = stb.getExpires(
            "http://example.com/portal.php",
            "00:1A:79:00:00:00",
            "test_token"
        )
        
        assert result is None
        
    def test_getAllChannels_success(self, mocker):
        """Test successful channel list retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "js": {
                "data": [
                    {"id": "1", "name": "Channel 1"},
                    {"id": "2", "name": "Channel 2"}
                ]
            }
        }
        
        mocker.patch.object(stb.s, 'get', return_value=mock_response)
        
        result = stb.getAllChannels(
            "http://example.com/portal.php",
            "00:1A:79:00:00:00",
            "test_token"
        )
        
        assert len(result) == 2
        assert result[0]["name"] == "Channel 1"
        
    def test_getAllChannels_timeout(self, mocker):
        """Test channel list retrieval with timeout."""
        mocker.patch.object(stb.s, 'get', side_effect=requests.Timeout("Connection timed out"))
        
        result = stb.getAllChannels(
            "http://example.com/portal.php",
            "00:1A:79:00:00:00",
            "test_token"
        )
        
        assert result is None


class TestTimeoutSettings:
    """Test that timeouts are properly configured."""
    
    def test_getToken_has_timeout(self, mocker):
        """Verify getToken uses appropriate timeout."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"js": {"token": "test"}}
        
        mock_get = mocker.patch.object(stb.s, 'get', return_value=mock_response)
        
        stb.getToken("http://example.com/portal.php", "00:1A:79:00:00:00")
        
        # Check that timeout parameter was passed
        call_kwargs = mock_get.call_args[1]
        assert 'timeout' in call_kwargs
        assert call_kwargs['timeout'] == 20  # Should be 20 seconds
        
    def test_getExpires_has_timeout(self, mocker):
        """Verify getExpires uses appropriate timeout."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"js": {"phone": "2025-12-31"}}
        
        mock_get = mocker.patch.object(stb.s, 'get', return_value=mock_response)
        
        stb.getExpires("http://example.com/portal.php", "00:1A:79:00:00:00", "token")
        
        # Check that timeout parameter was passed
        call_kwargs = mock_get.call_args[1]
        assert 'timeout' in call_kwargs
        assert call_kwargs['timeout'] == 15  # Should be 15 seconds
        
    def test_getAllChannels_has_timeout(self, mocker):
        """Verify getAllChannels uses appropriate timeout."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"js": {"data": []}}
        
        mock_get = mocker.patch.object(stb.s, 'get', return_value=mock_response)
        
        stb.getAllChannels("http://example.com/portal.php", "00:1A:79:00:00:00", "token")
        
        # Check that timeout parameter was passed
        call_kwargs = mock_get.call_args[1]
        assert 'timeout' in call_kwargs
        assert call_kwargs['timeout'] == 30  # Should be 30 seconds for large responses


class TestProxySupport:
    """Test proxy parameter handling."""
    
    def test_getToken_with_proxy(self, mocker):
        """Test that proxy parameter is correctly passed."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"js": {"token": "test"}}
        
        mock_get = mocker.patch.object(stb.s, 'get', return_value=mock_response)
        
        stb.getToken(
            "http://example.com/portal.php",
            "00:1A:79:00:00:00",
            proxy="http://proxy:8080"
        )
        
        # Check that proxies were set
        call_kwargs = mock_get.call_args[1]
        assert 'proxies' in call_kwargs
        assert call_kwargs['proxies']['http'] == "http://proxy:8080"
        assert call_kwargs['proxies']['https'] == "http://proxy:8080"
        
    def test_getToken_without_proxy(self, mocker):
        """Test that None proxy works correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"js": {"token": "test"}}
        
        mock_get = mocker.patch.object(stb.s, 'get', return_value=mock_response)
        
        stb.getToken("http://example.com/portal.php", "00:1A:79:00:00:00")
        
        # Check that proxies dict contains None values
        call_kwargs = mock_get.call_args[1]
        assert 'proxies' in call_kwargs
        assert call_kwargs['proxies']['http'] is None
        assert call_kwargs['proxies']['https'] is None


class TestMACAddressHandling:
    """Test MAC address cookie handling."""
    
    def test_mac_address_in_cookies(self, mocker):
        """Verify MAC address is correctly set in cookies."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"js": {"token": "test"}}
        
        mock_get = mocker.patch.object(stb.s, 'get', return_value=mock_response)
        
        test_mac = "00:1A:79:5D:05:D3"
        stb.getToken("http://example.com/portal.php", test_mac)
        
        # Check that MAC is in cookies
        call_kwargs = mock_get.call_args[1]
        assert 'cookies' in call_kwargs
        assert call_kwargs['cookies']['mac'] == test_mac

