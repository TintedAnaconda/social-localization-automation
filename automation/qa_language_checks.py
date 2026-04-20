from __future__ import annotations

import re

import pandas as pd

from qa_config import SEVERITY_WARNING
from qa_models import Issue
from qa_utils import clean_filename_for_language_check, contains_url, normalize_text

try:
    import language_tool_python
except ImportError:  # pragma: no cover
    language_tool_python = None


def build_language_tool():
    if language_tool_python is None:
        return None
    return language_tool_python.LanguageTool("en-US")


def should_skip_text_check(text: str) -> bool:
    text = normalize_text(text)
    if not text:
        return True
    if len(text) < 3:
        return True
    if contains_url(text):
        return True
    return False


def get_match_rule_id(match) -> str:
    """
    Safely get a rule id across different language_tool_python versions.
    """
    # Some versions expose ruleId directly
    rule_id = getattr(match, "ruleId", None)
    if rule_id:
        return str(rule_id)

    # Some versions may expose rule as an object or dict
    rule = getattr(match, "rule", None)
    if rule is not None:
        rule_id = getattr(rule, "id", None)
        if rule_id:
            return str(rule_id)

        if isinstance(rule, dict):
            return str(rule.get("id", ""))

    return ""


def get_match_message(match) -> str:
    """
    Safely get message text across versions.
    """
    return getattr(match, "message", "Possible spelling or grammar issue")


def get_match_context(match, fallback_text: str) -> str:
    """
    Safely get context text across versions.
    """
    context = getattr(match, "context", None)
    if context:
        return str(context)
    return fallback_text


def get_match_replacements(match) -> list[str]:
    """
    Safely get suggested replacements across versions.
    """
    replacements = getattr(match, "replacements", None)
    if replacements is None:
        return []

    # Usually already a list[str]
    if isinstance(replacements, list):
        return [str(r) for r in replacements]

    return []


def filter_language_tool_matches(matches, text: str, column: str):
    filtered = []

    for match in matches:
        rule_id = get_match_rule_id(match)
        context = get_match_context(match, text)

        # Reduce noise for filename-derived text
        if column == "IMAGE-NAME":
            if rule_id == "MORFOLOGIK_RULE_EN_US":
                continue

        # Ignore likely asset tokens / acronyms / IDs
        if re.search(r"\b[A-Z0-9_/\-]{2,}\b", context):
            continue

        filtered.append(match)

    return filtered


def validate_language_quality(df: pd.DataFrame, tool=None) -> list[Issue]:
    issues: list[Issue] = []

    if tool is None:
        return issues

    text_columns = ["Message", "Image or Video copy", "Alt-Text"]

    for _, row in df.iterrows():
        row_number = row.get("Source Row Number")

        for col in text_columns:
            if col not in df.columns:
                continue

            text = normalize_text(row.get(col, ""))
            if should_skip_text_check(text):
                continue

            matches = tool.check(text)
            matches = filter_language_tool_matches(matches, text, col)
            matches = matches[:2]

            for match in matches:
                suggestions = get_match_replacements(match)[:3]
                suggestion_text = ", ".join(suggestions) if suggestions else None

                issues.append(
                    Issue(
                        row_number=row_number,
                        column=col,
                        severity=SEVERITY_WARNING,
                        rule="Spell/Grammar Check",
                        message=get_match_message(match),
                        actual_value=text[:200],
                        expected_value=suggestion_text,
                    )
                )

        if "IMAGE-NAME" in df.columns:
            image_name = normalize_text(row.get("IMAGE-NAME", ""))
            cleaned_text = clean_filename_for_language_check(image_name)

            if should_skip_text_check(cleaned_text):
                continue

            matches = tool.check(cleaned_text)
            matches = filter_language_tool_matches(matches, cleaned_text, "IMAGE-NAME")
            matches = matches[:1]

            for match in matches:
                suggestions = get_match_replacements(match)[:3]
                suggestion_text = ", ".join(suggestions) if suggestions else None

                issues.append(
                    Issue(
                        row_number=row_number,
                        column="IMAGE-NAME",
                        severity=SEVERITY_WARNING,
                        rule="Filename Spell Check",
                        message=f"Possible spelling issue in IMAGE-NAME-derived text: {get_match_message(match)}",
                        actual_value=cleaned_text[:200],
                        expected_value=suggestion_text,
                    )
                )

    return issues