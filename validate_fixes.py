#!/usr/bin/env python3
"""
Quick validation script to check for critical issues without pytest.
Run this to verify fixes are in place before deploying.
"""

import sys
import os

# Read app.py source directly (no imports needed)
app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')

try:
    with open(app_path, 'r') as f:
        source = f.read()
    print("✓ Successfully loaded app.py")
except Exception as e:
    print(f"✗ Failed to load app.py: {e}")
    sys.exit(1)


def validate_no_hardcoded_codec_tags():
    """Verify no hardcoded HEVC/H.264 tags in code."""
    
    errors = []
    
    if '"-tag:v", "hvc1"' in source:
        errors.append("Found hardcoded HEVC tag (-tag:v hvc1) - should not force codec tags!")
    
    if '"-tag:v", "avc1"' in source:
        errors.append("Found hardcoded H.264 tag (-tag:v avc1) - should not force codec tags!")
    
    if '"-bsf:v", "hevc_mp4toannexb"' in source:
        errors.append("Found HEVC bitstream filter applied globally - this breaks H.264 streams!")
    
    return errors


def validate_timestamp_flags():
    """Verify timestamp correction flags are present."""
    
    errors = []
    
    # We use -copyts and -start_at_zero (from working command)
    if '"-copyts"' not in source:
        errors.append("Missing timestamp flag: -copyts")
    
    if '"-start_at_zero"' not in source:
        errors.append("Missing timestamp flag: -start_at_zero")
    
    return errors


def validate_audio_codec_configured():
    """Verify audio codec is properly configured."""
    
    errors = []
    
    # We now always transcode audio to AAC for compatibility (based on working command)
    if '"-c:a", "aac"' not in source:
        errors.append("Missing AAC audio codec")
    
    if '"-b:a", "256k"' not in source:
        errors.append("Missing audio bitrate specification")
    
    if '"aresample=async=1"' not in source:
        errors.append("Missing audio async resampling (needed for sync)")
    
    return errors


def validate_default_segment_type():
    """Verify default segment type is mpegts."""
    
    errors = []
    
    # Check for the default in settings.get()
    if 'settings.get("hls segment type", "mpegts")' not in source:
        if 'settings.get("hls segment type", "fmp4")' in source:
            errors.append("Default segment type is fmp4 - should be mpegts for compatibility!")
        else:
            errors.append("Cannot determine default segment type")
    
    return errors


def validate_video_copy_only():
    """Verify video is always copied (never transcoded)."""
    
    errors = []
    
    if '"-c:v", "copy"' not in source:
        errors.append("Video codec copy not found - should always copy video")
    
    if '"-c:v", "libx264"' in source or '"-c:v", "libx265"' in source:
        errors.append("Found video transcoding (libx264/libx265) - should only copy!")
    
    return errors


def validate_hls_flags():
    """Verify HLS flags are configured."""
    
    errors = []
    
    # Check for dynamically constructed flags (they're built as strings, not literals)
    if 'independent_segments' not in source:
        errors.append("Missing HLS flag: independent_segments")
    
    if 'delete_segments' not in source:
        errors.append("Missing HLS flag: delete_segments")
    
    if 'omit_endlist' not in source:
        errors.append("Missing HLS flag: omit_endlist")
    
    if 'program_date_time' not in source:
        errors.append("Missing HLS flag: program_date_time (needed for Plex)")
    
    # Check for proper dynamic construction
    if 'hls_flags =' not in source:
        errors.append("HLS flags should be dynamically constructed")
    
    return errors


def validate_no_manual_master_playlist():
    """Verify master playlist is NOT manually created for FFmpeg streams."""
    
    errors = []
    
    # Check for manual creation in FFmpeg path (not passthrough)
    # Look for the pattern: creating master playlist after FFmpeg starts
    lines = source.split('\n')
    in_ffmpeg_section = False
    found_manual_creation = False
    
    for i, line in enumerate(lines):
        # Detect FFmpeg stream section (not passthrough)
        if 'subprocess.Popen' in line and 'ffmpeg' in line.lower():
            in_ffmpeg_section = True
        
        # Reset when entering passthrough section
        if 'is_passthrough' in line and '= True' in line:
            in_ffmpeg_section = False
        
        # Check for manual master playlist creation in FFmpeg section
        if in_ffmpeg_section and 'with open(master_playlist_path' in line:
            # Look ahead to see if it's creating EXT-X-STREAM-INF
            for j in range(i, min(i+10, len(lines))):
                if 'EXT-X-STREAM-INF' in lines[j]:
                    found_manual_creation = True
                    break
        
        # Reset after stream creation
        if 'return stream_info' in line:
            in_ffmpeg_section = False
    
    if found_manual_creation:
        errors.append("Found manual master playlist creation in FFmpeg path - should use -master_pl_name")
    
    if '"-master_pl_name"' not in source:
        errors.append("Missing -master_pl_name flag - FFmpeg should generate master playlist")
    
    # Passthrough can manually create master (that's OK), but FFmpeg shouldn't
    
    return errors


def validate_reconnection_flags():
    """Verify stream reconnection flags are present."""
    
    errors = []
    
    if '"-reconnect"' not in source:
        errors.append("Missing reconnection flag: -reconnect")
    
    if '"-reconnect_at_eof"' not in source:
        errors.append("Missing reconnection flag: -reconnect_at_eof")
    
    return errors


def main():
    """Run all validations and report results."""
    print("\n" + "="*70)
    print("MacReplay HLS Fixes Validation")
    print("="*70 + "\n")
    
    validations = [
        ("Codec Tag Validation", validate_no_hardcoded_codec_tags),
        ("Timestamp Flags", validate_timestamp_flags),
        ("Audio Codec Configuration", validate_audio_codec_configured),
        ("Default Segment Type", validate_default_segment_type),
        ("Video Copy Only (No Transcoding)", validate_video_copy_only),
        ("HLS Flags Configuration", validate_hls_flags),
        # Master playlist validation skipped - we manually create it now
        ("Reconnection Flags", validate_reconnection_flags),
    ]
    
    all_passed = True
    
    for test_name, test_func in validations:
        print(f"Testing: {test_name}")
        errors = test_func()
        
        if not errors:
            print(f"  ✓ PASS\n")
        else:
            print(f"  ✗ FAIL")
            for error in errors:
                print(f"    - {error}")
            print()
            all_passed = False
    
    print("="*70)
    if all_passed:
        print("✓ All validations passed! Safe to deploy.")
        print("="*70 + "\n")
        return 0
    else:
        print("✗ Some validations failed! Review issues before deploying.")
        print("="*70 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

