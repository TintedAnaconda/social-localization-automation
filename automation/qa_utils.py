from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

import re
import unicodedata

def normalize_autofill_value(value) -> str:
    """
    Normalize Autofill values for reliable matching across Excel sources.
    """
    text = normalize_text(value)

    if not text:
        return ""

    # Normalize unicode forms
    text = unicodedata.normalize("NFKC", text)

    # Replace invisible / special spacing characters
    text = text.replace("\u00A0", " ")   # non-breaking space
    text = text.replace("\u2007", " ")   # figure space
    text = text.replace("\u202F", " ")   # narrow no-break space

    # Normalize curly punctuation to plain equivalents
    text = text.replace("’", "'")
    text = text.replace("‘", "'")
    text = text.replace("“", '"')
    text = text.replace("”", '"')
    text = text.replace("–", "-")
    text = text.replace("—", "-")

    # Collapse repeated whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Case-insensitive comparison
    return text.lower()

def normalize_text(value) -> str:
    """
    Convert a cell value to a clean string.
    NaN/None become empty string.
    """
    if pd.isna(value):
        return ""
    return str(value).strip()


def safe_lower(value) -> str:
    """
    Lowercase helper that safely handles NaN/None.
    """
    return normalize_text(value).lower()


def is_blank(value) -> bool:
    """
    True if the value is empty after normalization.
    """
    return normalize_text(value) == ""


def clean_object_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Trim whitespace on object columns only.
    Does NOT change header names.
    """
    df = df.copy()

    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].map(lambda x: normalize_text(x) if not pd.isna(x) else "")

    return df


def filter_rows_with_message_name(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only rows where Message Name is populated.
    This defines the QA scope.
    """
    if "Message Name" not in df.columns:
        return df.copy()

    filtered_df = df[df["Message Name"].astype(str).str.strip() != ""].copy()
    return filtered_df


def contains_url(text: str) -> bool:
    """
    Detect whether a text string contains a URL.
    """
    text = normalize_text(text)
    if not text:
        return False

    pattern = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
    return bool(pattern.search(text))


def extract_hashtags(text: str) -> list[str]:
    """
    Extract hashtags from a text string.
    Example: 'Hello #AI #Cloud' -> ['#AI', '#Cloud']
    """
    text = normalize_text(text)
    if not text:
        return []

    return re.findall(r"#\w+", text)


def parse_hashtags_cell(value: str) -> list[str]:
    """
    Parse the HASHTAGS column into a list of hashtag-like values.
    Supports hashtags entered with # or plain text separated by commas,
    semicolons, pipes, or line breaks.
    """
    text = normalize_text(value)
    if not text:
        return []

    hashtag_matches = re.findall(r"#\w+", text)
    if hashtag_matches:
        return hashtag_matches

    parts = re.split(r"[,\n\r;|]+", text)
    return [part.strip() for part in parts if part.strip()]


def normalize_hashtag(tag: str) -> str:
    """
    Normalize hashtag for uniqueness comparison.
    '#AI' and 'AI' both become 'ai'
    """
    return normalize_text(tag).lstrip("#").lower()


def clean_multiline_filenames(value: str) -> list[str]:
    """
    Split IMAGE-NAME values into individual filenames.
    Supports multiple filenames separated by line breaks.
    """
    text = normalize_text(value)
    if not text:
        return []

    parts = re.split(r"[\r\n]+", text)
    return [part.strip() for part in parts if part.strip()]


def get_extension(filename: str) -> str:
    """
    Return lowercase file extension including the dot.
    Example: 'image.PNG' -> '.png'
    """
    return Path(filename).suffix.lower()


def is_valid_https_url(url: str) -> bool:
    """
    Validate that the cell contains one valid https:// URL.
    """
    text = normalize_text(url)
    if not text:
        return False

    if "\n" in text or "\r" in text:
        return False

    parsed = urlparse(text)
    return parsed.scheme == "https" and bool(parsed.netloc)


def clean_filename_for_language_check(text: str) -> str:
    """
    Convert IMAGE-NAME values into cleaner human-readable text for optional
    spell-checking.

    Example:
    'LinkedIn_AI_Campaign_EN-US_v2.png'
    -> 'LinkedIn AI Campaign EN US v'
    """
    text = normalize_text(text)
    if not text:
        return ""

    filenames = clean_multiline_filenames(text)
    cleaned_parts: list[str] = []

    for name in filenames:
        stem = Path(name).stem
        stem = re.sub(r"[_\-]+", " ", stem)
        stem = re.sub(r"\d+", " ", stem)
        stem = re.sub(r"\s+", " ", stem).strip()

        if stem:
            cleaned_parts.append(stem)

    return ". ".join(cleaned_parts)


def add_source_row_number(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add Excel-style source row numbers for reporting.
    Assumes row 1 is the header row, so first data row is 2.
    """
    df = df.copy()

    if "Source Row Number" not in df.columns:
        df.insert(0, "Source Row Number", range(2, len(df) + 2))

    return df


def dedupe_preserve_order(values: list[str]) -> list[str]:
    """
    Deduplicate strings while preserving order.
    """
    seen = set()
    deduped: list[str] = []

    for value in values:
        if value not in seen:
            seen.add(value)
            deduped.append(value)

    return deduped


def split_single_value_field(value: str) -> list[str]:
    """
    Split a field that is expected to contain only one value.
    Useful for detecting whether a user entered multiple values separated by
    commas, semicolons, pipes, or line breaks.
    """
    text = normalize_text(value)
    if not text:
        return []

    return [part.strip() for part in re.split(r"[,\n\r;|]+", text) if part.strip()]