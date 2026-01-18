# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MacReplay is a cross-platform proxy service bridging MAC address-based IPTV portals with media platforms like Plex or M3U software. Enhanced version of STB-Proxy with playlist management, fallback systems, and HLS streaming.

**Stack**: Python 3.7+ / Flask 3.0 / SQLite / FFmpeg

## Commands

```bash
# Install
pip install -r requirements.txt

# Run
python3 app.py          # Starts on http://localhost:13681

# Test
pytest                  # All tests
pytest -v               # Verbose
pytest tests/test_app.py  # Single file
pytest -k "test_name"   # Single test
```

## Architecture

### Core Files
- `app.py` - Main Flask app, all routes, HLSStreamManager class
- `stb.py` - STB portal communication (auth, channel fetch, stream URLs)

### Key Classes
- **HLSStreamManager** (app.py:177-586): Manages concurrent HLS streams with pooling, auto-cleanup, and background monitoring

### Data Flow
1. Portals configured via web UI → stored in `~/.evilvir.us/MacReplay.json`
2. Channels cached in SQLite (`~/.evilvir.us/channels.db`) for performance
3. Playlist requests read from DB, not live portal calls
4. Streaming: get token → fetch stream URL → FFmpeg transcode → serve

### Important Routes
| Route | Purpose |
|-------|---------|
| `/play/<portalId>/<channelId>` | MPEG-TS stream |
| `/hls/<portalId>/<channelId>/<filename>` | HLS segments |
| `/playlist.m3u` | M3U playlist |
| `/xmltv` | EPG guide |
| `/api/editor_data` | Paginated channel list |
| `/discover.json`, `/lineup.json` | Plex compatibility |

### Database Schema
```sql
channels (
    portal TEXT, channel_id TEXT,  -- composite PK
    name, number, genre, logo,
    enabled INTEGER DEFAULT 0,
    custom_name, custom_number, custom_genre,
    custom_epg_id, fallback_channel
)
```

## Key Patterns

- **MAC Rotation**: Multiple MACs per portal enable concurrent streams
- **Fallback Channels**: Primary failure → automatic backup channel
- **Server-Side Pagination**: DataTables format, 250 channels/page
- **Thread-Safe HLS**: Locks in HLSStreamManager for concurrent access

## Testing

Tests use pytest-mock with fixtures in `tests/conftest.py`:
- `client` - Flask test client
- `mock_config` - Mocked settings/portals
- `mock_db_with_channels` - Mock database with test data

Test files: `test_app.py`, `test_stb.py`, `test_hls_manager.py`, `test_ffmpeg_command_generation.py`, `test_editor_filters.py`, `test_dropdown_population.py`

## File Locations

- Config: `~/.evilvir.us/MacReplay.json`
- Database: `~/.evilvir.us/channels.db`
- Logs: `~/.Evilvir.us/MacReplay.log`
