#!/usr/bin/env python3
"""
FFmpeg Startup Time Benchmark
Tests different FFmpeg command configurations to find the fastest startup time.
Run on the server: python3 test_ffmpeg_startup.py <stream_url>
"""

import subprocess
import sys
import time
import os

# Different FFmpeg command configurations to test
CONFIGS = {
    "minimal": {
        "desc": "Minimal - just copy",
        "args": ["-c", "copy", "-f", "mpegts"]
    },
    "nobuffer": {
        "desc": "No buffer flags",
        "args": ["-fflags", "+genpts+nobuffer", "-flags", "low_delay",
                 "-c", "copy", "-f", "mpegts"]
    },
    "small_probe": {
        "desc": "Small probesize (100KB/100ms)",
        "input_args": ["-analyzeduration", "100000", "-probesize", "100000"],
        "args": ["-c", "copy", "-f", "mpegts"]
    },
    "tiny_probe": {
        "desc": "Tiny probesize (32KB/0ms) - may fail",
        "input_args": ["-analyzeduration", "0", "-probesize", "32000"],
        "args": ["-c", "copy", "-f", "mpegts"]
    },
    "medium_probe": {
        "desc": "Medium probesize (500KB/500ms)",
        "input_args": ["-analyzeduration", "500000", "-probesize", "500000"],
        "args": ["-c", "copy", "-f", "mpegts"]
    },
    "full_combo": {
        "desc": "Full combo - nobuffer + small probe + flush",
        "input_args": ["-fflags", "+genpts+nobuffer", "-flags", "low_delay",
                       "-analyzeduration", "100000", "-probesize", "100000"],
        "args": ["-c", "copy", "-f", "mpegts", "-flush_packets", "1"]
    },
    "realtime": {
        "desc": "With -re (realtime) flag",
        "input_args": ["-re", "-analyzeduration", "100000", "-probesize", "100000"],
        "args": ["-c", "copy", "-f", "mpegts"]
    },
    "audio_transcode": {
        "desc": "Copy video, transcode audio to AAC",
        "input_args": ["-analyzeduration", "500000", "-probesize", "500000"],
        "args": ["-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-f", "mpegts"]
    },
    "audio_fix": {
        "desc": "Copy video, transcode audio with forced params (fixes 0 channels)",
        "input_args": ["-fflags", "+genpts+nobuffer", "-flags", "low_delay",
                       "-analyzeduration", "100000", "-probesize", "100000"],
        "args": ["-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
                 "-f", "mpegts", "-flush_packets", "1"]
    },
    "video_only": {
        "desc": "Video only, drop audio entirely",
        "input_args": ["-fflags", "+genpts+nobuffer", "-flags", "low_delay",
                       "-analyzeduration", "100000", "-probesize", "100000"],
        "args": ["-map", "0:v", "-c:v", "copy", "-f", "mpegts", "-flush_packets", "1"]
    },
    "igndts": {
        "desc": "Ignore DTS errors",
        "input_args": ["-fflags", "+genpts+igndts", "-err_detect", "ignore_err",
                       "-analyzeduration", "100000", "-probesize", "100000"],
        "args": ["-c", "copy", "-f", "mpegts"]
    },
    "discardcorrupt": {
        "desc": "Discard corrupt packets",
        "input_args": ["-fflags", "+genpts+discardcorrupt",
                       "-analyzeduration", "100000", "-probesize", "100000"],
        "args": ["-c", "copy", "-f", "mpegts", "-flush_packets", "1"]
    },
}

def test_config(name: str, config: dict, url: str, timeout: int = 15) -> dict:
    """Test a single FFmpeg configuration and measure time to first byte."""

    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error"]

    # Add input args before -i
    if "input_args" in config:
        cmd.extend(config["input_args"])

    cmd.extend(["-i", url])
    cmd.extend(config["args"])
    cmd.append("pipe:1")

    print(f"\n{'='*60}")
    print(f"Testing: {name} - {config['desc']}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")

    result = {
        "name": name,
        "desc": config["desc"],
        "success": False,
        "time_to_first_byte": None,
        "bytes_received": 0,
        "error": None
    }

    try:
        start_time = time.time()

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )

        # Wait for first byte with timeout
        first_byte_time = None
        total_bytes = 0

        while time.time() - start_time < timeout:
            # Non-blocking read
            chunk = proc.stdout.read(1024)
            if chunk:
                if first_byte_time is None:
                    first_byte_time = time.time() - start_time
                    print(f"  First byte received after: {first_byte_time:.2f}s")
                total_bytes += len(chunk)

                # Read a bit more to confirm it's working
                if total_bytes > 50000:  # 50KB is enough to confirm
                    break
            else:
                # Check if process died
                if proc.poll() is not None:
                    stderr = proc.stderr.read().decode('utf-8', errors='ignore')
                    result["error"] = stderr[-200:] if stderr else "Process exited with no output"
                    print(f"  FAILED: {result['error']}")
                    break
                time.sleep(0.01)

        # Cleanup
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except:
            proc.kill()

        if first_byte_time is not None:
            result["success"] = True
            result["time_to_first_byte"] = first_byte_time
            result["bytes_received"] = total_bytes
            print(f"  SUCCESS: {total_bytes} bytes in {first_byte_time:.2f}s")
        elif result["error"] is None:
            result["error"] = f"Timeout ({timeout}s) - no data received"
            print(f"  FAILED: {result['error']}")

    except Exception as e:
        result["error"] = str(e)
        print(f"  ERROR: {e}")

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_ffmpeg_startup.py <stream_url> [timeout_seconds]")
        print("\nTo get a stream URL, check the MacReplay logs for lines like:")
        print("  [DEBUG] FFmpeg command: ffmpeg ... -i <URL> ...")
        sys.exit(1)

    url = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 15

    print(f"\nTesting FFmpeg startup times with URL: {url[:80]}...")
    print(f"Timeout per test: {timeout}s\n")

    # Check FFmpeg is available
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except:
        print("ERROR: ffmpeg not found in PATH")
        sys.exit(1)

    # Run all tests
    results = []
    for name, config in CONFIGS.items():
        result = test_config(name, config, url, timeout)
        results.append(result)

    # Summary
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    if successful:
        # Sort by time
        successful.sort(key=lambda x: x["time_to_first_byte"])

        print("\nSUCCESSFUL (sorted by startup time):")
        print("-" * 50)
        for r in successful:
            print(f"  {r['time_to_first_byte']:5.2f}s - {r['name']:20} ({r['desc']})")

        best = successful[0]
        print(f"\n*** RECOMMENDED: {best['name']} ({best['time_to_first_byte']:.2f}s) ***")
        print(f"\nRecommended FFmpeg command for settings:")

        config = CONFIGS[best['name']]
        cmd_parts = ["ffmpeg"]
        if "input_args" in config:
            cmd_parts.extend(config["input_args"])
        cmd_parts.extend(["-i", "<url>"])
        cmd_parts.extend(config["args"])
        cmd_parts.append("pipe:")
        print(f"  {' '.join(cmd_parts)}")

    if failed:
        print(f"\nFAILED ({len(failed)}):")
        print("-" * 50)
        for r in failed:
            err = r['error'][:60] + "..." if len(r['error']) > 60 else r['error']
            print(f"  {r['name']:20} - {err}")


if __name__ == "__main__":
    main()
