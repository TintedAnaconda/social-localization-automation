from __future__ import annotations

import pandas as pd

from qa_config import (
    ALLOWED_CHANNELS,
    FIXED_VALUE_RULES,
    IMAGE_TYPES_FOR_ALT_TEXT,
    INVALID_CHANNEL_WARNING_MAP,
    MEDIA_EXTENSION_RULES,
    SEVERITY_BLOCKER,
    SEVERITY_WARNING,
    TEXT_ONLY_VALUE,
)
from qa_models import Issue
from qa_utils import (
    clean_multiline_filenames,
    contains_url,
    extract_hashtags,
    get_extension,
    is_blank,
    is_valid_https_url,
    normalize_autofill_value,
    normalize_hashtag,
    normalize_text,
    parse_hashtags_cell,
)


def validate_fixed_values(df: pd.DataFrame) -> list[Issue]:
    issues: list[Issue] = []

    for col, expected in FIXED_VALUE_RULES.items():
        if col not in df.columns:
            continue

        for _, row in df.iterrows():
            actual = normalize_text(row.get(col, ""))
            if actual and actual != expected:
                issues.append(
                    Issue(
                        row_number=row.get("Source Row Number"),
                        column=col,
                        severity=SEVERITY_BLOCKER,
                        rule="Invalid Fixed Value",
                        message=f"'{col}' must equal '{expected}'",
                        actual_value=actual,
                        expected_value=expected,
                    )
                )

    return issues


def validate_channel_rules(df: pd.DataFrame) -> list[Issue]:
    issues: list[Issue] = []

    if "Channel" not in df.columns:
        return issues

    for _, row in df.iterrows():
        channel = normalize_text(row.get("Channel", ""))
        if not channel:
            continue

        if channel in INVALID_CHANNEL_WARNING_MAP:
            issues.append(
                Issue(
                    row_number=row.get("Source Row Number"),
                    column="Channel",
                    severity=SEVERITY_WARNING,
                    rule="Invalid Channel Naming",
                    message=f"Use 'X' instead of '{channel}'",
                    actual_value=channel,
                    expected_value="X",
                )
            )
        elif channel not in ALLOWED_CHANNELS:
            issues.append(
                Issue(
                    row_number=row.get("Source Row Number"),
                    column="Channel",
                    severity=SEVERITY_WARNING,
                    rule="Unexpected Channel Value",
                    message=f"Channel '{channel}' is not in allowed list",
                    actual_value=channel,
                )
            )

    return issues


def validate_message_rules(df: pd.DataFrame) -> list[Issue]:
    issues: list[Issue] = []

    if "Message" not in df.columns:
        return issues

    for _, row in df.iterrows():
        message = normalize_text(row.get("Message", ""))
        if not message:
            continue

        hashtags = extract_hashtags(message)
        if hashtags:
            issues.append(
                Issue(
                    row_number=row.get("Source Row Number"),
                    column="Message",
                    severity=SEVERITY_WARNING,
                    rule="Hashtags in Message",
                    message="Message should not contain hashtags",
                    actual_value=", ".join(hashtags),
                )
            )

        if contains_url(message):
            issues.append(
                Issue(
                    row_number=row.get("Source Row Number"),
                    column="Message",
                    severity=SEVERITY_WARNING,
                    rule="URL in Message",
                    message="Message should not contain URLs",
                )
            )

    return issues


def validate_hashtag_rules(df: pd.DataFrame) -> list[Issue]:
    issues: list[Issue] = []

    if "HASHTAGS" not in df.columns:
        return issues

    for _, row in df.iterrows():
        raw_hashtags = parse_hashtags_cell(row.get("HASHTAGS", ""))
        if not raw_hashtags:
            continue

        unique_tags = {normalize_hashtag(tag) for tag in raw_hashtags if normalize_hashtag(tag)}
        if len(unique_tags) > 2:
            issues.append(
                Issue(
                    row_number=row.get("Source Row Number"),
                    column="HASHTAGS",
                    severity=SEVERITY_WARNING,
                    rule="Too Many Hashtags",
                    message="HASHTAGS contains more than 2 unique hashtags",
                    actual_value=", ".join(sorted(unique_tags)),
                    expected_value="Maximum 2 unique hashtags",
                )
            )

    return issues


