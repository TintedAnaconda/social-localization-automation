from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from openpyxl.utils import get_column_letter

from qa_language_checks import build_language_tool, validate_language_quality
from qa_models import Issue
from qa_required_columns import validate_required_headers, validate_required_values
from qa_utils import (
    add_source_row_number,
    clean_object_columns,
    filter_rows_with_message_name,
)
from qa_validators import (
    validate_autofill_logic,
    validate_channel_rules,
    validate_concatenate_rule,
    validate_fixed_values,
    validate_hashtag_rules,
    validate_media_rules,
    validate_message_rules,
    validate_x_character_limit,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config"
INPUT_DIR = REPO_ROOT / "input"
OUTPUT_DIR = REPO_ROOT / "output" / "qa_reports"
LOGS_DIR = REPO_ROOT / "logs"

GLOBAL_AUTOFILL_PATH = CONFIG_DIR / "Global Autofill Rule.xlsx"
if not GLOBAL_AUTOFILL_PATH.exists():
    raise FileNotFoundError(
        f"Missing required config file: {GLOBAL_AUTOFILL_PATH}"
    )

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

EMAIL_TEMPLATE_DIR = REPO_ROOT / "output" / "localization_email_templates"
EMAIL_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS_DIR / "qa_engine.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def choose_latest_input_file(input_dir: Path) -> Optional[Path]:
    excel_files = sorted(
        [
            p for p in input_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".xlsx", ".xls"}
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not excel_files:
        logger.warning(f"No Excel files found in {input_dir}")
        return None

    return excel_files[0]


def load_input_excel(path: Path) -> pd.DataFrame:
    logger.info("Loading input file: %s", path)
    df = pd.read_excel(path, dtype=object)
    df = add_source_row_number(df)
    return df


def load_autofill_values_from_row1(path: Path) -> pd.DataFrame:
    logger.info(
        "Loading Global Autofill source "
        "(row 1 values from all sheets, skipping column A): %s",
        path,
    )

    dfs: list[pd.DataFrame] = []
    xl = pd.ExcelFile(path)

    for sheet in xl.sheet_names:
        raw_df = pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)

        if raw_df.empty:
            continue

        row1_values = raw_df.iloc[0].tolist()
        candidate_values = row1_values[1:]

        cleaned_values = [
            str(v).replace("\u00A0", " ").strip()
            for v in candidate_values
            if pd.notna(v) and str(v).strip()
        ]

        if not cleaned_values:
            logger.info(
                "Skipping sheet (no Autofill values found in row 1 after column A): %s",
                sheet,
            )
            continue

        logger.info(
            "Sheet '%s' loaded %s Autofill value(s) from row 1",
            sheet,
            len(cleaned_values),
        )

        sheet_df = pd.DataFrame(
            {
                "Global Autofill Value": cleaned_values,
                "__source_sheet": sheet,
            }
        )
        dfs.append(sheet_df)

    if not dfs:
        raise ValueError(
            "No valid Autofill values found in row 1 "
            "(columns B onward) of Global Autofill Rule.xlsx"
        )

    combined_df = pd.concat(dfs, ignore_index=True)
    logger.info(
        "Loaded %s sheet(s) with %s total Autofill values",
        len(dfs),
        len(combined_df),
    )

    return combined_df


def has_blocking_header_issues(issues: list[Issue]) -> bool:
    return any(
        issue.severity == "BLOCKER"
        and issue.rule in {"Missing Header", "Header Mismatch"}
        for issue in issues
    )


def build_summary_df(
    input_rows: int,
    qa_rows: int,
    skipped_rows: int,
    issues_df: pd.DataFrame,
) -> pd.DataFrame:
    blocker_count = (
        int((issues_df["severity"] == "BLOCKER").sum())
        if not issues_df.empty
        else 0
    )
    warning_count = (
        int((issues_df["severity"] == "WARNING").sum())
        if not issues_df.empty
        else 0
    )

    status = (
        "FAIL"
        if blocker_count > 0
        else "PASS WITH WARNINGS"
        if warning_count > 0
        else "PASS"
    )

    return pd.DataFrame(
        [
            {"Metric": "Input Rows", "Value": input_rows},
            {"Metric": "QA Rows", "Value": qa_rows},
            {"Metric": "Skipped Rows Without Message Name", "Value": skipped_rows},
            {"Metric": "Total Issues", "Value": len(issues_df)},
            {"Metric": "Blockers", "Value": blocker_count},
            {"Metric": "Warnings", "Value": warning_count},
            {"Metric": "Status", "Value": status},
        ]
    )


def autosize_worksheet(writer, sheet_name: str, df: pd.DataFrame) -> None:
    ws = writer.sheets[sheet_name]

    for idx, col in enumerate(df.columns, start=1):
        values = df[col].astype(str).fillna("").tolist() if not df.empty else []
        max_len = max([len(str(col))] + [len(v) for v in values])
        ws.column_dimensions[get_column_letter(idx)].width = min(max_len + 2, 60)


def write_qa_report(
    summary_df: pd.DataFrame,
    issues_df: pd.DataFrame,
    cleaned_input_df: pd.DataFrame,
    input_file_path: Path,
) -> Path:
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"{input_file_path.stem}_qa_report_{timestamp}.xlsx"

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        issues_df.to_excel(writer, sheet_name="Issues", index=False)
        cleaned_input_df.to_excel(writer, sheet_name="Cleaned Input", index=False)

        autosize_worksheet(writer, "Summary", summary_df)
        autosize_worksheet(writer, "Issues", issues_df)
        autosize_worksheet(writer, "Cleaned Input", cleaned_input_df)

    logger.info("QA report written: %s", output_file)

    return output_file


def write_qa_summary(
    report_path: Path,
    issues_df: pd.DataFrame,
    input_file: Path,
) -> Path:
    if issues_df.empty:
        blocker_count = 0
        warning_count = 0
    else:
        blocker_count = int((issues_df["severity"] == "BLOCKER").sum())
        warning_count = int((issues_df["severity"] == "WARNING").sum())

    if blocker_count > 0:
        status = "BLOCKED"
    elif warning_count > 0:
        status = "PASS_WITH_WARNINGS"
    else:
        status = "PASS"

    summary = {
        "status": status,
        "blocker_count": blocker_count,
        "warning_count": warning_count,
        "qa_report_path": str(report_path),
        "input_file_path": str(input_file),
        "input_file_name": input_file.name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    summary_path = report_path.parent / "qa_summary.json"

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info("QA summary written: %s", summary_path)

    print(f"QA_SUMMARY_PATH={summary_path}")
    print(f"QA_STATUS={status}")
    print(f"BLOCKER_COUNT={blocker_count}")
    print(f"WARNING_COUNT={warning_count}")

    return summary_path


def run_qa(input_file: Optional[Path] = None) -> Optional[Path]:
    if input_file is None:
        input_file = choose_latest_input_file(INPUT_DIR)

    if input_file is None:
        logger.info("No input file found. Skipping QA run.")
        return None

    input_df = load_input_excel(input_file)
    original_input_rows = len(input_df)

    header_issues = validate_required_headers(input_df)

    if has_blocking_header_issues(header_issues):
        issues_df = pd.DataFrame([issue.to_dict() for issue in header_issues])

        summary_df = build_summary_df(
            input_rows=original_input_rows,
            qa_rows=0,
            skipped_rows=original_input_rows,
            issues_df=issues_df,
        )

        report_path = write_qa_report(summary_df, issues_df, input_df, input_file)
        write_qa_summary(report_path, issues_df, input_file)

        blocker_count = int((issues_df["severity"] == "BLOCKER").sum())
        warning_count = int((issues_df["severity"] == "WARNING").sum())

        logger.info(
            "QA complete with blocking header issues | blockers=%s | warnings=%s",
            blocker_count,
            warning_count,
        )

        return report_path

    autofill_df = load_autofill_values_from_row1(GLOBAL_AUTOFILL_PATH)

    working_df = clean_object_columns(input_df)
    working_df = filter_rows_with_message_name(working_df)

    qa_rows = len(working_df)
    skipped_rows = original_input_rows - qa_rows

    issues: list[Issue] = []
    issues.extend(validate_required_values(working_df))
    issues.extend(validate_fixed_values(working_df))
    issues.extend(validate_channel_rules(working_df))
    issues.extend(validate_message_rules(working_df))
    issues.extend(validate_hashtag_rules(working_df))
    issues.extend(validate_x_character_limit(working_df))
    issues.extend(validate_concatenate_rule(working_df))
    issues.extend(validate_media_rules(working_df))
    issues.extend(validate_autofill_logic(working_df, autofill_df))

    tool = build_language_tool()
    issues.extend(validate_language_quality(working_df, tool))

    issues_df = pd.DataFrame([issue.to_dict() for issue in issues])

    if issues_df.empty:
        issues_df = pd.DataFrame(
            columns=[
                "row_number",
                "column",
                "severity",
                "rule",
                "message",
                "actual_value",
                "expected_value",
            ]
        )

    summary_df = build_summary_df(
        input_rows=original_input_rows,
        qa_rows=qa_rows,
        skipped_rows=skipped_rows,
        issues_df=issues_df,
    )

    report_path = write_qa_report(summary_df, issues_df, working_df, input_file)
    write_qa_summary(report_path, issues_df, input_file)

    blocker_count = (
        int((issues_df["severity"] == "BLOCKER").sum())
        if not issues_df.empty
        else 0
    )
    warning_count = (
        int((issues_df["severity"] == "WARNING").sum())
        if not issues_df.empty
        else 0
    )

    logger.info(
        "QA complete | blockers=%s | warnings=%s",
        blocker_count,
        warning_count,
    )

    return report_path


if __name__ == "__main__":
    report = run_qa()
    if report is not None:
        print(f"QA report created: {report}")
    else:
        print("No input file found. QA was skipped.")