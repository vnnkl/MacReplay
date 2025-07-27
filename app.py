import sys
import os
import shutil
import time
import subprocess
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import threading
from threading import Thread
import logging
logger = logging.getLogger("MacReplay")
logger.setLevel(logging.INFO)
logFormat = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")


home_dir = os.path.expanduser("~")  # Get the user's home directory
log_dir = os.path.join(home_dir, "Evilvir.us")  # Subdirectory for logs
# Create the directory if it doesn't already exist
os.makedirs(log_dir, exist_ok=True)
# Full path to the log file
log_file_path = os.path.join(log_dir, "MacReplay.log")
# Set up the FileHandler
fileHandler = logging.FileHandler(log_file_path)
fileHandler.setFormatter(logFormat)

logger.addHandler(fileHandler)
consoleFormat = logging.Formatter("[%(levelname)s] %(message)s")
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(consoleFormat)
logger.addHandler(consoleHandler)

# Use system-installed ffmpeg and ffprobe (like STB-Proxy does)
# Check if the binaries exist
try:
    subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
    logger.info("FFmpeg and FFprobe found and working")
except (subprocess.CalledProcessError, FileNotFoundError):
    logger.error("Error: ffmpeg or ffprobe not found! Please install ffmpeg.")

import flask
from flask import Flask, jsonify
import stb
import json
import subprocess
import uuid
import xml.etree.cElementTree as ET
from flask import (
    Flask,
    render_template,
    redirect,
    request,
    Response,
    make_response,
    flash,
)
from datetime import datetime, timezone
from functools import wraps
import secrets
import waitress

app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(32)


basePath = os.path.abspath(os.getcwd())

if os.getenv("HOST"):
    host = os.getenv("HOST")
else:
    host = "ubuntu.verbergwest.appboxes.co:13681"
logger.info(f"Server started on http://{host}")

# Get the base path for the user directory
basePath = os.path.expanduser("~")

# Determine the config file path, placing it in 'evilvir.us' subdirectory
if os.getenv("CONFIG"):
    configFile = os.getenv("CONFIG")
else:
    configFile = os.path.join(basePath, "evilvir.us", "MacReplay.json")

# Ensure the subdirectory exists
os.makedirs(os.path.dirname(configFile), exist_ok=True)

logger.info(f"Using config file: {configFile}")

occupied = {}
config = {}
cached_lineup = []
cached_playlist = None
last_playlist_host = None
cached_xmltv = None
last_updated = 0


d_ffmpegcmd = [
    "-re",                      # Flag for real-time streaming
    "-http_proxy", "<proxy>",   # Proxy setting
    "-timeout", "<timeout>",    # Timeout setting
    "-i", "<url>",              # Input URL
    "-map", "0",                # Map all streams
    "-codec", "copy",           # Copy codec (no re-encoding)
    "-f", "mpegts",             # Output format
    "-flush_packets", "0",      # Disable flushing packets (optimized for faster output)
    "-fflags", "+nobuffer",     # No buffering for low latency
    "-flags", "low_delay",      # Low delay flag
    "-strict", "experimental",  # Use experimental features
    "-analyzeduration", "0",    # Skip analysis duration for faster startup
    "-probesize", "32",         # Set probe size to reduce input analysis time
    "-copyts",                  # Copy timestamps (avoid recalculating)
    "-threads", "12",           # Enable multi-threading (adjust thread count as needed)
    "pipe:"                     # Output to pipe
]







defaultSettings = {
    "stream method": "ffmpeg",
    "ffmpeg command": "-re -http_proxy <proxy> -timeout <timeout> -i <url> -map 0 -codec copy -f mpegts -flush_packets 0 -fflags +nobuffer -flags low_delay -strict experimental -analyzeduration 0 -probesize 32 -copyts -threads 12 pipe:",
    "ffmpeg timeout": "5",
    "test streams": "true",
    "try all macs": "true",
    "use channel genres": "true",
    "use channel numbers": "true",
    "sort playlist by channel genre": "false",
    "sort playlist by channel number": "true",
    "sort playlist by channel name": "false",
    "enable security": "false",
    "username": "admin",
    "password": "12345",
    "enable hdhr": "true",
    "hdhr name": "MacReplay",
    "hdhr id": str(uuid.uuid4().hex),
    "hdhr tuners": "10",
}

defaultPortal = {
    "enabled": "true",
    "name": "",
    "url": "",
    "macs": {},
    "streams per mac": "1",
    "epg offset": "0",
    "proxy": "",
    "enabled channels": [],
    "custom channel names": {},
    "custom channel numbers": {},
    "custom genres": {},
    "custom epg ids": {},
    "fallback channels": {},
}


def loadConfig():
    try:
        with open(configFile) as f:
            data = json.load(f)
    except:
        logger.warning("No existing config found. Creating a new one")
        data = {}

    data.setdefault("portals", {})
    data.setdefault("settings", {})

    settings = data["settings"]
    settingsOut = {}

    for setting, default in defaultSettings.items():
        value = settings.get(setting)
        if not value or type(default) != type(value):
            value = default
        settingsOut[setting] = value

    data["settings"] = settingsOut

    portals = data["portals"]
    portalsOut = {}

    for portal in portals:
        portalsOut[portal] = {}
        for setting, default in defaultPortal.items():
            value = portals[portal].get(setting)
            if not value or type(default) != type(value):
                value = default
            portalsOut[portal][setting] = value

    data["portals"] = portalsOut

    with open(configFile, "w") as f:
        json.dump(data, f, indent=4)

    return data


