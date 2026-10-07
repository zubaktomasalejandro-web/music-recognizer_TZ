# Music Recognizer

A free Windows tool that scans long DJ sets from YouTube or SoundCloud, identifies tracks with Shazam, and generates a timestamped tracklist.

## Features

- Automatic track recognition for long DJ sets
- YouTube and SoundCloud support
- Timestamped tracklists
- Low-confidence detections separated automatically
- Portable Windows version
- No installation required for the packaged release
- Optional temporary YouTube login for restricted videos
- Temporary Firefox login data is deleted after the authenticated download attempt

## How it works

Music Recognizer analyzes a 12-second audio sample every 30 seconds.

Tracks identified more than once are added to the main tracklist.

Tracks identified only once are listed under:

`LOW RELIABILITY`

These detections may still be correct, but may also correspond to samples, short overlaps, or false positives.

## Windows version

Download the latest Windows ZIP from the Releases section.

Extract the ZIP and run:

`music-recognizer_TZ.exe`

Do not move or delete the `program files` folder.

## Restricted YouTube videos

Most videos work without authentication.

If YouTube requires you to sign in, Music Recognizer first lets the normal download process fail completely and then checks whether the error is actually authentication-related.

Only in that case will it offer to open the included Firefox Portable instance.

1. Log in to YouTube in Firefox Portable.
2. Confirm that you can open the restricted video.
3. Close Firefox Portable completely.
4. Return to Music Recognizer and press ENTER.

The program then temporarily uses that Firefox session for the download.

After the authenticated download attempt, the temporary Firefox profile is deleted automatically.

## Output

Tracklists are saved automatically inside:

`tracklists/`

Example:

```text
TRACKLIST
==================================================

00:30 — Artist - Track
04:00 — Artist - Track
08:30 — Artist - Track


LOW RELIABILITY
==================================================

12:00 — Artist - Track
```

## Running from source

Requirements:

- Python 3.12
- FFmpeg
- FFprobe
- Deno

Install the Python dependencies with:

```bash
pip install -r requirements.txt
```

The current Windows-oriented source expects the bundled executables in:

```text
program files/
├── ffmpeg.exe
├── ffprobe.exe
├── deno.exe
└── FirefoxPortable/
```

## Building the Windows executable

```bash
pyinstaller --onefile --name MusicRecognizer music-recognizer_TZ.py
```

The executable will be created inside:

`dist/`

## Notes

Track timestamps are approximate and correspond to the first moment at which the track was detected.

Music recognition depends on Shazam and may not identify unreleased, heavily edited, obscure, or highly overlapped tracks.

Use Music Recognizer only with content you are permitted to access and download. Users are responsible for complying with applicable copyright law and the terms of the source platform.

## License

MIT

---

*hope your set is fire.*  
**tomás zubak**
