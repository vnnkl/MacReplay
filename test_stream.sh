#!/bin/bash
# Stream Testing Script

if [ -z "$1" ]; then
    echo "Usage: $0 <server_url> [channel_id]"
    echo "Example: $0 http://localhost:5004 694588"
    exit 1
fi

SERVER="$1"
CHANNEL="${2:-694588}"
PORTAL="31375c8a4ecd41598023d8b4de6bbef5"

STREAM_URL="${SERVER}/${PORTAL}/${CHANNEL}/master.m3u8"

echo "Testing stream: $STREAM_URL"
echo ""
echo "1. Testing with ffprobe (check stream info):"
ffprobe -v error -show_format -show_streams "$STREAM_URL" 2>&1 | head -50

echo ""
echo "2. Testing with ffplay (5 second playback test):"
timeout 5 ffplay -v error -stats "$STREAM_URL" -autoexit 2>&1

echo ""
echo "3. Testing with curl (check if master playlist is accessible):"
curl -v "$STREAM_URL" 2>&1 | head -30

echo ""
echo "4. Done!"
