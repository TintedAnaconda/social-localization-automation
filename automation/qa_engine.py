from __future__ import annotations

import os
from typing import Any

import pandas as pd


def normalize_channel(value: Any) -> Any:
    if pd.isna(value):
        return value

    channel_normalization = {
        "twitter": "X",
        "x": "X",
        "x/twitter": "X",
    }

    v = str(value).strip().lower()
    return channel_normalization.get(v, str(value).strip())


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns
        .str.replace("\ufeff", "", regex=False)
        .str.replace("\xa0", " ", regex=False)
        .str.replace("\n", " ", regex=False)
        .str.replace("\r", " ", regex=False)
        .str.strip()
    )
    return df


def validate_required_columns(df: pd.DataFrame, required_columns: list[str]) -> None:
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")


def clean_hashtags(text: Any) -> str:
    if pd.isna(text):
        return ""
    return str(text).replace("#", " ").strip()


def add_issue(
    qa_issues: list[dict[str, Any]],
    row_index: int,
    message_name: str,
    channel: str,
    field: str,
    severity: str,
    issue: str,
    description: str,
) -> None:
    qa_issues.append({
        "Row": row_index + 2,
        "Message Name": message_name,
        "Channel": channel,
        "Field": field,
        "Severity": severity,
        "Issue": issue,
        "Description": description,
    })


def check_duplicate_message_channel(df: pd.DataFrame, qa_issues: list[dict[str, Any]]) -> None:
    duplicate_check_df = df.copy()
    duplicate_check_df["Message Name"] = duplicate_check_df["Message Name"].fillna("").astype(str).str.strip()
    duplicate_check_df["Channel"] = duplicate_check_df["Channel"].fillna("").astype(str).str.strip()

    duplicate_check_df = duplicate_check_df[
        (duplicate_check_df["Message Name"] != "") &
        (duplicate_check_df["Channel"] != "")
    ]

    duplicate_rows = duplicate_check_df[
        duplicate_check_df.duplicated(subset=["Message Name", "Channel"], keep=False)
    ]

    for idx, row in duplicate_rows.iterrows():
        add_issue(
            qa_issues=qa_issues,
            row_index=idx,
            message_name=row["Message Name"],
            channel=row["Channel"],
            field="Message Name + Channel",
            severity="BLOCKER",
            issue="Duplicate combination",
            description="Message Name + Channel must be unique.",
        )


def check_channel_values(df: pd.DataFrame, qa_issues: list[dict[str, Any]]) -> None:
    valid_channels = ["LinkedIn", "X", "Instagram", "Facebook", "Threads"]

    for idx, row in df.iterrows():
        channel = "" if pd.isna(row["Channel"]) else str(row["Channel"]).strip()
        message_name = "" if pd.isna(row["Message Name"]) else str(row["Message Name"]).strip()

        if channel not in valid_channels:
            add_issue(
                qa_issues=qa_issues,
                row_index=idx,
                message_name=message_name,
                channel=channel,
                field="Channel",
                severity="BLOCKER",
                issue="Invalid channel",
                description=f"Channel must be one of {valid_channels}",
            )


def check_x_character_limit(df: pd.DataFrame, qa_issues: list[dict[str, Any]]) -> None:
    for idx, row in df.iterrows():
        channel = "" if pd.isna(row["Channel"]) else str(row["Channel"]).strip()
        message_name = "" if pd.isna(row["Message Name"]) else str(row["Message Name"]).strip()
        message = "" if pd.isna(row["Message"]) else str(row["Message"]).strip()
        hashtags = "" if pd.isna(row["HASHTAGS"]) else str(row["HASHTAGS"]).strip()

        if channel == "X":
            combined_text = f"{message} {hashtags}".strip()
            char_count = len(combined_text)

            if char_count > 197:
                add_issue(
                    qa_issues=qa_issues,
                    row_index=idx,
                    message_name=message_name,
                    channel=channel,
                    field="Message + HASHTAGS",
                    severity="BLOCKER",
                    issue="Character limit exceeded",
                    description=f"X posts must be ≤ 197 characters. Current length: {char_count}",
                )


