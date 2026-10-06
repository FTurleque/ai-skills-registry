"""Modele de donnees partage par tous les analyseurs."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional

CRITICAL = "CRITICAL"
MAJOR = "MAJOR"
MINOR = "MINOR"

SEVERITY_ORDER = {CRITICAL: 0, MAJOR: 1, MINOR: 2}

# Categories exposees a l'agent implementeur.
CAT_SECURITY = "securite"
CAT_BUG = "bug"
CAT_DUPLICATION = "duplication"
CAT_COMPLEXITY = "complexite"
CAT_NAMING = "nommage"
CAT_CONVENTION = "convention"


@dataclass
class Finding:
    rule: str                      # identifiant stable de la regle, ex: SEC.SQL_CONCAT
    category: str                  # CAT_*
    severity: str                  # CRITICAL / MAJOR / MINOR
    message: str                   # ce qui est faux, en une phrase
    fix: str                       # ce que l'agent doit faire
    file: str                      # chemin relatif au depot
    line: int = 0                  # 1-indexe, 0 = pas de ligne precise
    end_line: int = 0
    symbol: Optional[str] = None   # methode / classe concernee
    evidence: str = ""             # extrait de code
    source: str = "static"         # static | llm
    extra: dict = field(default_factory=dict)

    def key(self) -> str:
        """Empreinte stable, utilisee pour la deduplication et l'anti-boucle."""
        raw = "%s|%s|%s|%s" % (self.rule, self.file, self.symbol or "", self.evidence[:120])
        return hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()[:12]

    def location(self) -> str:
        if self.line and self.end_line and self.end_line != self.line:
            return "%s:%d-%d" % (self.file, self.line, self.end_line)
        if self.line:
            return "%s:%d" % (self.file, self.line)
        return self.file

    def to_dict(self) -> dict:
        d = asdict(self)
        d["key"] = self.key()
        d["location"] = self.location()
        return d


def sort_findings(findings):
    return sorted(
        findings,
        key=lambda f: (SEVERITY_ORDER.get(f.severity, 3), f.category, f.file, f.line),
    )


def dedupe(findings):
    seen = {}
    for f in findings:
        k = f.key()
        prev = seen.get(k)
        if prev is None or SEVERITY_ORDER.get(f.severity, 3) < SEVERITY_ORDER.get(prev.severity, 3):
            seen[k] = f
    return list(seen.values())
