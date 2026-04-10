from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = [
    "Message Name",
    "Channel",
    "LCID",
    "Campaigns",
    "Message",
    "URL",
    "HASHTAGS",
    "Message (message+url+hashtags)",
]


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


def normalize_channel(value: Any) -> Any:
    if pd.isna(value):
        return value

    channel_map = {
        "twitter": "X",
        "x": "X",
        "x/twitter": "X",
    }

    v = str(value).strip().lower()
    return channel_map.get(v, str(value).strip())


def normalize_lcid(value: Any) -> str:
    if pd.isna(value):
        return ""

    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def add_issue(
    issues: list[dict[str, Any]],
    row_index: int | None,
    message_name: str,
    channel: str,
    field: str,
    severity: str,
    issue: str,
    description: str,
) -> None:
    issues.append({
        "Row": "" if row_index is None else row_index + 2,
        "Message Name": message_name,
        "Channel": channel,
        "Field": field,
        "Severity": severity,
        "Issue": issue,
        "Description": description,
    })


def load_localization_return(project_root: Path, filename: str) -> pd.DataFrame:
    file_path = project_root / "03_localization_return" / filename
    df = pd.read_excel(file_path)
    df = clean_columns(df)
    df["Channel_original"] = df["Channel"]
    df["Channel"] = df["Channel"].apply(normalize_channel)
    if "LCID" in df.columns:
        df["LCID"] = df["LCID"].apply(normalize_lcid)
    return df


def validate_required_columns(df: pd.DataFrame, required_columns: list[str]) -> None:
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in localization return file: {missing}")


def load_required_lcids(project_root: Path) -> set[str]:
    lcid_path = project_root / "06_tracking" / "lcid_mapping.csv"
    lcid_df = pd.read_csv(lcid_path, encoding="utf-8-sig")
    lcid_df.columns = lcid_df.columns.str.strip()

    if "LCID" not in lcid_df.columns:
        raise ValueError("lcid_mapping.csv must contain an 'LCID' column.")

    required_lcids = set(
        lcid_df["LCID"]
        .apply(normalize_lcid)
        .loc[lambda s: s != ""]
        .tolist()
    )

    if not required_lcids:
        raise ValueError("No valid LCIDs found in lcid_mapping.csv.")

    return required_lcids


def check_blank_cells_excluding_fully_blank_columns(df: pd.DataFrame, issues: list[dict[str, Any]]) -> None:
    fully_blank_columns = []
    for col in df.columns:
        series = df[col]
        normalized = series.fillna("").astype(str).str.strip()
        if (normalized == "").all():
            fully_blank_columns.append(col)

    columns_to_check = [c for c in df.columns if c not in fully_blank_columns]

    for idx, row in df.iterrows():
        message_name = "" if pd.isna(row.get("Message Name")) else str(row.get("Message Name")).strip()
        channel = "" if pd.isna(row.get("Channel")) else str(row.get("Channel")).strip()

        for col in columns_to_check:
            value = row[col]
            if pd.isna(value) or str(value).strip() == "":
                add_issue(
                    issues,
                    idx,
                    message_name,
                    channel,
                    col,
                    "BLOCKER",
                    "Blank cell detected",
                    f"Blank value found in column '{col}'. Entirely blank columns are allowed, but individual blanks are not.",
                )


def check_campaigns_value(df: pd.DataFrame, issues: list[dict[str, Any]]) -> None:
    for idx, row in df.iterrows():
        campaigns = "" if pd.isna(row["Campaigns"]) else str(row["Campaigns"]).strip()
        message_name = "" if pd.isna(row["Message Name"]) else str(row["Message Name"]).strip()
        channel = "" if pd.isna(row["Channel"]) else str(row["Channel"]).strip()

        if campaigns != "Social: Broadcast":
            add_issue(
                issues,
                idx,
                message_name,
                channel,
                "Campaigns",
                "BLOCKER",
                "Invalid Campaigns value",
                "Campaigns must be 'Social: Broadcast'.",
            )


def check_group_consistency(df: pd.DataFrame, issues: list[dict[str, Any]]) -> None:
    consistency_columns = [
        "Asset Type",
        "Campaigns",
        "Partner CF:Global Autofill Tagging",
        "Partner CF:E&E Moments & Campaigns",
        "Topic (second level)",
        "Event Workstream",
        "Partner CF:Creator (Second Level Tagging)",
        "Partner CF:URL Content Type (Level 1)",
        "Partner CF:URL Content Type (Level 2)",
        "Partner CF:Post Media Type",
        "Partner CF:Language",
        "Partner CF:Language_GSM",
        "Channel",
        "Type Of Message",
        "Media Title",
        "IMAGE-NAME",
    ]

    grouped = df.groupby(["Message Name", "Channel"], dropna=False)

    for (message_name, channel), group in grouped:
        for col in consistency_columns:
            values = group[col].fillna("").astype(str).str.strip().unique()
            values = [v for v in values if v != ""]
            if len(values) > 1:
                for idx in group.index:
                    add_issue(
                        issues,
                        idx,
                        "" if pd.isna(message_name) else str(message_name).strip(),
                        "" if pd.isna(channel) else str(channel).strip(),
                        col,
                        "BLOCKER",
                        "Inconsistent grouped value",
                        f"Column '{col}' must be identical for each Message Name + Channel group.",
                    )