def validate_x_character_limit(df: pd.DataFrame) -> list[Issue]:
    issues: list[Issue] = []

    if "Channel" not in df.columns or "Character count" not in df.columns:
        return issues

    for _, row in df.iterrows():
        channel = normalize_text(row.get("Channel", ""))
        if channel != "X":
            continue

        raw_count = normalize_text(row.get("Character count", ""))
        if not raw_count:
            continue

        try:
            count = int(float(raw_count))
        except ValueError:
            issues.append(
                Issue(
                    row_number=row.get("Source Row Number"),
                    column="Character count",
                    severity=SEVERITY_WARNING,
                    rule="Invalid Character Count",
                    message="Character count is not numeric",
                    actual_value=raw_count,
                )
            )
            continue

        if count > 197:
            issues.append(
                Issue(
                    row_number=row.get("Source Row Number"),
                    column="Character count",
                    severity=SEVERITY_WARNING,
                    rule="X Character Limit",
                    message="Character count exceeds 197 for X",
                    actual_value=str(count),
                    expected_value="<= 197",
                )
            )

    return issues


def validate_concatenate_rule(df: pd.DataFrame) -> list[Issue]:
    issues: list[Issue] = []

    needed = {"Channel", "Media Title", "Language", "Asset Name"}
    if not needed.issubset(df.columns):
        return issues

    for _, row in df.iterrows():
        channel = normalize_text(row.get("Channel", ""))
        media_title = normalize_text(row.get("Media Title", ""))
        language = normalize_text(row.get("Language", ""))
        asset_name = normalize_text(row.get("Asset Name", ""))

        if not all([channel, media_title, language, asset_name]):
            continue

        expected = f"{channel} - {media_title} - {language}"
        if asset_name != expected:
            issues.append(
                Issue(
                    row_number=row.get("Source Row Number"),
                    column="Asset Name",
                    severity=SEVERITY_WARNING,
                    rule="Concatenate Mismatch",
                    message="Asset Name does not match required concatenate format",
                    actual_value=asset_name,
                    expected_value=expected,
                )
            )

    return issues


def validate_media_rules(df: pd.DataFrame) -> list[Issue]:
    issues: list[Issue] = []

    needed = {
        "Partner CF:Post Media Type",
        "IMAGE-NAME",
        "Asset link",
        "Image or Video copy",
        "Alt-Text",
    }
    if not needed.issubset(df.columns):
        return issues

    for _, row in df.iterrows():
        row_number = row.get("Source Row Number")
        media_type = normalize_text(row.get("Partner CF:Post Media Type", ""))
        image_name = normalize_text(row.get("IMAGE-NAME", ""))
        asset_link = normalize_text(row.get("Asset link", ""))
        image_video_copy = normalize_text(row.get("Image or Video copy", ""))
        alt_text = normalize_text(row.get("Alt-Text", ""))

        has_media_type = not is_blank(media_type)
        has_image_name = not is_blank(image_name)
        has_asset_link = not is_blank(asset_link)

        if (has_image_name or has_asset_link) and not has_media_type:
            issues.append(
                Issue(
                    row_number=row_number,
                    column="Partner CF:Post Media Type",
                    severity=SEVERITY_BLOCKER,
                    rule="Missing Media Type",
                    message=(
                        "Partner CF:Post Media Type is required when IMAGE-NAME "
                        "or Asset link contains a value."
                    ),
                )
            )
            continue

        if not has_media_type:
            continue

        if media_type == TEXT_ONLY_VALUE:
            if has_image_name or has_asset_link:
                issues.append(
                    Issue(
                        row_number=row_number,
                        column="Partner CF:Post Media Type",
                        severity=SEVERITY_WARNING,
                        rule="Text-only With Assets",
                        message=(
                            "Text-only post contains IMAGE-NAME or Asset link. "
                            "Confirm whether the media type is correct."
                        ),
                        actual_value=media_type,
                    )
                )
            continue

        if not has_image_name:
            issues.append(
                Issue(
                    row_number=row_number,
                    column="IMAGE-NAME",
                    severity=SEVERITY_BLOCKER,
                    rule="Missing Media Filename",
                    message=(
                        "IMAGE-NAME is required when Partner CF:Post Media Type "
                        "contains a value other than 'Text-only'."
                    ),
                )
            )

        if not has_asset_link:
            issues.append(
                Issue(
                    row_number=row_number,
                    column="Asset link",
                    severity=SEVERITY_BLOCKER,
                    rule="Missing Asset Link",
                    message=(
                        "Asset link is required when Partner CF:Post Media Type "
                        "contains a value other than 'Text-only'."
                    ),
                )
            )
        else:
            if "\n" in asset_link or "\r" in asset_link:
                issues.append(
                    Issue(
                        row_number=row_number,
                        column="Asset link",
                        severity=SEVERITY_BLOCKER,
                        rule="Multiple Asset Links",
                        message="Asset link must contain only one URL",
                        actual_value=asset_link,
                    )
                )
            elif not is_valid_https_url(asset_link):
                issues.append(
                    Issue(
                        row_number=row_number,
                        column="Asset link",
                        severity=SEVERITY_BLOCKER,
                        rule="Invalid Asset Link",
                        message="Asset link must be one valid https:// URL",
                        actual_value=asset_link,
                        expected_value="Single valid https:// URL",
                    )
                )

        allowed_extensions = MEDIA_EXTENSION_RULES.get(media_type)
        filenames = clean_multiline_filenames(image_name)

        if has_image_name and allowed_extensions:
            for filename in filenames:
                ext = get_extension(filename)
                if ext not in allowed_extensions:
                    issues.append(
                        Issue(
                            row_number=row_number,
                            column="IMAGE-NAME",
                            severity=SEVERITY_BLOCKER,
                            rule="Invalid Media File Extension",
                            message=f"Invalid file extension for media type '{media_type}'",
                            actual_value=filename,
                            expected_value=", ".join(sorted(allowed_extensions)),
                        )
                    )

        if is_blank(image_video_copy):
            issues.append(
                Issue(
                    row_number=row_number,
                    column="Image or Video copy",
                    severity=SEVERITY_WARNING,
                    rule="Missing Image/Video Copy",
                    message="Image or Video copy is blank",
                )
            )

        if media_type in IMAGE_TYPES_FOR_ALT_TEXT and is_blank(alt_text):
            issues.append(
                Issue(
                    row_number=row_number,
                    column="Alt-Text",
                    severity=SEVERITY_WARNING,
                    rule="Missing Alt-Text",
                    message="Alt-Text is blank for image-type media",
                )
            )

    return issues


