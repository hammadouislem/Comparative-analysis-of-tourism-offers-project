import math
import os
import re
from typing import Optional, Union


def ensure_directory(path: str) -> None:
    """Create directory if it does not exist."""
    os.makedirs(path, exist_ok=True)


def clean_text(value: Optional[Union[str, int, float]]) -> str:
    """Normalize white spaces and return a safe string."""
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    if not isinstance(value, str):
        value = str(value)
    if not value or value.lower() == "nan":
        return ""
    return re.sub(r"\s+", " ", value).strip()


def parse_price(value: Optional[Union[str, int, float]]) -> Optional[float]:
    """
    Parse price-like strings into float.
    Examples:
      '12 500 DA' -> 12500.0
      '1.250,50' -> 1250.50
    """
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = clean_text(value).lower()
    if any(marker in text for marker in ["à débattre", "negociable", "négociable", "sur demande"]):
        return None

    text = text.replace("da", "").replace("dzd", "")
    text = text.replace("\u202f", " ").replace("\xa0", " ")
    text = text.replace(" ", "")
    text = text.replace(",", ".")

    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def parse_duration_to_days(value: Optional[Union[str, int, float]]) -> Optional[float]:
    """
    Parse duration text and normalize to days.
    Handles:
      - '7 jours' -> 7
      - '1 semaine' -> 7
      - '2 semaines' -> 14
      - '3 nuits / 4 jours' -> 4
      - '48h' -> 2
    """
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (int, float)):
        days = float(value)
        return days if days > 0 else None

    text = clean_text(value).lower()

    day_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(jour|jours|j)\b", text)
    if day_match:
        return float(day_match.group(1).replace(",", "."))

    week_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(semaine|semaines|sem)\b", text)
    if week_match:
        return float(week_match.group(1).replace(",", ".")) * 7.0

    night_day_match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*nuits?\s*[/\-]\s*(\d+(?:[.,]\d+)?)\s*jours?",
        text,
    )
    if night_day_match:
        return float(night_day_match.group(2).replace(",", "."))

    hour_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(h|heure|heures)\b", text)
    if hour_match:
        return float(hour_match.group(1).replace(",", ".")) / 24.0

    # Generic fallback: first number in text assumed to be days.
    generic = re.search(r"(\d+(?:[.,]\d+)?)", text)
    if generic:
        return float(generic.group(1).replace(",", "."))

    return None