def check_instagram_rules(df: pd.DataFrame, qa_issues: list[dict[str, Any]]) -> None:
    instagram_cta_phrases = [
        "link in bio",
	"link in the bio",
        "check the link in bio",
        "tap the link in bio",
        "see link in bio",
        "see the link in bio",
        "learn more at the link in bio",
        "learn more via link in bio",
    ]

    for idx, row in df.iterrows():
        channel = "" if pd.isna(row["Channel"]) else str(row["Channel"]).strip()
        message_name = "" if pd.isna(row["Message Name"]) else str(row["Message Name"]).strip()
        message = "" if pd.isna(row["Message"]) else str(row["Message"]).strip()
        message_lower = message.lower()

        if channel.lower() == "instagram":
            if "http://" in message_lower or "https://" in message_lower or "www." in message_lower:
                add_issue(
                    qa_issues=qa_issues,
                    row_index=idx,
                    message_name=message_name,
                    channel=channel,
                    field="Message",
                    severity="BLOCKER",
                    issue="URL not allowed",
                    description="Instagram social copy cannot include URLs.",
                )

            if not any(phrase in message_lower for phrase in instagram_cta_phrases):
                add_issue(
                    qa_issues=qa_issues,
                    row_index=idx,
                    message_name=message_name,
                    channel=channel,
                    field="Message",
                    severity="WARNING",
                    issue="Missing link in bio CTA",
                    description="Instagram posts should include a CTA directing users to the link in bio.",
                )


def check_asset_rules(df: pd.DataFrame, qa_issues: list[dict[str, Any]]) -> None:
    media_type_column = "Partner CF:Post Media Type"

    image_media_types = {"image (illustration)", "image (photography)", "carousel"}
    valid_image_extensions = {".png", ".jpg", ".jpeg"}
    valid_video_extensions = {".mp4"}
    valid_pdf_extensions = {".pdf"}

    for idx, row in df.iterrows():
        media_type = "" if pd.isna(row[media_type_column]) else str(row[media_type_column]).strip().lower()
        image_name = "" if pd.isna(row["IMAGE-NAME"]) else str(row["IMAGE-NAME"]).strip()
        alt_text = "" if pd.isna(row["Alt-Text"]) else str(row["Alt-Text"]).strip()
        message_name = "" if pd.isna(row["Message Name"]) else str(row["Message Name"]).strip()
        channel = "" if pd.isna(row["Channel"]) else str(row["Channel"]).strip()

        _, extension = os.path.splitext(image_name)
        extension = extension.lower().strip()

        is_image = media_type in image_media_types
        is_video = media_type.startswith("video")
        is_linkedin_doc = media_type == "linkedin document ad"

        if is_image and alt_text == "":
            add_issue(
                qa_issues=qa_issues,
                row_index=idx,
                message_name=message_name,
                channel=channel,
                field="Alt-Text",
                severity="WARNING",
                issue="Missing Alt Text",
                description="Alt Text is required for Image (Illustration), Image (Photography), and Carousel.",
            )

        if is_image:
            if image_name == "":
                add_issue(
                    qa_issues=qa_issues,
                    row_index=idx,
                    message_name=message_name,
                    channel=channel,
                    field="IMAGE-NAME",
                    severity="BLOCKER",
                    issue="Missing asset file name",
                    description="IMAGE-NAME is required for image and carousel assets.",
                )
            elif extension == "":
                add_issue(
                    qa_issues=qa_issues,
                    row_index=idx,
                    message_name=message_name,
                    channel=channel,
                    field="IMAGE-NAME",
                    severity="BLOCKER",
                    issue="Missing file extension",
                    description="Image and Carousel assets must include .png, .jpg, or .jpeg.",
                )
            elif extension not in valid_image_extensions:
                add_issue(
                    qa_issues=qa_issues,
                    row_index=idx,
                    message_name=message_name,
                    channel=channel,
                    field="IMAGE-NAME",
                    severity="BLOCKER",
                    issue="Invalid image file type",
                    description="Image and Carousel assets must end with .png, .jpg, or .jpeg.",
                )

        if is_video:
            if image_name == "":
                add_issue(
                    qa_issues=qa_issues,
                    row_index=idx,
                    message_name=message_name,
                    channel=channel,
                    field="IMAGE-NAME",
                    severity="BLOCKER",
                    issue="Missing asset file name",
                    description="IMAGE-NAME is required for video assets.",
                )
            elif extension == "":
                add_issue(
                    qa_issues=qa_issues,
                    row_index=idx,
                    message_name=message_name,
                    channel=channel,
                    field="IMAGE-NAME",
                    severity="BLOCKER",
                    issue="Missing file extension",
                    description="Video assets must include the .mp4 file extension.",
                )
            elif extension not in valid_video_extensions:
                add_issue(
                    qa_issues=qa_issues,
                    row_index=idx,
                    message_name=message_name,
                    channel=channel,
                    field="IMAGE-NAME",
                    severity="BLOCKER",
                    issue="Invalid video file type",
                    description=f"Video assets ({row[media_type_column]}) must end with .mp4.",
                )

        if is_linkedin_doc:
            if image_name == "":
                add_issue(
                    qa_issues=qa_issues,
                    row_index=idx,
                    message_name=message_name,
                    channel=channel,
                    field="IMAGE-NAME",
                    severity="BLOCKER",
                    issue="Missing asset file name",
                    description="IMAGE-NAME is required for LinkedIn Document Ad assets.",
                )
            elif extension == "":
                add_issue(
                    qa_issues=qa_issues,
                    row_index=idx,
                    message_name=message_name,
                    channel=channel,
                    field="IMAGE-NAME",
                    severity="BLOCKER",
                    issue="Missing file extension",
                    description="LinkedIn Document Ad assets must include the .pdf file extension.",
                )
            elif extension not in valid_pdf_extensions:
                add_issue(
                    qa_issues=qa_issues,
                    row_index=idx,
                    message_name=message_name,
                    channel=channel,
                    field="IMAGE-NAME",
                    severity="BLOCKER",
                    issue="Invalid document file type",
                    description="LinkedIn Document Ad assets must end with .pdf.",
                )


