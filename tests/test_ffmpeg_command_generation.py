"""Tests for FFmpeg command generation and codec validation."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app import HLSStreamManager


class TestFFmpegCommandGeneration:
    """Test suite for FFmpeg command generation and validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = HLSStreamManager(max_streams=5, inactive_timeout=2)
    
    def teardown_method(self):
        """Clean up after tests."""
        self.manager.running = False
        self.manager.cleanup_all()
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('builtins.open', create=True)
    def test_mpegts_default_segment_type(self, mock_open, mock_get_settings, mock_mkdtemp, mock_popen):
        """Test that MPEG-TS is the default segment type for compatibility."""
        # Mock settings with no explicit segment type
        mock_get_settings.return_value = {
            "ffmpeg timeout": "5",
            "hls segment duration": "4",
            "hls playlist size": "6"
            # Note: "hls segment type" is NOT set, should default to mpegts
        }
        
        mock_mkdtemp.return_value = "/tmp/test_hls"
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Start stream
        self.manager.start_stream(
            portal_id="portal1",
            channel_id="123",
            stream_url="http://example.com/stream.ts"
        )
        
        # Get FFmpeg command
        ffmpeg_cmd = mock_popen.call_args[0][0]
        ffmpeg_cmd_str = " ".join(ffmpeg_cmd)
        
        # Verify MPEG-TS is used (not fMP4)
        assert "-hls_segment_type mpegts" in ffmpeg_cmd_str
        assert "-hls_segment_type fmp4" not in ffmpeg_cmd_str
        
        # Verify .ts extension, not .m4s
        assert "seg_%03d.ts" in ffmpeg_cmd_str
        assert "seg_%03d.m4s" not in ffmpeg_cmd_str
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('builtins.open', create=True)
    def test_no_wrong_codec_tags(self, mock_open, mock_get_settings, mock_mkdtemp, mock_popen):
        """Test that we don't apply HEVC tags to H.264 or vice versa.
        
        This was a critical bug where -tag:v hvc1 was applied to all streams,
        causing H.264 streams to be tagged as HEVC.
        """
        mock_get_settings.return_value = {
            "ffmpeg timeout": "5",
            "hls segment type": "mpegts",
            "hls segment duration": "4",
            "hls playlist size": "6"
        }
        
        mock_mkdtemp.return_value = "/tmp/test_hls"
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Start stream
        self.manager.start_stream(
            portal_id="portal1",
            channel_id="123",
            stream_url="http://example.com/stream.ts"
        )
        
        # Get FFmpeg command
        ffmpeg_cmd = mock_popen.call_args[0][0]
        ffmpeg_cmd_str = " ".join(ffmpeg_cmd)
        
        # Verify NO codec tags are applied
        # We should NOT be forcing any specific video codec tags
        assert "-tag:v hvc1" not in ffmpeg_cmd_str
        assert "-tag:v avc1" not in ffmpeg_cmd_str
        
        # Video should be copied as-is
        assert "-c:v copy" in ffmpeg_cmd_str
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('builtins.open', create=True)
    def test_mpegts_uses_audio_copy(self, mock_open, mock_get_settings, mock_mkdtemp, mock_popen):
        """Test that MPEG-TS uses audio copy (no transcoding) for compatibility."""
        mock_get_settings.return_value = {
            "ffmpeg timeout": "5",
            "hls segment type": "mpegts",
            "hls segment duration": "4",
            "hls playlist size": "6"
        }
        
        mock_mkdtemp.return_value = "/tmp/test_hls"
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Start stream
        self.manager.start_stream(
            portal_id="portal1",
            channel_id="123",
            stream_url="http://example.com/stream.ts"
        )
        
        # Get FFmpeg command
        ffmpeg_cmd = mock_popen.call_args[0][0]
        ffmpeg_cmd_str = " ".join(ffmpeg_cmd)
        
        # Verify audio is copied (not transcoded)
        assert "-c:a copy" in ffmpeg_cmd_str
        assert "-c:a aac" not in ffmpeg_cmd_str
        
        # Verify timestamp handling flags
        assert "-avoid_negative_ts make_zero" in ffmpeg_cmd_str
        assert "-mpegts_copyts 1" in ffmpeg_cmd_str
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('builtins.open', create=True)
    def test_fmp4_uses_aac_transcoding(self, mock_open, mock_get_settings, mock_mkdtemp, mock_popen):
        """Test that fMP4 transcodes audio to AAC (required for fMP4)."""
        mock_get_settings.return_value = {
            "ffmpeg timeout": "5",
            "hls segment type": "fmp4",
            "hls segment duration": "4",
            "hls playlist size": "6"
        }
        
        mock_mkdtemp.return_value = "/tmp/test_hls"
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Start stream
        self.manager.start_stream(
            portal_id="portal1",
            channel_id="123",
            stream_url="http://example.com/stream.ts"
        )
        
        # Get FFmpeg command
        ffmpeg_cmd = mock_popen.call_args[0][0]
        ffmpeg_cmd_str = " ".join(ffmpeg_cmd)
        
        # Verify fMP4 settings
        assert "-hls_segment_type fmp4" in ffmpeg_cmd_str
        assert "seg_%03d.m4s" in ffmpeg_cmd_str
        
        # Verify audio is transcoded to AAC
        assert "-c:a aac" in ffmpeg_cmd_str
        assert "-ac 2" in ffmpeg_cmd_str
        
        # Verify timestamp handling
        assert "-avoid_negative_ts make_zero" in ffmpeg_cmd_str
        
        # Verify init file for fMP4
        assert "-hls_fmp4_init_filename init.mp4" in ffmpeg_cmd_str
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('builtins.open', create=True)
    def test_timestamp_correction_flags_present(self, mock_open, mock_get_settings, 
                                               mock_mkdtemp, mock_popen):
        """Test that timestamp correction flags are always present.
        
        These flags fix "Non-monotonous DTS" warnings that cause Plex issues.
        """
        mock_get_settings.return_value = {
            "ffmpeg timeout": "5",
            "hls segment type": "mpegts",
            "hls segment duration": "4",
            "hls playlist size": "6"
        }
        
        mock_mkdtemp.return_value = "/tmp/test_hls"
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Start stream
        self.manager.start_stream(
            portal_id="portal1",
            channel_id="123",
            stream_url="http://example.com/stream.ts"
        )
        
        # Get FFmpeg command
        ffmpeg_cmd = mock_popen.call_args[0][0]
        ffmpeg_cmd_str = " ".join(ffmpeg_cmd)
        
        # Verify timestamp correction flags
        assert "-avoid_negative_ts make_zero" in ffmpeg_cmd_str
        assert "-mpegts_copyts 1" in ffmpeg_cmd_str
        
        # Verify input flags for timestamp handling
        assert "-fflags +genpts+igndts" in ffmpeg_cmd_str
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('builtins.open', create=True)
    def test_hls_flags_configuration(self, mock_open, mock_get_settings, mock_mkdtemp, mock_popen):
        """Test that HLS flags are correctly configured for Plex compatibility."""
        mock_get_settings.return_value = {
            "ffmpeg timeout": "5",
            "hls segment type": "mpegts",
            "hls segment duration": "4",
            "hls playlist size": "6"
        }
        
        mock_mkdtemp.return_value = "/tmp/test_hls"
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Start stream
        self.manager.start_stream(
            portal_id="portal1",
            channel_id="123",
            stream_url="http://example.com/stream.ts"
        )
        
        # Get FFmpeg command
        ffmpeg_cmd = mock_popen.call_args[0][0]
        
        # Find the -hls_flags parameter
        hls_flags_index = ffmpeg_cmd.index("-hls_flags")
        hls_flags_value = ffmpeg_cmd[hls_flags_index + 1]
        
        # Verify required flags
        assert "independent_segments" in hls_flags_value
        assert "delete_segments" in hls_flags_value
        assert "omit_endlist" in hls_flags_value
        
        # For MPEG-TS, should include program_date_time
        assert "program_date_time" in hls_flags_value
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('builtins.open', create=True)
    def test_fmp4_no_mpegts_specific_flags(self, mock_open, mock_get_settings, 
                                          mock_mkdtemp, mock_popen):
        """Test that fMP4 doesn't include MPEG-TS specific flags."""
        mock_get_settings.return_value = {
            "ffmpeg timeout": "5",
            "hls segment type": "fmp4",
            "hls segment duration": "4",
            "hls playlist size": "6"
        }
        
        mock_mkdtemp.return_value = "/tmp/test_hls"
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Start stream
        self.manager.start_stream(
            portal_id="portal1",
            channel_id="123",
            stream_url="http://example.com/stream.ts"
        )
        
        # Get FFmpeg command
        ffmpeg_cmd = mock_popen.call_args[0][0]
        ffmpeg_cmd_str = " ".join(ffmpeg_cmd)
        
        # Verify MPEG-TS specific flags are NOT present for fMP4
        assert "-mpegts_copyts" not in ffmpeg_cmd_str
        
        # But timestamp correction should still be present
        assert "-avoid_negative_ts make_zero" in ffmpeg_cmd_str
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('builtins.open', create=True)
    def test_segment_numbering_starts_at_zero(self, mock_open, mock_get_settings, 
                                             mock_mkdtemp, mock_popen):
        """Test that segment numbering explicitly starts at 0."""
        mock_get_settings.return_value = {
            "ffmpeg timeout": "5",
            "hls segment type": "mpegts",
            "hls segment duration": "4",
            "hls playlist size": "6"
        }
        
        mock_mkdtemp.return_value = "/tmp/test_hls"
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Start stream
        self.manager.start_stream(
            portal_id="portal1",
            channel_id="123",
            stream_url="http://example.com/stream.ts"
        )
        
        # Get FFmpeg command
        ffmpeg_cmd = mock_popen.call_args[0][0]
        ffmpeg_cmd_str = " ".join(ffmpeg_cmd)
        
        # Verify segment numbering starts at 0
        assert "-start_number 0" in ffmpeg_cmd_str
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('builtins.open', create=True)
    def test_reconnection_flags_present(self, mock_open, mock_get_settings, 
                                       mock_mkdtemp, mock_popen):
        """Test that stream reconnection flags are configured."""
        mock_get_settings.return_value = {
            "ffmpeg timeout": "5",
            "hls segment type": "mpegts",
            "hls segment duration": "4",
            "hls playlist size": "6"
        }
        
        mock_mkdtemp.return_value = "/tmp/test_hls"
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Start stream
        self.manager.start_stream(
            portal_id="portal1",
            channel_id="123",
            stream_url="http://example.com/stream.ts"
        )
        
        # Get FFmpeg command
        ffmpeg_cmd = mock_popen.call_args[0][0]
        ffmpeg_cmd_str = " ".join(ffmpeg_cmd)
        
        # Verify reconnection flags
        assert "-reconnect 1" in ffmpeg_cmd_str
        assert "-reconnect_at_eof 1" in ffmpeg_cmd_str
        assert "-reconnect_streamed 1" in ffmpeg_cmd_str
        assert "-reconnect_delay_max 15" in ffmpeg_cmd_str
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('builtins.open', create=True)
    def test_master_playlist_generated_by_ffmpeg(self, mock_open, mock_get_settings, 
                                                mock_mkdtemp, mock_popen):
        """Test that master playlist is generated by FFmpeg, not manually created.
        
        Manual creation caused codec mismatches. FFmpeg should generate it
        with correct codec info from the actual stream.
        """
        mock_get_settings.return_value = {
            "ffmpeg timeout": "5",
            "hls segment type": "mpegts",
            "hls segment duration": "4",
            "hls playlist size": "6"
        }
        
        mock_mkdtemp.return_value = "/tmp/test_hls"
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Track file writes
        file_writes = {}
        
        def mock_open_func(path, mode='r'):
            mock_file = MagicMock()
            file_writes[path] = mock_file
            return MagicMock(__enter__=lambda s: mock_file, __exit__=lambda s, *args: None)
        
        mock_open.side_effect = mock_open_func
        
        # Start stream
        self.manager.start_stream(
            portal_id="portal1",
            channel_id="123",
            stream_url="http://example.com/stream.ts"
        )
        
        # Get FFmpeg command
        ffmpeg_cmd = mock_popen.call_args[0][0]
        ffmpeg_cmd_str = " ".join(ffmpeg_cmd)
        
        # Verify FFmpeg is told to create master playlist
        assert "-master_pl_name master.m3u8" in ffmpeg_cmd_str
        
        # Verify we're NOT manually writing master.m3u8
        # (The code should not create it with hardcoded codec strings)
        master_playlist_paths = [p for p in file_writes.keys() if 'master.m3u8' in p]
        assert len(master_playlist_paths) == 0, \
            "Master playlist should be generated by FFmpeg, not manually created"
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('builtins.open', create=True)
    def test_video_always_copied_never_transcoded(self, mock_open, mock_get_settings,
                                                  mock_mkdtemp, mock_popen):
        """Test that video is always copied (never transcoded) for performance."""
        for segment_type in ["mpegts", "fmp4"]:
            mock_get_settings.return_value = {
                "ffmpeg timeout": "5",
                "hls segment type": segment_type,
                "hls segment duration": "4",
                "hls playlist size": "6"
            }
            
            mock_mkdtemp.return_value = "/tmp/test_hls"
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process
            
            # Start stream
            self.manager.start_stream(
                portal_id="portal1",
                channel_id=f"123_{segment_type}",
                stream_url="http://example.com/stream.ts"
            )
            
            # Get FFmpeg command
            ffmpeg_cmd = mock_popen.call_args[0][0]
            ffmpeg_cmd_str = " ".join(ffmpeg_cmd)
            
            # Verify video is copied
            assert "-c:v copy" in ffmpeg_cmd_str, \
                f"Video should be copied for {segment_type}"
            
            # Verify video is NOT transcoded
            assert "-c:v libx264" not in ffmpeg_cmd_str, \
                f"Video should not be transcoded for {segment_type}"
            assert "-c:v libx265" not in ffmpeg_cmd_str, \
                f"Video should not be transcoded for {segment_type}"
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('builtins.open', create=True)
    def test_segment_settings_consistent(self, mock_open, mock_get_settings, 
                                        mock_mkdtemp, mock_popen):
        """Test that segment duration and playlist size settings are applied."""
        mock_get_settings.return_value = {
            "ffmpeg timeout": "5",
            "hls segment type": "mpegts",
            "hls segment duration": "6",  # Custom value
            "hls playlist size": "10"     # Custom value
        }
        
        mock_mkdtemp.return_value = "/tmp/test_hls"
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Start stream
        self.manager.start_stream(
            portal_id="portal1",
            channel_id="123",
            stream_url="http://example.com/stream.ts"
        )
        
        # Get FFmpeg command
        ffmpeg_cmd = mock_popen.call_args[0][0]
        ffmpeg_cmd_str = " ".join(ffmpeg_cmd)
        
        # Verify custom settings applied
        assert "-hls_time 6" in ffmpeg_cmd_str
        assert "-hls_list_size 10" in ffmpeg_cmd_str


