#!/usr/bin/env python3
import os
import time
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup
import deepl
import re


# --- Config (from environment variables) ---
WATCH_DIRS = os.getenv("WATCH_DIRS", "/path/to/directory/to/watch")
WATCH_DIRS = [d.strip() for d in WATCH_DIRS.split(",") if d.strip()]
TARGET_LANG = os.getenv("TARGET_LANG", "TH") # for Thai language (see DeepL docs)
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "your_default_key") # (see DeepL docs)
SLEEP_INTERVAL = int(os.getenv("SLEEP_INTERVAL", "10")) # the higher the less responsive. the lower the higher "load" on the system.

# Optional regex to filter files by filename
WATCH_REGEX = os.getenv("WATCH_REGEX", None)
if WATCH_REGEX:
    WATCH_REGEX_COMPILED = re.compile(WATCH_REGEX)
else:
    WATCH_REGEX_COMPILED = None

# --- Config (hardcoded variables) ---
FILE_EXTENSIONS = [".srt", ".ass"]
TRANSLATED_SUFFIX = ".GENERATED.th" # this should be a unique identifier (because it will tell the watchdog to not translate this kind of file) ... put .th additionally in order to help emby/plex/... to detect the langauge
DB_FILE = "translated_files.json" # in this file it is tracked which files were already translated


# --- DeepL client setup ---
deepl_client = deepl.DeepLClient(DEEPL_API_KEY)


# --- Tracking ---
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        processed_files = json.load(f)
else:
    processed_files = {}  # {filepath: "success" / "error"}


def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(processed_files, f, indent=2)


# --- File discovery ---
def find_subtitle_files(base_dir: str):
    for root, _, files in os.walk(base_dir):
        for f in files:
            if any(f.lower().endswith(ext) for ext in FILE_EXTENSIONS) and TRANSLATED_SUFFIX not in f:
                if WATCH_REGEX_COMPILED and not WATCH_REGEX_COMPILED.search(f):
                    continue
                yield Path(root) / f


# --- Translation ---

# see also https://developers.deepl.com/api-reference/translate#request-body-descriptions
# see also https://github.com/deeplcom/deepl-python


def translate_texts(texts: list[str], target_lang: str) -> list[str]:
    """Send a batch of texts to DeepL, returns translations in the same order"""
    cleaned = [BeautifulSoup(t, "html.parser").get_text() for t in texts]

    responses = deepl_client.translate_text(
        cleaned,
        target_lang=target_lang,
        context="These are subtitles from a video file."
    )

    return [r.text for r in responses]



# --- Subtitle parsing for SRT file ---
def translate_srt(file_path: Path, target_lang: str):
    translated_lines = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    buffer = []
    text_blocks = []
    block_positions = []

    for line in lines:
        if line.strip() == "" or line.strip().isdigit() or "-->" in line:
            if buffer:
                joined_text = " ".join(buffer)
                text_blocks.append(joined_text)
                block_positions.append(len(translated_lines))
                translated_lines.append(None)
                buffer = []
            translated_lines.append(line)
        else:
            buffer.append(line.strip())

    if buffer:
        joined_text = " ".join(buffer)
        text_blocks.append(joined_text)
        block_positions.append(len(translated_lines))
        translated_lines.append(None)

    if text_blocks:
        translations = translate_texts(text_blocks, target_lang)
        for pos, t in zip(block_positions, translations):
            translated_lines[pos] = t + "\n"

    out_file = file_path.with_name(file_path.stem + TRANSLATED_SUFFIX + file_path.suffix)
    with open(out_file, "w", encoding="utf-8") as f:
        f.writelines(translated_lines)

    return out_file


# --- Subtitle parsing for ASS file ---
def translate_ass(file_path: Path, target_lang: str):
    lines = []
    text_blocks = []
    block_positions = []

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for idx, line in enumerate(f):
            if line.startswith("Dialogue:"):
                parts = line.strip().split(",", 9)
                if len(parts) == 10:
                    text_blocks.append(parts[9])
                    block_positions.append(idx)
            lines.append(line)

    if text_blocks:
        translations = translate_texts(text_blocks, target_lang)
        for pos, t in zip(block_positions, translations):
            parts = lines[pos].strip().split(",", 9)
            parts[9] = t
            lines[pos] = ",".join(parts) + "\n"

    out_file = file_path.with_name(file_path.stem + TRANSLATED_SUFFIX + file_path.suffix)
    with open(out_file, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return out_file



def translate_subtitle(file_path: Path, target_lang: str):
    ext = file_path.suffix.lower()
    if ext == ".srt":
        return translate_srt(file_path, target_lang)
    elif ext == ".ass":
        return translate_ass(file_path, target_lang)
    else:
        raise ValueError(f"Unsupported subtitle format: {ext}")


def is_translated(file_path: Path) -> bool:
    return str(file_path) in processed_files


def process_file(file_path: Path):
    try:
        out_file = translate_subtitle(file_path, TARGET_LANG)
        processed_files[str(file_path)] = "success"
        print(f"Translated: {file_path} -> {out_file}")
    except Exception as e:
        processed_files[str(file_path)] = "error"
        print(f"Error translating {file_path}: {e}")
    finally:
        save_db()


# --- Watchdog ---
def watch_folders():
    while True:
        for watch_dir in WATCH_DIRS:
            for file in find_subtitle_files(watch_dir):
                if not is_translated(file):
                    process_file(file)
        time.sleep(SLEEP_INTERVAL)


# --- Test ---
def test_single_file(file_path: str):
    process_file(Path(file_path))


if __name__ == "__main__":
    watch_folders()
    #test_single_file("FullFile_Test.srt")