def getPortals():
    return config["portals"]


def savePortals(portals):
    with open(configFile, "w") as f:
        config["portals"] = portals
        json.dump(config, f, indent=4)


def getSettings():
    return config["settings"]


def saveSettings(settings):
    with open(configFile, "w") as f:
        config["settings"] = settings
        json.dump(config, f, indent=4)


def authorise(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        settings = getSettings()
        security = settings["enable security"]
        username = settings["username"]
        password = settings["password"]
        if (
            security == "false"
            or auth
            and auth.username == username
            and auth.password == password
        ):
            return f(*args, **kwargs)

        return make_response(
            "Could not verify your login!",
            401,
            {"WWW-Authenticate": 'Basic realm="Login Required"'},
        )

    return decorated


def moveMac(portalId, mac):
    portals = getPortals()
    macs = portals[portalId]["macs"]
    x = macs[mac]
    del macs[mac]
    macs[mac] = x
    portals[portalId]["macs"] = macs
    savePortals(portals)


@app.route("/", methods=["GET"])
@authorise
def home():
    return redirect("/portals", code=302)


@app.route("/portals", methods=["GET"])
@authorise
def portals():
    return render_template("portals.html", portals=getPortals())


@app.route("/portal/add", methods=["POST"])
@authorise
def portalsAdd():
    global cached_xmltv
    cached_xmltv = None
    id = uuid.uuid4().hex
    enabled = "true"
    name = request.form["name"]
    url = request.form["url"]
    macs = list(set(request.form["macs"].split(",")))
    streamsPerMac = request.form["streams per mac"]
    epgOffset = request.form["epg offset"]
    proxy = request.form["proxy"]

    if not url.endswith(".php"):
        url = stb.getUrl(url, proxy)
        if not url:
            logger.error("Error getting URL for Portal({})".format(name))
            flash("Error getting URL for Portal({})".format(name), "danger")
            return redirect("/portals", code=302)

    macsd = {}

    for mac in macs:
        token = stb.getToken(url, mac, proxy)
        if token:
            stb.getProfile(url, mac, token, proxy)
            expiry = stb.getExpires(url, mac, token, proxy)
            if expiry:
                macsd[mac] = expiry
                logger.info(
                    "Successfully tested MAC({}) for Portal({})".format(mac, name)
                )
                flash(
                    "Successfully tested MAC({}) for Portal({})".format(mac, name),
                    "success",
                )
                continue

        logger.error("Error testing MAC({}) for Portal({})".format(mac, name))
        flash("Error testing MAC({}) for Portal({})".format(mac, name), "danger")

    if len(macsd) > 0:
        portal = {
            "enabled": enabled,
            "name": name,
            "url": url,
            "macs": macsd,
            "streams per mac": streamsPerMac,
            "epg offset": epgOffset,
            "proxy": proxy,
        }

        for setting, default in defaultPortal.items():
            if not portal.get(setting):
                portal[setting] = default

        portals = getPortals()
        portals[id] = portal
        savePortals(portals)
        logger.info("Portal({}) added!".format(portal["name"]))

    else:
        logger.error(
            "None of the MACs tested OK for Portal({}). Adding not successfull".format(
                name
            )
        )

    return redirect("/portals", code=302)


@app.route("/portal/update", methods=["POST"])
@authorise
def portalUpdate():
    global cached_xmltv
    cached_xmltv = None
    id = request.form["id"]
    enabled = request.form.get("enabled", "false")
    name = request.form["name"]
    url = request.form["url"]
    newmacs = list(set(request.form["macs"].split(",")))
    streamsPerMac = request.form["streams per mac"]
    epgOffset = request.form["epg offset"]
    proxy = request.form["proxy"]
    retest = request.form.get("retest", None)

    if not url.endswith(".php"):
        url = stb.getUrl(url, proxy)
        if not url:
            logger.error("Error getting URL for Portal({})".format(name))
            flash("Error getting URL for Portal({})".format(name), "danger")
            return redirect("/portals", code=302)

    portals = getPortals()
    oldmacs = portals[id]["macs"]
    macsout = {}
    deadmacs = []

    for mac in newmacs:
        if retest or mac not in oldmacs.keys():
            token = stb.getToken(url, mac, proxy)
            if token:
                stb.getProfile(url, mac, token, proxy)
                expiry = stb.getExpires(url, mac, token, proxy)
                if expiry:
                    macsout[mac] = expiry
                    logger.info(
                        "Successfully tested MAC({}) for Portal({})".format(mac, name)
                    )
                    flash(
                        "Successfully tested MAC({}) for Portal({})".format(mac, name),
                        "success",
                    )

            if mac not in list(macsout.keys()):
                deadmacs.append(mac)

        if mac in oldmacs.keys() and mac not in deadmacs:
            macsout[mac] = oldmacs[mac]

        if mac not in macsout.keys():
            logger.error("Error testing MAC({}) for Portal({})".format(mac, name))
            flash("Error testing MAC({}) for Portal({})".format(mac, name), "danger")

    if len(macsout) > 0:
        portals[id]["enabled"] = enabled
        portals[id]["name"] = name
        portals[id]["url"] = url
        portals[id]["macs"] = macsout
        portals[id]["streams per mac"] = streamsPerMac
        portals[id]["epg offset"] = epgOffset
        portals[id]["proxy"] = proxy
        savePortals(portals)
        logger.info("Portal({}) updated!".format(name))
        flash("Portal({}) updated!".format(name), "success")

    else:
        logger.error(
            "None of the MACs tested OK for Portal({}). Adding not successfull".format(
                name
            )
        )

    return redirect("/portals", code=302)


@app.route("/portal/remove", methods=["POST"])
@authorise
def portalRemove():
    id = request.form["deleteId"]
    portals = getPortals()
    name = portals[id]["name"]
    del portals[id]
    savePortals(portals)
    logger.info("Portal ({}) removed!".format(name))
    flash("Portal ({}) removed!".format(name), "success")
    return redirect("/portals", code=302)


@app.route("/editor", methods=["GET"])
@authorise
def editor():
    return render_template("editor.html")
    


@app.route("/editor_data", methods=["GET"])
@authorise
def editor_data():
    channels = []
    portals = getPortals()
    for portal in portals:
        logger.info(f"getting Data from {portal}")
        if portals[portal]["enabled"] == "true":
            portalName = portals[portal]["name"]
            url = portals[portal]["url"]
            macs = list(portals[portal]["macs"].keys())
            proxy = portals[portal]["proxy"]
            enabledChannels = portals[portal].get("enabled channels", [])
            customChannelNames = portals[portal].get("custom channel names", {})
            customGenres = portals[portal].get("custom genres", {})
            customChannelNumbers = portals[portal].get("custom channel numbers", {})
            customEpgIds = portals[portal].get("custom epg ids", {})
            fallbackChannels = portals[portal].get("fallback channels", {})

            for mac in macs:
                logger.info(f"Using mac: {mac}")
                try:
                    token = stb.getToken(url, mac, proxy)
                    stb.getProfile(url, mac, token, proxy)
                    allChannels = stb.getAllChannels(url, mac, token, proxy)
                    genres = stb.getGenreNames(url, mac, token, proxy)
                    break
                except:
                    allChannels = None
                    genres = None

            if allChannels and genres:
                for channel in allChannels:
                    channelId = str(channel["id"])
                    channelName = str(channel["name"])
                    channelNumber = str(channel["number"])
                    genre = str(genres.get(str(channel["tv_genre_id"])))
                    if channelId in enabledChannels:
                        enabled = True
                    else:
                        enabled = False
                    customChannelNumber = customChannelNumbers.get(channelId)
                    if customChannelNumber == None:
                        customChannelNumber = ""
                    customChannelName = customChannelNames.get(channelId)
                    if customChannelName == None:
                        customChannelName = ""
                    customGenre = customGenres.get(channelId)
                    if customGenre == None:
                        customGenre = ""
                    customEpgId = customEpgIds.get(channelId)
                    if customEpgId == None:
                        customEpgId = ""
                    fallbackChannel = fallbackChannels.get(channelId)
                    if fallbackChannel == None:
                        fallbackChannel = ""
                    channels.append(
                        {
                            "portal": portal,
                            "portalName": portalName,
                            "enabled": enabled,
                            "channelNumber": channelNumber,
                            "customChannelNumber": customChannelNumber,
                            "channelName": channelName,
                            "customChannelName": customChannelName,
                            "genre": genre,
                            "customGenre": customGenre,
                            "channelId": channelId,
                            "customEpgId": customEpgId,
                            "fallbackChannel": fallbackChannel,
                            "link": "http://"
                            + host
                            + "/play/"
                            + portal
                            + "/"
                            + channelId
                            + "?web=true",
                        }
                    )
            else:
                logger.error(
                    "Error getting channel data for {}, skipping".format(portalName)
                )
                flash(
                    "Error getting channel data for {}, skipping".format(portalName),
                    "danger",
                )

    data = {"data": channels}

    return flask.jsonify(data)


@app.route("/editor/save", methods=["POST"])
@authorise
def editorSave():
    global cached_xmltv
    #cached_xmltv = None # The tv guide will be updated next time its downloaded
    threading.Thread(target=refresh_xmltv, daemon=True).start() #Force update in a seperate thread
    last_playlist_host = None     # The playlist will be updated next time it is downloaded
    Thread(target=refresh_lineup).start() # Update the channel lineup for plex.
    enabledEdits = json.loads(request.form["enabledEdits"])
    numberEdits = json.loads(request.form["numberEdits"])
    nameEdits = json.loads(request.form["nameEdits"])
    genreEdits = json.loads(request.form["genreEdits"])
    epgEdits = json.loads(request.form["epgEdits"])
    fallbackEdits = json.loads(request.form["fallbackEdits"])
    portals = getPortals()
    for edit in enabledEdits:
        portal = edit["portal"]
        channelId = edit["channel id"]
        enabled = edit["enabled"]
        if enabled:
            portals[portal].setdefault("enabled channels", [])
            portals[portal]["enabled channels"].append(channelId)
        else:
            portals[portal]["enabled channels"] = list(
                filter((channelId).__ne__, portals[portal]["enabled channels"])
            )

    for edit in numberEdits:
        portal = edit["portal"]
        channelId = edit["channel id"]
        customNumber = edit["custom number"]
        if customNumber:
            portals[portal].setdefault("custom channel numbers", {})
            portals[portal]["custom channel numbers"].update({channelId: customNumber})
        else:
            portals[portal]["custom channel numbers"].pop(channelId)

    for edit in nameEdits:
        portal = edit["portal"]
        channelId = edit["channel id"]
        customName = edit["custom name"]
        if customName:
            portals[portal].setdefault("custom channel names", {})
            portals[portal]["custom channel names"].update({channelId: customName})
        else:
            portals[portal]["custom channel names"].pop(channelId)

    for edit in genreEdits:
        portal = edit["portal"]
        channelId = edit["channel id"]
        customGenre = edit["custom genre"]
        if customGenre:
            portals[portal].setdefault("custom genres", {})
            portals[portal]["custom genres"].update({channelId: customGenre})
        else:
            portals[portal]["custom genres"].pop(channelId)

    for edit in epgEdits:
        portal = edit["portal"]
        channelId = edit["channel id"]
        customEpgId = edit["custom epg id"]
        if customEpgId:
            portals[portal].setdefault("custom epg ids", {})
            portals[portal]["custom epg ids"].update({channelId: customEpgId})
        else:
            portals[portal]["custom epg ids"].pop(channelId)

    for edit in fallbackEdits:
        portal = edit["portal"]
        channelId = edit["channel id"]
        channelName = edit["channel name"]
        if channelName:
            portals[portal].setdefault("fallback channels", {})
            portals[portal]["fallback channels"].update({channelId: channelName})
        else:
            portals[portal]["fallback channels"].pop(channelId)

    savePortals(portals)
    logger.info("Playlist config saved!")
    flash("Playlist config saved!", "success")
    return redirect("/editor", code=302)


@app.route("/editor/reset", methods=["POST"])
@authorise
def editorReset():
    portals = getPortals()
    for portal in portals:
        portals[portal]["enabled channels"] = []
        portals[portal]["custom channel numbers"] = {}
        portals[portal]["custom channel names"] = {}
        portals[portal]["custom genres"] = {}
        portals[portal]["custom epg ids"] = {}
        portals[portal]["fallback channels"] = {}

    savePortals(portals)
    logger.info("Playlist reset!")
    flash("Playlist reset!", "success")
    return redirect("/editor", code=302)


@app.route("/settings", methods=["GET"])
@authorise
def settings():
    settings = getSettings()
    return render_template(
        "settings.html", settings=settings, defaultSettings=defaultSettings
    )


@app.route("/settings/save", methods=["POST"])
@authorise
def save():
    settings = {}

    for setting, _ in defaultSettings.items():
        value = request.form.get(setting, "false")
        settings[setting] = value

    saveSettings(settings)
    logger.info("Settings saved!")
    Thread(target=refresh_xmltv).start()
    flash("Settings saved!", "success")
    return redirect("/settings", code=302)

# Route to serve the cached playlist.m3u
@app.route("/playlist.m3u", methods=["GET"])
@authorise
def playlist():
    global cached_playlist, last_playlist_host
    
    logger.info("Playlist Requested")
    
    # Detect the current host dynamically
    current_host = host
    
    # Regenerate the playlist if it is empty or the host has changed
    if cached_playlist is None or len(cached_playlist) == 0 or last_playlist_host != current_host:
        logger.info(f"Regenerating playlist due to host change: {last_playlist_host} -> {current_host}")
        last_playlist_host = current_host
        generate_playlist()

    return Response(cached_playlist, mimetype="text/plain")

# Function to manually trigger playlist update
@app.route("/update_playlistm3u", methods=["POST"])
def update_playlistm3u():
    generate_playlist()
    return Response("Playlist updated successfully", status=200)

def generate_playlist():
    global cached_playlist
    logger.info("Generating playlist.m3u...")

    # Detect the host dynamically from the request
    playlist_host = host
    
    channels = []
    portals = getPortals()

    for portal in portals:
        if portals[portal]["enabled"] == "true":
            enabledChannels = portals[portal].get("enabled channels", [])
            if len(enabledChannels) != 0:
                name = portals[portal]["name"]
                url = portals[portal]["url"]
                macs = list(portals[portal]["macs"].keys())
                proxy = portals[portal]["proxy"]
                customChannelNames = portals[portal].get("custom channel names", {})
                customGenres = portals[portal].get("custom genres", {})
                customChannelNumbers = portals[portal].get("custom channel numbers", {})
                customEpgIds = portals[portal].get("custom epg ids", {})

                for mac in macs:
                    try:
                        token = stb.getToken(url, mac, proxy)
                        stb.getProfile(url, mac, token, proxy)
                        allChannels = stb.getAllChannels(url, mac, token, proxy)
                        genres = stb.getGenreNames(url, mac, token, proxy)
                        break
                    except:
                        allChannels = None
                        genres = None

                if allChannels and genres:
                    for channel in allChannels:
                        channelId = str(channel.get("id"))
                        if channelId in enabledChannels:
                            channelName = customChannelNames.get(channelId)
                            if channelName is None:
                                channelName = str(channel.get("name"))
                            genre = customGenres.get(channelId)
                            if genre is None:
                                genreId = str(channel.get("tv_genre_id"))
                                genre = str(genres.get(genreId))
                            channelNumber = customChannelNumbers.get(channelId)
                            if channelNumber is None:
                                channelNumber = str(channel.get("number"))
                            epgId = customEpgIds.get(channelId)
                            if epgId is None:
                                epgId = channelName
                            channels.append(
                                "#EXTINF:-1"
                                + ' tvg-id="'
                                + epgId
                                + (
                                    '" tvg-chno="' + channelNumber
                                    if getSettings().get("use channel numbers", "true")
                                    == "true"
                                    else ""
                                )
                                + (
                                    '" group-title="' + genre
                                    if getSettings().get("use channel genres", "true")
                                    == "true"
                                    else ""
                                )
                                + '",'
                                + channelName
                                + "\n"
                                + "http://"
                                + playlist_host  # Use the dynamically detected playlist host
                                + "/play/"
                                + portal
                                + "/"
                                + channelId
                            )
                else:
                    logger.error("Error making playlist for {}, skipping".format(name))

    # Sorting the playlist based on settings
    if getSettings().get("sort playlist by channel name", "true") == "true":
        channels.sort(key=lambda k: k.split(",")[1].split("\n")[0])
    if getSettings().get("use channel numbers", "true") == "true":
        if getSettings().get("sort playlist by channel number", "false") == "true":
            channels.sort(key=lambda k: k.split('tvg-chno="')[1].split('"')[0])
    if getSettings().get("use channel genres", "true") == "true":
        if getSettings().get("sort playlist by channel genre", "false") == "true":
            channels.sort(key=lambda k: k.split('group-title="')[1].split('"')[0])

    playlist = "#EXTM3U \n"
    playlist = playlist + "\n".join(channels)

    # Update the cache
    cached_playlist = playlist
    logger.info("Playlist generated and cached.")
    
def refresh_xmltv():
    settings = getSettings()
    logger.info("Refreshing XMLTV...")

    # Set up paths for XMLTV cache
    user_dir = os.path.expanduser("~")
    cache_dir = os.path.join(user_dir, "Evilvir.us")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "MacReplayEPG.xml")

    # Define date cutoff for programme filtering
    day_before_yesterday = datetime.utcnow() - timedelta(days=2)
    day_before_yesterday_str = day_before_yesterday.strftime("%Y%m%d%H%M%S") + " +0000"

    # Load existing cache if it exists
    cached_programmes = []
    if os.path.exists(cache_file):
        try:
            tree = ET.parse(cache_file)
            root = tree.getroot()
            for programme in root.findall("programme"):
                stop_attr = programme.get("stop")  # Get the 'stop' attribute
                if stop_attr:
                    try:
                        # Parse the stop time and compare with the cutoff
                        stop_time = datetime.strptime(stop_attr.split(" ")[0], "%Y%m%d%H%M%S")
                        if stop_time >= day_before_yesterday:  # Keep only recent programmes
                            cached_programmes.append(ET.tostring(programme, encoding="unicode"))
                    except ValueError as e:
                        logger.warning(f"Invalid stop time format in cached programme: {stop_attr}. Skipping.")
            logger.info("Loaded existing programme data from cache.")
        except Exception as e:
            logger.error(f"Failed to load cache file: {e}")

    # Initialize new XMLTV data
    channels = ET.Element("tv")
    programmes = ET.Element("tv")
    portals = getPortals()

    for portal in portals:
        if portals[portal]["enabled"] == "true":
            portal_name = portals[portal]["name"]
            portal_epg_offset = int(portals[portal]["epg offset"])
            logger.info(f"Fetching EPG | Portal: {portal_name} | offset: {portal_epg_offset} |")

            enabledChannels = portals[portal].get("enabled channels", [])
            if len(enabledChannels) != 0:
                name = portals[portal]["name"]
                url = portals[portal]["url"]
                macs = list(portals[portal]["macs"].keys())
                proxy = portals[portal]["proxy"]
                customChannelNames = portals[portal].get("custom channel names", {})
                customEpgIds = portals[portal].get("custom epg ids", {})
                customChannelNumbers = portals[portal].get("custom channel numbers", {})

                for mac in macs:
                    try:
                        token = stb.getToken(url, mac, proxy)
                        stb.getProfile(url, mac, token, proxy)
                        allChannels = stb.getAllChannels(url, mac, token, proxy)
                        epg = stb.getEpg(url, mac, token, 24, proxy)
                        break
                    except Exception as e:
                        allChannels = None
                        epg = None
                        logger.error(f"Error fetching data for MAC {mac}: {e}")

                if allChannels and epg:
                    for channel in allChannels:
                        try:
                            channelId = str(channel.get("id"))
                            if str(channelId) in enabledChannels:
                                channelName = customChannelNames.get(channelId, channel.get("name"))
                                channelNumber = customChannelNumbers.get(channelId, str(channel.get("number")))
                                epgId = customEpgIds.get(channelId, channelNumber)

                                channelEle = ET.SubElement(
                                    channels, "channel", id=epgId
                                )
                                ET.SubElement(channelEle, "display-name").text = channelName
                                ET.SubElement(channelEle, "icon", src=channel.get("logo"))

                                if channelId not in epg or not epg.get(channelId):
                                    logger.warning(f"No EPG data found for channel {channelName} (ID: {channelId}), Creating a Dummy EPG item.")
                                    start_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
                                    stop_time = start_time + timedelta(hours=24)
                                    start = start_time.strftime("%Y%m%d%H%M%S") + " +0000"
                                    stop = stop_time.strftime("%Y%m%d%H%M%S") + " +0000"
                                    programmeEle = ET.SubElement(
                                        programmes,
                                        "programme",
                                        start=start,
                                        stop=stop,
                                        channel=epgId,
                                    )
                                    ET.SubElement(programmeEle, "title").text = channelName
                                    ET.SubElement(programmeEle, "desc").text = channelName
                                else:
                                    for p in epg.get(channelId):
                                        try:
                                            start_time = datetime.utcfromtimestamp(p.get("start_timestamp")) + timedelta(hours=portal_epg_offset)
                                            stop_time = datetime.utcfromtimestamp(p.get("stop_timestamp")) + timedelta(hours=portal_epg_offset)
                                            start = start_time.strftime("%Y%m%d%H%M%S") + " +0000"
                                            stop = stop_time.strftime("%Y%m%d%H%M%S") + " +0000"
                                            if start <= day_before_yesterday_str:
                                                continue
                                            programmeEle = ET.SubElement(
                                                programmes,
                                                "programme",
                                                start=start,
                                                stop=stop,
                                                channel=epgId,
                                            )
                                            ET.SubElement(programmeEle, "title").text = p.get("name")
                                            ET.SubElement(programmeEle, "desc").text = p.get("descr")
                                        except Exception as e:
                                            logger.error(f"Error processing programme for channel {channelName} (ID: {channelId}): {e}")
                                            pass
                        except Exception as e:
                            logger.error(f"| Channel:{channelNumber} | {channelName} | {e}")
                            pass
                else:
                    logger.error(f"Error making XMLTV for {name}, skipping")

    # Combine channels and programmes into a single XML document
    xmltv = channels
    for programme in programmes.iter("programme"):
        xmltv.append(programme)

    # Add cached programmes, ensuring no duplicates
    existing_programme_hashes = {ET.tostring(p, encoding="unicode") for p in xmltv.findall("programme")}
    for cached in cached_programmes:
        if cached not in existing_programme_hashes:
            xmltv.append(ET.fromstring(cached))

    # Pretty-print the XML with blank line removal
    rough_string = ET.tostring(xmltv, encoding="unicode")
    reparsed = minidom.parseString(rough_string)
    formatted_xmltv = "\n".join([line for line in reparsed.toprettyxml(indent="  ").splitlines() if line.strip()])

    # Save updated cache
    with open(cache_file, "w", encoding="utf-8") as f:
        f.write(formatted_xmltv)
    logger.info("XMLTV cache updated.")

    # Update global cache
    global cached_xmltv, last_updated
    cached_xmltv = formatted_xmltv
    last_updated = time.time()
    logger.debug(f"Generated XMLTV: {formatted_xmltv}")
    
