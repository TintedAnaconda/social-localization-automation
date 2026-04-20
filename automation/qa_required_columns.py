from __future__ import annotations

import difflib
import pandas as pd

from qa_config import REQUIRED_HEADERS, REQUIRED_VALUE_COLUMNS, SEVERITY_BLOCKER
from qa_models import Issue
from qa_utils import is_blank


def validate_required_headers(df: pd.DataFrame) -> list[Issue]:
    """
    Strict header validation.
    All required headers must exactly match the E&A template.
    Missing headers and slight header differences are BLOCKERS.
    """
    issues: list[Issue] = []
    actual_headers = list(df.columns)
    actual_header_set = set(actual_headers)

    for required_header in REQUIRED_HEADERS:
        if required_header in actual_header_set:
            continue

        close_matches = difflib.get_close_matches(
            required_header,
            actual_headers,
            n=3,
            cutoff=0.75,
        )

        if close_matches:
            issues.append(
                Issue(
                    row_number=None,
                    column=required_header,
                    severity=SEVERITY_BLOCKER,
                    rule="Header Mismatch",
                    message=(
                        f"Required header must exactly match E&A Template header: "
                        f"'{required_header}'. Similar header(s) found in file: "
                        f"{', '.join([repr(h) for h in close_matches])}. "
                        f"Do not rename, shorten, or reformat required headers."
                    ),
                    expected_value=required_header,
                    actual_value=", ".join(close_matches),
                )
            )
        else:
            issues.append(
                Issue(
                    row_number=None,
                    column=required_header,
                    severity=SEVERITY_BLOCKER,
                    rule="Missing Header",
                    message=(
                        f"Required header is missing and must exactly match the "
                        f"E&A Template header: '{required_header}'."
                    ),
                    expected_value=required_header,
                )
            )

    return issues


def validate_required_values(df: pd.DataFrame) -> list[Issue]:
    issues: list[Issue] = []

    for col in REQUIRED_VALUE_COLUMNS:
        if col not in df.columns:
            continue

        for _, row in df.iterrows():
            if is_blank(row.get(col, "")):
                issues.append(
                    Issue(
                        row_number=row.get("Source Row Number"),
                        column=col,
                        severity=SEVERITY_BLOCKER,
                        rule="Missing Required Value",
                        message=f"Required value is blank in '{col}'",
                    )
                )

    return issues