def check_message_concat(df: pd.DataFrame, issues: list[dict[str, Any]]) -> None:
    for idx, row in df.iterrows():
        message_name = "" if pd.isna(row["Message Name"]) else str(row["Message Name"]).strip()
        channel = "" if pd.isna(row["Channel"]) else str(row["Channel"]).strip()

        col_n = "" if pd.isna(row["Message (message+url+hashtags)"]) else str(row["Message (message+url+hashtags)"]).strip()
        message = "" if pd.isna(row["Message"]) else str(row["Message"]).strip()
        url = "" if pd.isna(row["URL"]) else str(row["URL"]).strip()
        hashtags = "" if pd.isna(row["HASHTAGS"]) else str(row["HASHTAGS"]).strip()

        expected = f"{message}{url}{hashtags}".strip()

        if col_n != expected:
            add_issue(
                issues,
                idx,
                message_name,
                channel,
                "Message (message+url+hashtags)",
                "WARNING",
                "Concatenation mismatch",
                "Column 'Message (message+url+hashtags)' does not match Message + URL + HASHTAGS.",
            )


def check_x_character_limit_280(df: pd.DataFrame, issues: list[dict[str, Any]]) -> None:
    for idx, row in df.iterrows():
        channel = "" if pd.isna(row["Channel"]) else str(row["Channel"]).strip()
        message_name = "" if pd.isna(row["Message Name"]) else str(row["Message Name"]).strip()
        text = "" if pd.isna(row["Message (message+url+hashtags)"]) else str(row["Message (message+url+hashtags)"]).strip()

        if channel == "X" and len(text) > 280:
            add_issue(
                issues,
                idx,
                message_name,
                channel,
                "Message (message+url+hashtags)",
                "BLOCKER",
                "Character limit exceeded",
                f"X posts must be <= 280 characters. Current length: {len(text)}",
            )


def check_lcid_coverage(df: pd.DataFrame, issues: list[dict[str, Any]], required_lcids: set[str]) -> None:
    grouped = df.groupby(["Message Name", "Channel"], dropna=False)
    expected_count = len(required_lcids)

    for (message_name, channel), group in grouped:
        group_message_name = "" if pd.isna(message_name) else str(message_name).strip()
        group_channel = "" if pd.isna(channel) else str(channel).strip()

        normalized_lcids = group["LCID"].apply(normalize_lcid)
        non_blank_lcids = normalized_lcids[normalized_lcids != ""]

        actual_row_count = len(group)
        actual_lcid_set = set(non_blank_lcids)

        missing_lcids = sorted(required_lcids - actual_lcid_set)
        unexpected_lcids = sorted(actual_lcid_set - required_lcids)
        duplicate_lcids = non_blank_lcids[non_blank_lcids.duplicated()].unique().tolist()
        blank_lcid_count = int((normalized_lcids == "").sum())

        if actual_row_count != expected_count:
            add_issue(
                issues,
                None,
                group_message_name,
                group_channel,
                "LCID",
                "BLOCKER",
                "Invalid row count",
                f"Expected exactly {expected_count} rows for this Message Name + Channel group, but found {actual_row_count}.",
            )

        if missing_lcids:
            add_issue(
                issues,
                None,
                group_message_name,
                group_channel,
                "LCID",
                "BLOCKER",
                "Missing LCIDs",
                f"Missing LCIDs for Message Name + Channel group: {missing_lcids}",
            )

        if unexpected_lcids:
            add_issue(
                issues,
                None,
                group_message_name,
                group_channel,
                "LCID",
                "BLOCKER",
                "Unexpected LCIDs",
                f"Unexpected LCIDs found for Message Name + Channel group: {unexpected_lcids}",
            )

        if duplicate_lcids:
            add_issue(
                issues,
                None,
                group_message_name,
                group_channel,
                "LCID",
                "BLOCKER",
                "Duplicate LCIDs",
                f"Duplicate LCIDs found for Message Name + Channel group: {duplicate_lcids}",
            )

        if blank_lcid_count > 0:
            add_issue(
                issues,
                None,
                group_message_name,
                group_channel,
                "LCID",
                "BLOCKER",
                "Blank LCIDs",
                f"Found {blank_lcid_count} blank LCID row(s) in this Message Name + Channel group.",
            )


def run_localization_return_qa(df: pd.DataFrame, required_lcids: set[str]) -> pd.DataFrame:
    issues: list[dict[str, Any]] = []

    check_blank_cells_excluding_fully_blank_columns(df, issues)
    check_campaigns_value(df, issues)
    check_group_consistency(df, issues)
    check_message_concat(df, issues)
    check_x_character_limit_280(df, issues)
    check_lcid_coverage(df, issues, required_lcids)

    return pd.DataFrame(issues)


def run_full_localization_qa(project_root: Path, filename: str) -> pd.DataFrame:
    df = load_localization_return(project_root, filename)

    validate_required_columns(df, REQUIRED_COLUMNS)

    required_lcids = load_required_lcids(project_root)

    issues_df = run_localization_return_qa(df, required_lcids)

    output_path = project_root / "04_qa_output" / "qa_issues.xlsx"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    issues_df.to_excel(output_path, index=False)

    if issues_df.empty:
        print("✅ QA PASSED — No issues found")
    else:
        print(f"❌ QA FAILED — {len(issues_df)} issues found")

    print(f"QA complete. Output saved to: {output_path}")

    return issues_df