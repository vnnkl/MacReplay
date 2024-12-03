# **MacReplay**

MacReplay is an modified/improved version of [STB-Proxy](https://github.com/Chris230291/STB-Proxy), designed for seamless connectivity between MAC address portals and media platforms like Plex or M3U-based software.  

This lightweight solution eliminates the need for Docker by compiling everything into a single executable file, making it easy to use and deploy on Windows systems.

---

## **Features**
- 🛠️ **Single Executable**: No need for Docker; everything is packed into one `.exe` file.  
- 🔗 **MAC Portal Integration**: Connect MAC address portals directly with Plex or M3U software.  
- 🐦‍🔥 **Multiple MACs**: Rotate between MAC addresses across a single portal, allowing for multiple connections simultaneously.  
- 🦕 **Multiple Portals**: Add multiple portal URLs to get channels from different providers in the same playlist.

---

## **Requirements**
To use MacReplay, ensure you have the following:
- **Windows**: Version 8 or higher.  
- **Plex Pass**: If you're connecting to Plex.  *this may no longer be a requirement. with recent plex updates*

---

## **Getting Started**
1. **Download** the latest release from the [Releases page](https://github.com/Evilvir-us/MacReplay/releases).  
2. **Run** the executable on your Windows system.  
3. **Open** the server URL in your web browser.  
4. **Add** your Portal address and MAC addresses on the Portals page.  
5. **Enable** the channels you want to use in the Playlist Editor and save them. *(Note: Plex has a limit of 480 channels.)*  
6. **Connect** in plex settings. Under plex settings, select *Live TV and DVR* and click the button *Set Up Plex Tuner*
7. **Click** *Have an XMLTV guide* link and enter http://127.0.0.1:8001/xmltv.
8. **Click** *Continue*
9. **???**
10. **Profit!!!**

---

## Troubleshooting

If the TV guide is not being populated:
Check the [XMLTV guide](http://192.168.1.88:8001/xmltv).
If it is just the list of channels with nothing below them, the provider likely does not supply a guide.
Try switching to a different provider.

---

## **Known Issues**

Channel logos may not display when viewed in a browser. This is likely due to your browsers security, related to HTTP files being served on an HTTPS domain.\
![Chrome](https://evilvir.us/application/files/2917/3318/2580/chrome_https_issue.png)
![Frefox](https://evilvir.us/application/files/9217/3318/2583/firefox_https_issue.png)

This issue does not occur with [PLEX HTPC](https://apps.microsoft.com/store/detail/XPFFFF6NN1LZDQ?ocid=pdpshare), the mobile apps, or the TV app. To watch from a PC, use [PLEX HTPC](https://apps.microsoft.com/store/detail/XPFFFF6NN1LZDQ?ocid=pdpshare). If any logos are still missing, it means the provider isn't supplying them.

---

## **Credits**
MacReplay is based on the incredible work done by [Chris230291](https://github.com/Chris230291) with the original [STB-Proxy](https://github.com/Chris230291/STB-Proxy).  

---

## **Disclaimer**
This tool is provided as-is and is intended for educational purposes only. Use responsibly and in compliance with applicable laws and terms of service.