# Endpoint to get the XMLTV data
@app.route("/xmltv", methods=["GET"])
@authorise
def xmltv():
    global cached_xmltv, last_updated
    logger.info("Guide Requested")
    
    # Check if the cached XMLTV data is older than 15 minutes
    if cached_xmltv is None or (time.time() - last_updated) > 900:  # 900 seconds = 15 minutes
        refresh_xmltv()
    
    return Response(
        cached_xmltv,
        mimetype="text/xml",
    )


@app.route("/play/<portalId>/<channelId>", methods=["GET"])
def channel(portalId, channelId):
    def streamData():
        def occupy():
            occupied.setdefault(portalId, [])
            occupied.get(portalId, []).append(
                {
                    "mac": mac,
                    "channel id": channelId,
                    "channel name": channelName,
                    "client": ip,
                    "portal name": portalName,
                    "start time": startTime,
                }
            )
            logger.info("Occupied Portal({}):MAC({})".format(portalId, mac))

        def unoccupy():
            occupied.get(portalId, []).remove(
                {
                    "mac": mac,
                    "channel id": channelId,
                    "channel name": channelName,
                    "client": ip,
                    "portal name": portalName,
                    "start time": startTime,
                }
            )
            logger.info("Unoccupied Portal({}):MAC({})".format(portalId, mac))

        try:
            startTime = datetime.now(timezone.utc).timestamp()
            occupy()
            with subprocess.Popen(
                ffmpegcmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            ) as ffmpeg_sp:
                while True:
                    chunk = ffmpeg_sp.stdout.read(1024)
                    if len(chunk) == 0:
                        if ffmpeg_sp.poll() != 0:
                            logger.info("Ffmpeg closed with error({}). Moving MAC({}) for Portal({})".format(str(ffmpeg_sp.poll()), mac, portalName))
                            moveMac(portalId, mac)
                        break
                    yield chunk
        except:
            pass
        finally:
            unoccupy()
            ffmpeg_sp.kill()

    def testStream():
        timeout = int(getSettings()["ffmpeg timeout"]) * int(1000000)
        ffprobecmd = ["ffprobe", "-timeout", str(timeout), "-i", link]

        if proxy:
            ffprobecmd.insert(1, "-http_proxy")
            ffprobecmd.insert(2, proxy)

        with subprocess.Popen(
            ffprobecmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as ffprobe_sb:
            ffprobe_sb.communicate()
            if ffprobe_sb.returncode == 0:
                return True
            else:
                return False

    def isMacFree():
        count = 0
        for i in occupied.get(portalId, []):
            if i["mac"] == mac:
                count = count + 1
        if count < streamsPerMac:
            return True
        else:
            return False

    portal = getPortals().get(portalId)
    portalName = portal.get("name")
    url = portal.get("url")
    macs = list(portal["macs"].keys())
    streamsPerMac = int(portal.get("streams per mac"))
    proxy = portal.get("proxy")
    web = request.args.get("web")
    ip = request.remote_addr

    logger.info(
        "IP({}) requested Portal({}):Channel({})".format(ip, portalId, channelId)
    )

    freeMac = False

    for mac in macs:
        channels = None
        cmd = None
        link = None
        if streamsPerMac == 0 or isMacFree():
            logger.info(
                "Trying Portal({}):MAC({}):Channel({})".format(portalId, mac, channelId)
            )
            freeMac = True
            token = stb.getToken(url, mac, proxy)
            if token:
                stb.getProfile(url, mac, token, proxy)
                channels = stb.getAllChannels(url, mac, token, proxy)

        if channels:
            for c in channels:
                if str(c["id"]) == channelId:
                    channelName = portal.get("custom channel names", {}).get(channelId)
                    if channelName == None:
                        channelName = c["name"]
                    cmd = c["cmd"]
                    break

        if cmd:
            if "http://localhost/" in cmd:
                link = stb.getLink(url, mac, token, cmd, proxy)
            else:
                link = cmd.split(" ")[1]

        if link:
            if getSettings().get("test streams", "true") == "false" or testStream():
                if web:
                    ffmpegcmd = [
                        "ffmpeg",
                        "-loglevel",
                        "panic",
                        "-hide_banner",
                        "-i",
                        link,
                        "-vcodec",
                        "copy",
                        "-f",
                        "mp4",
                        "-movflags",
                        "frag_keyframe+empty_moov",
                        "pipe:",
                    ]
                    if proxy:
                        ffmpegcmd.insert(1, "-http_proxy")
                        ffmpegcmd.insert(2, proxy)
                    return Response(streamData(), mimetype="application/octet-stream")

                else:
                    if getSettings().get("stream method", "ffmpeg") == "ffmpeg":
                        ffmpegcmd = str(getSettings()["ffmpeg command"])
                        ffmpegcmd = ffmpegcmd.replace("<url>", link)
                        ffmpegcmd = ffmpegcmd.replace(
                            "<timeout>",
                            str(int(getSettings()["ffmpeg timeout"]) * int(1000000)),
                        )
                        if proxy:
                            ffmpegcmd = ffmpegcmd.replace("<proxy>", proxy)
                        else:
                            ffmpegcmd = ffmpegcmd.replace("-http_proxy <proxy>", "")
                        " ".join(ffmpegcmd.split())  # cleans up multiple whitespaces
                        ffmpegcmd = ffmpegcmd.split()
                        return Response(
                            streamData(), mimetype="application/octet-stream"
                        )
                    else:
                        logger.info("Redirect sent")
                        return redirect(link)

        logger.info(
            "Unable to connect to Portal({}) using MAC({})".format(portalId, mac)
        )
        logger.info("Moving MAC({}) for Portal({})".format(mac, portalName))
        moveMac(portalId, mac)

        if not getSettings().get("try all macs", "true") == "true":
            break

    if not web:
        logger.info(
            "Portal({}):Channel({}) is not working. Looking for fallbacks...".format(
                portalId, channelId
            )
        )

        portals = getPortals()
        for portal in portals:
            if portals[portal]["enabled"] == "true":
                fallbackChannels = portals[portal]["fallback channels"]
                if channelName in fallbackChannels.values():
                    url = portals[portal].get("url")
                    macs = list(portals[portal]["macs"].keys())
                    proxy = portals[portal].get("proxy")
                    for mac in macs:
                        channels = None
                        cmd = None
                        link = None
                        if streamsPerMac == 0 or isMacFree():
                            for k, v in fallbackChannels.items():
                                if v == channelName:
                                    try:
                                        token = stb.getToken(url, mac, proxy)
                                        stb.getProfile(url, mac, token, proxy)
                                        channels = stb.getAllChannels(
                                            url, mac, token, proxy
                                        )
                                    except:
                                        logger.info(
                                            "Unable to connect to fallback Portal({}) using MAC({})".format(
                                                portalId, mac
                                            )
                                        )
                                    if channels:
                                        fChannelId = k
                                        for c in channels:
                                            if str(c["id"]) == fChannelId:
                                                cmd = c["cmd"]
                                                break
                                        if cmd:
                                            if "http://localhost/" in cmd:
                                                link = stb.getLink(
                                                    url, mac, token, cmd, proxy
                                                )
                                            else:
                                                link = cmd.split(" ")[1]
                                            if link:
                                                if testStream():
                                                    logger.info(
                                                        "Fallback found for Portal({}):Channel({})".format(
                                                            portalId, channelId
                                                        )
                                                    )
                                                    if (
                                                        getSettings().get(
                                                            "stream method", "ffmpeg"
                                                        )
                                                        == "ffmpeg"
                                                    ):
                                                        ffmpegcmd = str(
                                                            getSettings()[
                                                                "ffmpeg command"
                                                            ]
                                                        )
                                                        ffmpegcmd = ffmpegcmd.replace(
                                                            "<url>", link
                                                        )
                                                        ffmpegcmd = ffmpegcmd.replace(
                                                            "<timeout>",
                                                            str(
                                                                int(
                                                                    getSettings()[
                                                                        "ffmpeg timeout"
                                                                    ]
                                                                )
                                                                * int(1000000)
                                                            ),
                                                        )
                                                        if proxy:
                                                            ffmpegcmd = (
                                                                ffmpegcmd.replace(
                                                                    "<proxy>", proxy
                                                                )
                                                            )
                                                        else:
                                                            ffmpegcmd = ffmpegcmd.replace(
                                                                "-http_proxy <proxy>",
                                                                "",
                                                            )
                                                        " ".join(
                                                            ffmpegcmd.split()
                                                        )  # cleans up multiple whitespaces
                                                        ffmpegcmd = ffmpegcmd.split()
                                                        return Response(
                                                            streamData(),
                                                            mimetype="application/octet-stream",
                                                        )
                                                    else:
                                                        logger.info("Redirect sent")
                                                        return redirect(link)

    if freeMac:
        logger.info(
            "No working streams found for Portal({}):Channel({})".format(
                portalId, channelId
            )
        )
    else:
        logger.info(
            "No free MAC for Portal({}):Channel({})".format(portalId, channelId)
        )

    return make_response("No streams available", 503)


@app.route("/dashboard")
@authorise
def dashboard():
    return render_template("dashboard.html")


@app.route("/streaming")
@authorise
def streaming():
    return flask.jsonify(occupied)


@app.route("/log")
@authorise
def log():
    # Get the base path for the user directory
    basePath = os.path.expanduser("~")

    # Define the path for the log file in the 'evilvir.us' subdirectory
    logFilePath = os.path.join(basePath, "evilvir.us", "MacReplay.log")

    # Ensure the subdirectory exists
    os.makedirs(os.path.dirname(logFilePath), exist_ok=True)

    # Open and read the log file
    with open(logFilePath) as f:
        log_content = f.read()
    
    return log_content


# HD Homerun #


def hdhr(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        settings = getSettings()
        security = settings["enable security"]
        username = settings["username"]
        password = settings["password"]
        hdhrenabled = settings["enable hdhr"]
        if (
            security == "false"
            or auth
            and auth.username == username
            and auth.password == password
        ):
            if hdhrenabled:
                return f(*args, **kwargs)
        return make_response("Error", 404)

    return decorated


@app.route("/discover.json", methods=["GET"])
@hdhr
def discover():
    logger.info("HDHR Status Requested.")
    settings = getSettings()
    name = settings["hdhr name"]
    id = settings["hdhr id"]
    tuners = settings["hdhr tuners"]
    data = {
        "BaseURL": host,
        "DeviceAuth": name,
        "DeviceID": id,
        "FirmwareName": "MacReplay",
        "FirmwareVersion": "666",
        "FriendlyName": name,
        "LineupURL": host + "/lineup.json",
        "Manufacturer": "Evilvirus",
        "ModelNumber": "666",
        "TunerCount": int(tuners),
    }
    return flask.jsonify(data)


@app.route("/lineup_status.json", methods=["GET"])
@hdhr
def status():
    data = {
        "ScanInProgress": 0,
        "ScanPossible": 0,
        "Source": "Cable",
        "SourceList": ["Cable"],
    }
    return flask.jsonify(data)


# Function to refresh the lineup
def refresh_lineup():
    global cached_lineup
    logger.info("Refreshing Lineup...")
    lineup = []
    portals = getPortals()
    for portal in portals:
        if portals[portal]["enabled"] == "true":
            enabledChannels = portals[portal].get("enabled channels", [])
            if len(enabledChannels) != 0:
                name = portals[portal]["name"]
                url = portals[portal]["url"]
                macs = list(portals[portal]["macs"].keys())
                proxy = portals[portal]["proxy"]
                customChannelNames = portals[portal].get("custom channel names", {})
                customChannelNumbers = portals[portal].get("custom channel numbers", {})

                for mac in macs:
                    try:
                        token = stb.getToken(url, mac, proxy)
                        stb.getProfile(url, mac, token, proxy)
                        allChannels = stb.getAllChannels(url, mac, token, proxy)
                        break
                    except:
                        allChannels = None

                if allChannels:
                    for channel in allChannels:
                        channelId = str(channel.get("id"))
                        if channelId in enabledChannels:
                            channelName = customChannelNames.get(channelId)
                            if channelName is None:
                                channelName = str(channel.get("name"))
                            channelNumber = customChannelNumbers.get(channelId)
                            if channelNumber is None:
                                channelNumber = str(channel.get("number"))

                            lineup.append(
                                {
                                    "GuideNumber": channelNumber,
                                    "GuideName": channelName,
                                    "URL": "http://"
                                    + host
                                    + "/play/"
                                    + portal
                                    + "/"
                                    + channelId,
                                }
                            )
                else:
                    logger.error("Error making lineup for {}, skipping".format(name))
    
    # Sort lineup by GuideNumber
    lineup.sort(key=lambda x: int(x["GuideNumber"]))

    cached_lineup = lineup
    logger.info("Lineup Refreshed.")
    
    
# Endpoint to get the current lineup
@app.route("/lineup.json", methods=["GET"])
@app.route("/lineup.post", methods=["POST"])
@hdhr
def lineup():
    logger.info("Lineup Requested")
    if not cached_lineup:  # Refresh lineup if cache is empty
        refresh_lineup()
    logger.info("Lineup Delivered")
    return jsonify(cached_lineup)

# Endpoint to manually refresh the lineup
@app.route("/refresh_lineup", methods=["POST"])
def refresh_lineup_endpoint():
    refresh_lineup()
    return jsonify({"status": "Lineup refreshed successfully"})

def start_refresh():
    # Run refresh_lineup in a separate thread
    threading.Thread(target=refresh_lineup, daemon=True).start()
    threading.Thread(target=refresh_xmltv, daemon=True).start()
    
    
if __name__ == "__main__":
    config = loadConfig()

    # Start the refresh thread before the server
    start_refresh()

    # Start the server
    if "TERM_PROGRAM" in os.environ.keys() and os.environ["TERM_PROGRAM"] == "vscode":
        app.run(host="0.0.0.0", port=13681, debug=True)
    else:
        waitress.serve(app, port=13681, _quiet=True, threads=24)