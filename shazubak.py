import os
import re
import json
import glob
import asyncio
import subprocess
import sys
import shutil

from pathlib import Path
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from shazamio import Shazam


def get_app_directory():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


APP_DIR = get_app_directory()

PROGRAM_FILES_DIR = APP_DIR / "program files"
TRACKLISTS_DIR = APP_DIR / "tracklists"
TEMP_DIR = APP_DIR / "temp"

PROGRAM_FILES_DIR.mkdir(exist_ok=True)
TRACKLISTS_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

FFMPEG = str(PROGRAM_FILES_DIR / "ffmpeg.exe")
FFPROBE = str(PROGRAM_FILES_DIR / "ffprobe.exe")
DENO = str(PROGRAM_FILES_DIR / "deno.exe")

FIREFOX_PORTABLE_DIR = PROGRAM_FILES_DIR / "FirefoxPortable"
FIREFOX_PORTABLE = str(FIREFOX_PORTABLE_DIR / "FirefoxPortable.exe")
FIREFOX_PROFILE = FIREFOX_PORTABLE_DIR / "Data" / "profile"

TEMP_SAMPLE = str(TEMP_DIR / "_shazam_sample.wav")
DOWNLOAD_BASENAME = str(TEMP_DIR / "input_audio")


# ============================================================
# CONFIGURATION
# ============================================================

# How often the set is analyzed
INTERVAL = 30

# Duration of the fragment sent to Shazam
SAMPLE_DURATION = 12

# If the same track reappears within this time window,
# it is considered part of the same group
MAX_TRACK_GAP = 120


# ============================================================
# UTILITIES
# ============================================================

def sanitize_filename(name):
    """
    Removes characters that Windows does not allow
    in file names.
    """

    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name)
    name = name.strip().rstrip(".")

    if not name:
        return "unknown"

    return name[:150]


def format_time(seconds):
    seconds = max(0, int(seconds))

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours:02}:{minutes:02}:{secs:02}"

    return f"{minutes:02}:{secs:02}"


def track_key(artist, title):
    return (
        artist.strip().lower(),
        title.strip().lower()
    )


# ============================================================
# YOUTUBE AUTHENTICATION HELPERS
# ============================================================

def is_youtube_url(url):
    url = url.lower()

    return (
        "youtube.com" in url
        or "youtu.be" in url
    )


def requires_youtube_auth(error):
    message = str(error).lower()

    auth_indicators = [
        "sign in",
        "login required",
        "login to confirm",
        "confirm your age",
        "age-restricted",
        "age restricted",
        "members-only",
        "members only",
        "private video",
        "this video is private",
        "authentication required",
        "cookies",
        "not a bot",
    ]

    return any(
        indicator in message
        for indicator in auth_indicators
    )


def open_firefox_for_login(url):

    if not os.path.exists(FIREFOX_PORTABLE):

        print()
        print(
            "ERROR: Could not find Firefox Portable."
        )

        print(
            "Expected path:"
        )

        print(
            f"  {FIREFOX_PORTABLE}"
        )

        return False

    print()
    print("=" * 70)
    print("YOUTUBE AUTHENTICATION")
    print("=" * 70)

    print()

    print(
        "Firefox Portable will now open."
    )

    print()

    print(
        "1. Log in to YouTube."
    )

    print(
        "2. Make sure you can open the video in Firefox."
    )

    print(
        "3. CLOSE Firefox Portable completely."
    )

    print(
        "4. Return to this window."
    )

    print()

    try:

        subprocess.Popen([
            FIREFOX_PORTABLE,
            url
        ])

    except Exception as e:

        print(
            "Could not open Firefox Portable:"
        )

        print(e)

        return False

    input(
        "Once Firefox is completely closed, "
        "press ENTER to continue..."
    )

    return True


def delete_firefox_credentials():

    print()

    print(
        "Removing temporary login data..."
    )

    try:

        if FIREFOX_PROFILE.exists():

            shutil.rmtree(
                FIREFOX_PROFILE
            )

        FIREFOX_PROFILE.mkdir(
            parents=True,
            exist_ok=True
        )

        print(
            "Login data removed."
        )

    except Exception as e:

        print()

        print(
            "WARNING: Could not completely remove "
            "Firefox Portable login data."
        )

        print(
            "Make sure Firefox is closed."
        )

        print(
            f"Details: {e}"
        )


# ============================================================
# DOWNLOAD
# ============================================================