class TestCodecTagValidation:
    """Specific tests for codec tag validation to prevent the H.264/HEVC mix-up."""
    
    def test_no_hardcoded_codec_tags(self):
        """Verify that the code doesn't contain hardcoded codec tags in the wrong place.
        
        This is a code inspection test to ensure we don't have -tag:v hvc1 or
        -tag:v avc1 applied unconditionally.
        """
        import app
        import inspect
        
        # Get the source code of start_stream method
        source = inspect.getsource(app.HLSStreamManager.start_stream)
        
        # Check for problematic patterns
        assert '"-tag:v", "hvc1"' not in source, \
            "Found hardcoded HEVC tag - should not force codec tags"
        
        assert '"-tag:v", "avc1"' not in source, \
            "Found hardcoded H.264 tag - should not force codec tags"
        
        # If we ever need to add codec tags in the future, they must be conditional
        # based on actual codec detection, not applied to all streams
    
    def test_no_codec_specific_bitstream_filters_applied_globally(self):
        """Verify codec-specific bitstream filters are not applied to all streams.
        
        The hevc_mp4toannexb filter only works with HEVC and crashes on H.264.
        It should never be applied unconditionally.
        """
        import app
        import inspect
        
        source = inspect.getsource(app.HLSStreamManager.start_stream)
        
        # Check for unconditional bitstream filter
        assert '"-bsf:v", "hevc_mp4toannexb"' not in source, \
            "Found HEVC bitstream filter applied to all streams - this breaks H.264!"
        
        # If we need bitstream filters in the future, they must be conditional
        # Example: if codec == "hevc": ffmpeg_cmd.extend(["-bsf:v", "hevc_mp4toannexb"])