def validate_autofill_logic(df: pd.DataFrame, autofill_df: pd.DataFrame) -> list[Issue]:
    issues: list[Issue] = []

    input_autofill_col = "Partner CF:Global Autofill Tagging"
    source_value_col = "Global Autofill Value"

    if input_autofill_col not in df.columns:
        issues.append(
            Issue(
                row_number=None,
                column=input_autofill_col,
                severity=SEVERITY_BLOCKER,
                rule="Autofill Source Error",
                message=f"Required column missing from input file: '{input_autofill_col}'",
            )
        )
        return issues

    if source_value_col not in autofill_df.columns:
        issues.append(
            Issue(
                row_number=None,
                column=source_value_col,
                severity=SEVERITY_BLOCKER,
                rule="Autofill Source Error",
                message=(
                    f"Required Autofill value source missing from Global Autofill Rule workbook: "
                    f"'{source_value_col}'"
                ),
            )
        )
        return issues

    valid_autofill_values = {
        normalize_autofill_value(value)
        for value in autofill_df[source_value_col].tolist()
        if not is_blank(value)
    }

    # TEMP DEBUG
    print("SAMPLE VALID AUTOFILL VALUES:", list(sorted(valid_autofill_values))[:20])

    for _, row in df.iterrows():
        row_number = row.get("Source Row Number")
        raw_value = normalize_text(row.get(input_autofill_col, ""))

        if not raw_value:
            continue

        # TEMP DEBUG
        print("RAW INPUT VALUE:", repr(raw_value))

        split_values = [part.strip() for part in raw_value.splitlines() if part.strip()]
        if not split_values:
            split_values = [raw_value.strip()]

        if len(split_values) != 1:
            issues.append(
                Issue(
                    row_number=row_number,
                    column=input_autofill_col,
                    severity=SEVERITY_BLOCKER,
                    rule="Multiple Autofill Values",
                    message="Partner CF:Global Autofill Tagging must contain only one value",
                    actual_value=raw_value,
                )
            )
            continue

        autofill_value = split_values[0]
        normalized_autofill_value = normalize_autofill_value(autofill_value)

        # TEMP DEBUG
        print("NORMALIZED INPUT VALUE:", repr(normalized_autofill_value))

        if normalized_autofill_value not in valid_autofill_values:
            issues.append(
                Issue(
                    row_number=row_number,
                    column=input_autofill_col,
                    severity=SEVERITY_BLOCKER,
                    rule="Autofill Not Found",
                    message=(
                        "Partner CF:Global Autofill Tagging value was not found in "
                        "row 1 (columns B onward) of any tab in Global Autofill Rule.xlsx"
                    ),
                    actual_value=autofill_value,
                )
            )

    return issues