def download_audio(url):

    options = {
        "format": "bestaudio/best",
        "outtmpl": f"{DOWNLOAD_BASENAME}.%(ext)s",
        "noplaylist": True,
        "quiet": False,

        "js_runtimes": {
            "deno": {
                "path": DENO
            }
        },

        "remote_components": {
            "ejs:github"
        },
    }

    print()
    print(
        "Downloading audio..."
    )
    print("-" * 70)

    # --------------------------------------------------------
    # FIRST ATTEMPT: NORMAL DOWNLOAD
    # --------------------------------------------------------

    try:

        with YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

            downloaded_file = (
                ydl.prepare_filename(
                    info
                )
            )

            video_title = info.get(
                "title",
                "unknown"
            )

        return (
            downloaded_file,
            video_title
        )

    except DownloadError as e:

        # If this is not YouTube, there is no reason
        # to try YouTube authentication.
        if not is_youtube_url(url):
            raise

        # Firefox Portable is only offered if the error
        # actually appears to be authentication-related.
        if not requires_youtube_auth(e):
            raise

        print()

        print(
            "The normal download failed because this video "
            "appears to require YouTube authentication."
        )

        answer = input(
            "Would you like to sign in using "
            "Firefox Portable? [Y/n]: "
        ).strip().lower()

        if answer not in (
            "",
            "y",
            "yes"
        ):

            raise

    # --------------------------------------------------------
    # SECOND ATTEMPT: FIREFOX PORTABLE LOGIN
    # --------------------------------------------------------

    if not open_firefox_for_login(url):

        raise RuntimeError(
            "Could not start Firefox Portable."
        )

    authenticated_options = dict(
        options
    )

    authenticated_options[
        "cookiesfrombrowser"
    ] = (
        "firefox",
        str(FIREFOX_PROFILE),
        None,
        None
    )

    try:

        print()

        print(
            "Reading the temporary Firefox session..."
        )

        print()

        with YoutubeDL(
            authenticated_options
        ) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

            downloaded_file = (
                ydl.prepare_filename(
                    info
                )
            )

            video_title = info.get(
                "title",
                "unknown"
            )

        print()

        print(
            "Authenticated download completed."
        )

        return (
            downloaded_file,
            video_title
        )

    finally:

        delete_firefox_credentials()


def find_downloaded_audio():

    files = glob.glob(
        str(
            TEMP_DIR /
            "input_audio.*"
        )
    )

    valid_files = [
        f for f in files
        if not f.endswith(".part")
        and not f.endswith(".ytdl")
    ]

    if not valid_files:
        return None

    return valid_files[0]


# ============================================================
# FFMPEG
# ============================================================

def get_duration(filename):

    command = [
        FFPROBE,
        "-v", "quiet",
        "-show_entries",
        "format=duration",
        "-of", "json",
        filename
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True
    )

    data = json.loads(
        result.stdout
    )

    return float(
        data["format"]["duration"]
    )


def extract_sample(
    filename,
    start_time
):

    command = [
        FFMPEG,
        "-y",
        "-loglevel", "quiet",
        "-ss", str(start_time),
        "-i", filename,
        "-t", str(
            SAMPLE_DURATION
        ),
        "-vn",
        "-ac", "1",
        "-ar", "44100",
        TEMP_SAMPLE
    ]

    subprocess.run(
        command,
        check=True
    )


# ============================================================
# SHAZAM
# ============================================================

async def recognize_sample(
    shazam,
    audio_file,
    start_time
):

    try:

        extract_sample(
            audio_file,
            start_time
        )

        result = await (
            shazam.recognize(
                TEMP_SAMPLE
            )
        )

        track = result.get(
            "track"
        )

        if not track:
            return None

        return {

            "artist":
                track.get(
                    "subtitle",
                    "Unknown artist"
                ),

            "title":
                track.get(
                    "title",
                    "Unknown title"
                )
        }

    except Exception:

        return None


# ============================================================
# ANALYSIS
# ============================================================

async def analyze_audio(
    audio_file
):

    duration = get_duration(
        audio_file
    )

    print()
    print("=" * 70)
    print("ANALYSIS")
    print("=" * 70)

    print(
        f"File: {audio_file}"
    )

    print(
        f"Duration: {format_time(duration)}"
    )

    print()

    shazam = Shazam()

    detections = []

    current_time = 0

    while (
        current_time
        < duration
    ):

        timestamp = format_time(
            current_time
        )

        result = (
            await recognize_sample(
                shazam,
                audio_file,
                current_time
            )
        )

        if result:

            artist = (
                result["artist"]
            )

            title = (
                result["title"]
            )

            print(
                f"{timestamp}  →  "
                f"{artist} - {title}"
            )

            detections.append({

                "time":
                    current_time,

                "artist":
                    artist,

                "title":
                    title
            })

        else:

            print(
                f"{timestamp}  →  "
                "Not identified"
            )

            detections.append({

                "time":
                    current_time,

                "artist":
                    None,

                "title":
                    None
            })

        current_time += INTERVAL

    if os.path.exists(
        TEMP_SAMPLE
    ):

        os.remove(
            TEMP_SAMPLE
        )

    return detections


# ============================================================
# DETECTION GROUPING
# ============================================================