class TestConditionalFlags:
    """Test that format-specific flags are only applied when needed."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = HLSStreamManager(max_streams=5, inactive_timeout=2)
    
    def teardown_method(self):
        """Clean up after tests."""
        self.manager.running = False
        self.manager.cleanup_all()
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('builtins.open', create=True)
    def test_mpegts_specific_flags_only_for_mpegts(self, mock_open, mock_get_settings, 
                                                   mock_mkdtemp, mock_popen):
        """Test that MPEG-TS specific flags are NOT added for fMP4."""
        mock_get_settings.return_value = {
            "ffmpeg timeout": "5",
            "hls segment type": "fmp4",  # Using fMP4
            "hls segment duration": "4",
            "hls playlist size": "6"
        }
        
        mock_mkdtemp.return_value = "/tmp/test_hls"
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Start stream
        self.manager.start_stream(
            portal_id="portal1",
            channel_id="123",
            stream_url="http://example.com/stream.ts"
        )
        
        # Get FFmpeg command
        ffmpeg_cmd = mock_popen.call_args[0][0]
        ffmpeg_cmd_str = " ".join(ffmpeg_cmd)
        
        # Verify MPEG-TS specific flags are NOT present for fMP4
        assert "-mpegts_flags" not in ffmpeg_cmd_str, \
            "MPEG-TS flags should not be added for fMP4"
        assert "-pcr_period" not in ffmpeg_cmd_str, \
            "PCR period should not be added for fMP4"
        assert "program_date_time" not in ffmpeg_cmd_str, \
            "program_date_time should not be added for fMP4"
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('builtins.open', create=True)
    def test_mpegts_flags_present_for_mpegts(self, mock_open, mock_get_settings,
                                            mock_mkdtemp, mock_popen):
        """Test that MPEG-TS specific flags ARE added for MPEG-TS."""
        mock_get_settings.return_value = {
            "ffmpeg timeout": "5",
            "hls segment type": "mpegts",  # Using MPEG-TS
            "hls segment duration": "4",
            "hls playlist size": "6"
        }
        
        mock_mkdtemp.return_value = "/tmp/test_hls"
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Start stream
        self.manager.start_stream(
            portal_id="portal1",
            channel_id="123",
            stream_url="http://example.com/stream.ts"
        )
        
        # Get FFmpeg command
        ffmpeg_cmd = mock_popen.call_args[0][0]
        ffmpeg_cmd_str = " ".join(ffmpeg_cmd)
        
        # Verify MPEG-TS specific flags ARE present
        assert "-mpegts_flags pat_pmt_at_frames" in ffmpeg_cmd_str, \
            "MPEG-TS flags should be added for MPEG-TS"
        assert "-pcr_period 20" in ffmpeg_cmd_str, \
            "PCR period should be added for MPEG-TS"
        assert "program_date_time" in ffmpeg_cmd_str, \
            "program_date_time should be added for MPEG-TS"


class TestHLSPassthrough:
    """Test HLS passthrough mode (when source is already HLS)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = HLSStreamManager(max_streams=5, inactive_timeout=2)
    
    def teardown_method(self):
        """Clean up after tests."""
        self.manager.running = False
        self.manager.cleanup_all()
    
    @patch('app.subprocess.Popen')
    @patch('app.tempfile.mkdtemp')
    @patch('app.getSettings')
    @patch('app.requests.get')
    def test_hls_source_uses_passthrough(self, mock_requests, mock_get_settings, 
                                        mock_mkdtemp, mock_popen):
        """Test that HLS sources use passthrough mode (no re-encoding)."""
        mock_get_settings.return_value = {
            "ffmpeg timeout": "5",
            "hls segment type": "mpegts"
        }
        
        # Mock HLS source response
        mock_response = Mock()
        mock_response.text = "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000000\nstream.m3u8"
        mock_response.status_code = 200
        mock_requests.return_value = mock_response
        
        mock_mkdtemp.return_value = "/tmp/test_hls"
        
        # Start stream with HLS source
        stream_info = self.manager.start_stream(
            portal_id="portal1",
            channel_id="123",
            stream_url="http://example.com/master.m3u8"
        )
        
        # Verify passthrough mode is used
        assert stream_info['is_passthrough'] == True
        
        # Verify FFmpeg was NOT called (passthrough doesn't use FFmpeg)
        assert not mock_popen.called