def check_url_format(df: pd.DataFrame, qa_issues: list[dict[str, Any]]) -> None:
    for idx, row in df.iterrows():
        url = "" if pd.isna(row["URL"]) else str(row["URL"]).strip()
        message_name = "" if pd.isna(row["Message Name"]) else str(row["Message Name"]).strip()
        channel = "" if pd.isna(row["Channel"]) else str(row["Channel"]).strip()

        if url != "" and not url.lower().startswith("https://"):
            add_issue(
                qa_issues=qa_issues,
                row_index=idx,
                message_name=message_name,
                channel=channel,
                field="URL",
                severity="BLOCKER",
                issue="Invalid URL format",
                description="CTA URL must start with https://",
            )


def check_grammar(
    df: pd.DataFrame,
    qa_issues: list[dict[str, Any]],
    tool: Any,
) -> None:
    fields_to_check = ["Message", "HASHTAGS", "Alt-Text", "Image or video copy"]

    for idx, row in df.iterrows():
        message_name = "" if pd.isna(row["Message Name"]) else str(row["Message Name"]).strip()
        channel = "" if pd.isna(row["Channel"]) else str(row["Channel"]).strip()

        for field in fields_to_check:
            text = row[field]

            if field == "HASHTAGS":
                text = clean_hashtags(text)

            if pd.isna(text) or str(text).strip() == "":
                continue

            matches = tool.check(str(text))

            for match in matches:
                add_issue(
                    qa_issues=qa_issues,
                    row_index=idx,
                    message_name=message_name,
                    channel=channel,
                    field=field,
                    severity="WARNING",
                    issue="Spelling/Grammar issue",
                    description=match.message,
                )


def run_all_qa(df: pd.DataFrame, tool: Any) -> pd.DataFrame:
    qa_issues: list[dict[str, Any]] = []

    check_duplicate_message_channel(df, qa_issues)
    check_channel_values(df, qa_issues)
    check_x_character_limit(df, qa_issues)
    check_instagram_rules(df, qa_issues)
    check_asset_rules(df, qa_issues)
    check_url_format(df, qa_issues)
    check_grammar(df, qa_issues, tool)

    return pd.DataFrame(qa_issues)