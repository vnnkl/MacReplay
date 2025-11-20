"""Tests for HLS Stream Manager."""
import pytest
import time
import os
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch, call
from app import HLSStreamManager


class TestHLSStreamManager:
    """Test suite for HLSStreamManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = HLSStreamManager(max_streams=5, inactive_timeout=2)
    
    def teardown_method(self):
        """Clean up after tests."""
        self.manager.running = False
        self.manager.cleanup_all()
    
    def test_manager_initialization(self):
        """Test that manager initializes with correct defaults."""
        assert self.manager.max_streams == 5
        assert self.manager.inactive_timeout == 2
        assert len(self.manager.streams) == 0
        assert not self.manager.running
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    def test_start_stream(self, mock_get_settings, mock_mkdtemp, mock_popen):
        """Test starting a new HLS stream."""
        # Mock settings
        mock_get_settings.return_value = {"ffmpeg timeout": "5"}
        
        # Mock temp directory
        temp_dir = "/tmp/test_hls_stream"
        mock_mkdtemp.return_value = temp_dir
        
        # Mock FFmpeg process
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Mock file creation
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            # Start stream
            stream_info = self.manager.start_stream(
                portal_id="portal1",
                channel_id="123",
                stream_url="http://example.com/stream.ts",
                proxy=None
            )
        
        # Verify stream was created
        assert "portal1_123" in self.manager.streams
        assert stream_info['portal_id'] == "portal1"
        assert stream_info['channel_id'] == "123"
        assert stream_info['stream_url'] == "http://example.com/stream.ts"
        assert stream_info['process'] == mock_process
        
        # Verify FFmpeg was called
        mock_popen.assert_called_once()
        ffmpeg_cmd = mock_popen.call_args[0][0]
        assert ffmpeg_cmd[0] == "ffmpeg"
        assert "http://example.com/stream.ts" in ffmpeg_cmd
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    def test_reuse_existing_stream(self, mock_get_settings, mock_mkdtemp, mock_popen):
        """Test that calling start_stream twice reuses the existing stream."""
        # Mock settings
        mock_get_settings.return_value = {"ffmpeg timeout": "5"}
        
        # Mock temp directory
        temp_dir = "/tmp/test_hls_stream"
        mock_mkdtemp.return_value = temp_dir
        
        # Mock FFmpeg process
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Mock file creation
        with patch('builtins.open', create=True):
            # Start stream first time
            stream_info1 = self.manager.start_stream(
                portal_id="portal1",
                channel_id="123",
                stream_url="http://example.com/stream.ts"
            )
            
            # Start stream second time
            stream_info2 = self.manager.start_stream(
                portal_id="portal1",
                channel_id="123",
                stream_url="http://example.com/stream.ts"
            )
        
        # Verify only one stream exists
        assert len(self.manager.streams) == 1
        
        # Verify FFmpeg was only called once
        assert mock_popen.call_count == 1
        
        # Verify same stream info returned
        assert stream_info1 == stream_info2
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    def test_max_streams_limit(self, mock_get_settings, mock_mkdtemp, mock_popen):
        """Test that max_streams limit is enforced."""
        # Mock settings
        mock_get_settings.return_value = {"ffmpeg timeout": "5"}
        
        # Mock temp directory
        mock_mkdtemp.return_value = "/tmp/test_hls_stream"
        
        # Mock FFmpeg process
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Mock file creation
        with patch('builtins.open', create=True):
            # Start max_streams number of streams
            for i in range(self.manager.max_streams):
                self.manager.start_stream(
                    portal_id="portal1",
                    channel_id=str(i),
                    stream_url=f"http://example.com/stream{i}.ts"
                )
            
            # Try to start one more stream - should fail
            with pytest.raises(Exception, match="Maximum concurrent streams"):
                self.manager.start_stream(
                    portal_id="portal1",
                    channel_id="999",
                    stream_url="http://example.com/stream999.ts"
                )
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('app.os.path.exists')
    @patch('app.shutil.rmtree')
    def test_cleanup_inactive_streams(self, mock_rmtree, mock_exists, mock_get_settings, 
                                     mock_mkdtemp, mock_popen):
        """Test that inactive streams are cleaned up."""
        # Mock settings
        mock_get_settings.return_value = {"ffmpeg timeout": "5"}
        
        # Mock temp directory
        temp_dir = "/tmp/test_hls_stream"
        mock_mkdtemp.return_value = temp_dir
        mock_exists.return_value = True
        
        # Mock FFmpeg process
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Mock file creation
        with patch('builtins.open', create=True):
            # Start a stream
            self.manager.start_stream(
                portal_id="portal1",
                channel_id="123",
                stream_url="http://example.com/stream.ts"
            )
        
        # Verify stream exists
        assert len(self.manager.streams) == 1
        
        # Manually set last_accessed to past timeout
        stream_key = "portal1_123"
        self.manager.streams[stream_key]['last_accessed'] = time.time() - 100
        
        # Run cleanup
        self.manager._cleanup_inactive_streams()
        
        # Verify stream was cleaned up
        assert len(self.manager.streams) == 0
        mock_process.terminate.assert_called_once()
        mock_rmtree.assert_called_once()
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('app.os.path.exists')
    @patch('app.shutil.rmtree')
    def test_cleanup_crashed_streams(self, mock_rmtree, mock_exists, mock_get_settings,
                                    mock_mkdtemp, mock_popen):
        """Test that crashed streams are detected and cleaned up."""
        # Mock settings
        mock_get_settings.return_value = {"ffmpeg timeout": "5"}
        
        # Mock temp directory
        temp_dir = "/tmp/test_hls_stream"
        mock_mkdtemp.return_value = temp_dir
        mock_exists.return_value = True
        
        # Mock FFmpeg process
        mock_process = Mock()
        mock_process.poll.return_value = None  # Initially running
        mock_process.returncode = 1  # Crashed with error
        mock_popen.return_value = mock_process
        
        # Mock file creation
        with patch('builtins.open', create=True):
            # Start a stream
            self.manager.start_stream(
                portal_id="portal1",
                channel_id="123",
                stream_url="http://example.com/stream.ts"
            )
        
        # Verify stream exists
        assert len(self.manager.streams) == 1
        
        # Simulate process crash
        mock_process.poll.return_value = 1  # Process exited with error
        
        # Run cleanup
        self.manager._cleanup_inactive_streams()
        
        # Verify stream was cleaned up
        assert len(self.manager.streams) == 0
        mock_rmtree.assert_called_once()
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('app.os.path.exists')
    def test_get_file(self, mock_exists, mock_get_settings, mock_mkdtemp, mock_popen):
        """Test getting a file from an active stream."""
        # Mock settings
        mock_get_settings.return_value = {"ffmpeg timeout": "5"}
        
        # Mock temp directory
        temp_dir = "/tmp/test_hls_stream"
        mock_mkdtemp.return_value = temp_dir
        
        # Mock FFmpeg process
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Mock file creation and existence
        with patch('builtins.open', create=True):
            # Start a stream
            self.manager.start_stream(
                portal_id="portal1",
                channel_id="123",
                stream_url="http://example.com/stream.ts"
            )
        
        # Mock file exists
        mock_exists.return_value = True
        
        # Get file
        file_path = self.manager.get_file("portal1", "123", "stream.m3u8")
        
        # Verify correct path returned
        assert file_path == os.path.join(temp_dir, "stream.m3u8")
        
        # Verify last_accessed was updated
        stream_key = "portal1_123"
        assert self.manager.streams[stream_key]['last_accessed'] > time.time() - 1
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    def test_get_file_nonexistent_stream(self, mock_get_settings, mock_mkdtemp, mock_popen):
        """Test getting a file from a non-existent stream returns None."""
        file_path = self.manager.get_file("portal1", "999", "stream.m3u8")
        assert file_path is None
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('app.os.path.exists')
    @patch('app.shutil.rmtree')
    def test_cleanup_all(self, mock_rmtree, mock_exists, mock_get_settings,
                        mock_mkdtemp, mock_popen):
        """Test cleanup_all removes all active streams."""
        # Mock settings
        mock_get_settings.return_value = {"ffmpeg timeout": "5"}
        
        # Mock temp directory
        mock_mkdtemp.return_value = "/tmp/test_hls_stream"
        mock_exists.return_value = True
        
        # Mock FFmpeg process
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Mock file creation
        with patch('builtins.open', create=True):
            # Start multiple streams
            for i in range(3):
                self.manager.start_stream(
                    portal_id="portal1",
                    channel_id=str(i),
                    stream_url=f"http://example.com/stream{i}.ts"
                )
        
        # Verify streams exist
        assert len(self.manager.streams) == 3
        
        # Cleanup all
        self.manager.cleanup_all()
        
        # Verify all streams cleaned up
        assert len(self.manager.streams) == 0
        assert not self.manager.running
        
        # Verify all processes terminated
        assert mock_process.terminate.call_count == 3