def summarize_detections(
    detections
):

    groups = []

    for detection in detections:

        if (
            detection["artist"]
            is None
        ):

            continue

        key = track_key(
            detection["artist"],
            detection["title"]
        )

        matching_group = None

        # Check whether the same track appeared recently.
        #
        # This allows cases such as:
        #
        # 32:00 Track A
        # 32:30 Track B
        # 33:00 Track C
        # 33:30 Track A
        #
        # Track A is still grouped together.

        for group in reversed(
            groups
        ):

            if (
                group["key"]
                != key
            ):

                continue

            gap = (
                detection["time"]
                -
                group["times"][-1]
            )

            if (
                gap
                <= MAX_TRACK_GAP
            ):

                matching_group = (
                    group
                )

            break

        if matching_group:

            matching_group[
                "times"
            ].append(
                detection["time"]
            )

        else:

            groups.append({

                "key":
                    key,

                "artist":
                    detection["artist"],

                "title":
                    detection["title"],

                "times": [
                    detection["time"]
                ]
            })

    groups.sort(
        key=lambda group:
            group["times"][0]
    )

    return groups


# ============================================================
# SAVE TRACKLIST
# ============================================================

def save_tracklist_txt(
    groups,
    filename
):

    reliable = [

        group
        for group in groups

        if len(
            group["times"]
        ) >= 2
    ]

    low_reliability = [

        group
        for group in groups

        if len(
            group["times"]
        ) == 1
    ]

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "TRACKLIST\n"
        )

        f.write(
            "=" * 50
        )

        f.write(
            "\n\n"
        )

        if reliable:

            for group in reliable:

                timestamp = (
                    format_time(
                        group[
                            "times"
                        ][0]
                    )
                )

                f.write(
                    f"{timestamp} — "
                    f"{group['artist']} - "
                    f"{group['title']}\n"
                )

        else:

            f.write(
                "No tracks with multiple "
                "detections were found.\n"
            )

        if low_reliability:

            f.write(
                "\n\n"
            )

            f.write(
                "LOW RELIABILITY\n"
            )

            f.write(
                "=" * 50
            )

            f.write(
                "\n\n"
            )

            for group in (
                low_reliability
            ):

                timestamp = (
                    format_time(
                        group[
                            "times"
                        ][0]
                    )
                )

                f.write(
                    f"{timestamp} — "
                    f"{group['artist']} - "
                    f"{group['title']}\n"
                )


# ============================================================
# DISPLAY RESULTS
# ============================================================

def print_tracklist(
    groups
):

    reliable = [

        group
        for group in groups

        if len(
            group["times"]
        ) >= 2
    ]

    low_reliability = [

        group
        for group in groups

        if len(
            group["times"]
        ) == 1
    ]

    print()
    print("=" * 70)
    print("TRACKLIST")
    print("=" * 70)

    if reliable:

        for group in reliable:

            timestamp = (
                format_time(
                    group["times"][0]
                )
            )

            print(
                f"{timestamp}  —  "
                f"{group['artist']} - "
                f"{group['title']} "
                f"({len(group['times'])} "
                "detections)"
            )

    else:

        print(
            "No tracks with multiple "
            "detections were found."
        )

    if low_reliability:

        print()
        print("-" * 70)
        print("LOW RELIABILITY")
        print("-" * 70)

        for group in (
            low_reliability
        ):

            timestamp = (
                format_time(
                    group["times"][0]
                )
            )

            print(
                f"{timestamp}  —  "
                f"{group['artist']} - "
                f"{group['title']} "
                "(1 detection)"
            )


# ============================================================
# CLEANUP
# ============================================================

def delete_downloaded_audio(
    audio_file
):

    try:

        if os.path.exists(
            audio_file
        ):

            os.remove(
                audio_file
            )

            print()

            print(
                "Temporary audio deleted: "
                f"{audio_file}"
            )

    except Exception as e:

        print()

        print(
            "Could not delete the "
            f"temporary audio: {e}"
        )


# ============================================================
# MAIN
# ============================================================

async def main():

    print()
    print("=" * 70)
    print("SHAZUBAK")
    print("=" * 70)

    print(
        "hope your set is fire. "
        "tomás zubak"
    )

    print()

    url = input(
        "Paste a link:\n> "
    ).strip()

    if not url:

        print(
            "No link was entered."
        )

        return

    try:

        (
            downloaded_file,
            video_title
        ) = download_audio(
            url
        )

    except Exception as e:

        print()

        print(
            "ERROR during download:"
        )

        print(e)

        return

    if not os.path.exists(
        downloaded_file
    ):

        downloaded_file = (
            find_downloaded_audio()
        )

    if downloaded_file is None:

        print(
            "Could not find the "
            "downloaded file."
        )

        return

    clean_title = (
        sanitize_filename(
            video_title
        )
    )

    txt_filename = (
        TRACKLISTS_DIR
        /
        f"tracklist_{clean_title}.txt"
    )

    print()

    print(
        f"Title: {video_title}"
    )

    detections = (
        await analyze_audio(
            downloaded_file
        )
    )

    groups = (
        summarize_detections(
            detections
        )
    )

    print_tracklist(
        groups
    )

    save_tracklist_txt(
        groups,
        txt_filename
    )

    print()

    print(
        "Tracklist saved to:"
    )

    print(
        f"  {txt_filename}"
    )

    delete_downloaded_audio(
        downloaded_file
    )

    print()

    print(
        "Process finished."
    )


asyncio.run(main())