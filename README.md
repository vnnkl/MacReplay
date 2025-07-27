# **MacReplay**

MacReplay is an improved version of [STB-Proxy](https://github.com/Chris230291/STB-Proxy), designed for seamless connectivity between MAC address portals and media platforms like Plex or M3U-based software.  

This cross-platform solution works on Windows, Linux, and macOS, with both standalone executable and Python script options for maximum flexibility.

---

## **Features**
- 🛠️ **Cross-Platform**: Works on Windows, Linux, and macOS  
- 🎯 **Enhanced Playlist Editor**: Advanced filtering, duplicate management, and smart autocomplete
- 🔗 **MAC Portal Integration**: Connect MAC address portals directly with Plex or M3U software  
- 🐦‍🔥 **Multiple MACs**: Rotate between MAC addresses across a single portal, allowing for multiple connections simultaneously  
- 🦕 **Multiple Portals**: Add multiple portal URLs to get channels from different providers in the same playlist
- 🚀 **Smart Fallback System**: Automatic failover to backup channels when primary streams fail
- 📊 **Intelligent Duplicate Detection**: Only considers enabled channels as duplicates for cleaner management
- 🎮 **One-Click Duplicate Cleanup**: Remove duplicate enabled channels while preserving the first occurrence
- 🔍 **Multi-Level Filtering**: Portal, Genre, and Duplicate filters work together for precise channel selection
- ✨ **Autocomplete Fallbacks**: Smart suggestions for setting up channel failover systems

---

## **Enhanced Playlist Editor**

The playlist editor features a completely redesigned interface with powerful management tools:

### 🎯 **Advanced Filtering System**
- **Portal Filter**: Isolate channels from specific portals for focused management
- **Genre Filter**: Filter by Sports, Movies, News, Entertainment, and more
- **Enabled Duplicates Filter**: Show only channels with multiple enabled instances
- **Combined Filtering**: All filters work together for laser-focused channel selection
- **Real-time Search**: Built-in text search across all channel names

### 🔄 **Smart Duplicate Management**
- **Enabled-Only Detection**: Only counts active channels as duplicates (ignores disabled channels)
- **Visual Highlighting**: Duplicate enabled channels highlighted in yellow for easy identification
- **Count Badges**: Shows "3x enabled" indicators next to channel names with multiple instances
- **One-Click Cleanup**: "Deactivate Enabled Duplicates" button keeps first occurrence, removes the rest
- **Intelligent Logic**: Focuses on channels you're actually using, not all available channels

### 🎮 **Fallback Channel System**
- **Autocomplete Dropdown**: Type or click to see all available channel names for easy selection
- **Cross-Portal Fallbacks**: Set backup channels from any portal to cover for any other channel
- **Smart Suggestions**: Dropdown populated with all channel names (including custom names)
- **Seamless Failover**: When primary channel fails, automatically switches to designated backup
- **Example Use**: Set "ESPN SD" as fallback for "ESPN HD" - viewers get uninterrupted content

### ⚡ **Enhanced User Experience**
- **Auto-Loading Data**: Channels load automatically when page opens (no manual refresh needed)
- **DataTables Integration**: Professional table with sorting, pagination, and bulk actions
- **Real-Time Updates**: All filters and changes apply instantly without page reloads
- **Bulk Operations**: Select All checkbox for mass enable/disable operations
- **Persistent Settings**: All configurations saved automatically for future sessions

---

## **Requirements**
- **Python 3.7+** (for Python script) or download pre-built executable
- **FFmpeg** installed on your system  
- **Plex Pass** (if connecting to Plex) - *may no longer be required with recent Plex updates*

### **Platform-Specific Setup**
- **Windows**: Download `.exe` or install Python + FFmpeg
- **Linux**: Install Python, pip, and FFmpeg via package manager
- **macOS**: Install via Homebrew or download pre-built executable

---

## **Getting Started**

### **Option 1: Pre-built Executable**
1. **Download** the latest release for your platform from the [Releases page](https://github.com/Evilvir-us/MacReplay/releases)
2. **Run** the executable
3. **Open** your browser to the server URL shown in console

### **Option 2: Python Script**
1. **Clone** or download this repository
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Run**: `python3 app.py`
4. **Open** your browser to `http://localhost:13681`

### **Configuration Workflow**
1. **Add Portals**: Go to Portals page and add your portal URLs and MAC addresses
2. **Configure Channels**: Use the enhanced Playlist Editor to:
   - Filter channels by portal or genre
   - Enable/disable channels with checkboxes
   - Set up custom channel names and numbers
   - Configure fallback channels for reliability
   - Remove duplicate channels with one click
3. **Setup Plex**: 
   - In Plex settings, go to *Live TV and DVR*
   - Click *Set Up Plex Tuner*
   - Select *Have an XMLTV guide*
   - Enter: `http://YOUR_SERVER_IP:13681/xmltv`
   - Use playlist: `http://YOUR_SERVER_IP:13681/playlist.m3u`

---

## **Playlist Editor Guide**

### **Managing Large Channel Lists**
1. **Filter by Portal**: Select specific portal to focus on its channels
2. **Filter by Genre**: Show only Sports, Movies, News, etc.
3. **Search**: Type channel names to find specific channels quickly
4. **Bulk Actions**: Use "Select All" checkbox for mass enable/disable

### **Setting Up Fallbacks**
1. **Find backup channel**: Use filters to locate a reliable backup (e.g., "ESPN SD")
2. **Configure fallback**: In the backup channel's "Fallback For" field, type or select the primary channel name (e.g., "ESPN HD")
3. **Automatic failover**: If "ESPN HD" fails, viewers automatically get "ESPN SD"

### **Duplicate Channel Cleanup**
1. **View duplicates**: Select "Enabled Duplicates Only" filter
2. **Review highlighted channels**: Yellow rows show duplicate enabled channels
3. **One-click cleanup**: Click "Deactivate Enabled Duplicates" to keep only the first occurrence
4. **Manual selection**: Or manually uncheck unwanted duplicates

---

## **Troubleshooting**
**The TV guide is not being populated:**\
Check the [XMLTV guide](http://localhost:13681/xmltv).
If it just shows the list of channels with nothing below them, the provider likely does not supply a guide.
Try switching to a different provider.

**I've modified the channels, but Plex isn't changing:**\
You must delete the DVR from Plex and re-add it to see changes.

**Error getting channel data for [Portal], skipping** or **Error making XMLTV for [Portal], skipping:**\
Go to the Portals page, select the malfunctioning portal and click "Retest". You likely have an expired MAC address.

**Channels not loading in editor:**\
Ensure your portals are configured correctly and MAC addresses are valid. Check the Dashboard logs for specific errors.

**Duplicate detection not working:**\
The system only considers enabled channels as duplicates. Disable a channel to remove it from duplicate detection.

---

## **Known Issues**

Channel logos may not display when viewed in a browser. This is likely due to your browser's security settings related to HTTP files being served on an HTTPS domain.\
![Chrome](https://evilvir.us/application/files/2917/3318/2580/chrome_https_issue.png)
![Firefox](https://evilvir.us/application/files/9217/3318/2583/firefox_https_issue.png)

This issue does not occur with [PLEX HTPC](https://apps.microsoft.com/store/detail/XPFFFF6NN1LZDQ?ocid=pdpshare), the mobile apps, or the TV app. To watch from a PC, use [PLEX HTPC](https://apps.microsoft.com/store/detail/XPFFFF6NN1LZDQ?ocid=pdpshare). If any logos are still missing, it means the provider isn't supplying them.

For Plex HTPC, you must enable **Force Direct Play** in the settings.
![HTPC Settings](https://evilvir.us/application/files/5117/3368/8848/htpcsettings.png)

---

## **Credits**
MacReplay is based on the incredible work done by [Chris230291](https://github.com/Chris230291) with the original [STB-Proxy](https://github.com/Chris230291/STB-Proxy).  

---

## **Disclaimer**
This tool is provided as-is and is intended for educational purposes only. Use responsibly and in compliance with applicable laws and terms of service.
