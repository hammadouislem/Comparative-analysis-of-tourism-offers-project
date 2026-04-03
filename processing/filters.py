"""
Heuristic filters to drop obvious non-tourism-product rows from merged listings.
"""

import re

# Administrative / visa / paperwork ads that are not trips or stays.
_NOISE_PATTERN = re.compile(
    r"\b("
    r"visa\b|visa\s|passeport|passport|notaire|notary|traduction|translation|"
    r"attestation|l[ée]galisation|legalization|consulat|consulate|"
    r"rdv\b|rendez-vous|dossier\s+consulaire|permis\s+de\s+travail|work\s+permit|"
    r"invitation\s+letter|lettre\s+d['’]?invitation|appointment\s+only"
    r")\b",
    re.IGNORECASE,
)


def is_listing_noise(name: str) -> bool:
    if not name or not str(name).strip():
        return True
    return bool(_NOISE_PATTERN.search(str(name)))
