"""Mise en forme des verdicts : message bloquant pour l'agent, avertissement, journal."""
from __future__ import annotations

import datetime
from typing import List

from model import CRITICAL, LLM_NOTE_PREFIX, MAJOR, MINOR, CAT_SECURITY, Finding, sort_findings

CATEGORY_LABEL = {
    "securite": "Securite",
    "bug": "Bug",
    "duplication": "Duplication",
    "complexite": "Complexite",
    "nommage": "Nommage",
    "convention": "Conventions",
}


def static_only(verdict: str) -> bool:
    """Vrai quand la revue par modele n'a pas eu lieu : seul le verdict de l'analyse statique existe."""
    return bool(verdict) and verdict.startswith(LLM_NOTE_PREFIX)


def _render(findings: List[Finding], limit: int) -> str:
    lines = []
    for f in sort_findings(findings)[:limit]:
        head = "- **%s / %s** — %s" % (f.severity, CATEGORY_LABEL.get(f.category, f.category), f.location())
        if f.symbol:
            head += " (`%s`)" % f.symbol
        lines.append(head)
        lines.append("  - Probleme : %s" % f.message)
        lines.append("  - A faire : %s" % f.fix)
        if f.evidence:
            lines.append("  - Code : `%s`" % f.evidence.replace("`", "'")[:180])
    extra = len(findings) - limit
    if extra > 0:
        lines.append("- ... et %d autre(s) point(s), detail dans le rapport complet." % extra)
    return "\n".join(lines)


def block_message(blockers: List[Finding], others: List[Finding], verdict: str, report_path: str, limit: int) -> str:
    out = [
        "SUPERVISEUR DE CODE — correction requise avant de rendre la main.",
        "",
        "%d probleme(s) bloquant(s) detecte(s) dans les fichiers que tu viens de modifier." % len(blockers),
        "",
        "## A corriger maintenant",
        _render(blockers, limit),
    ]
    if others:
        out += ["", "## Signale sans blocage (a traiter si c'est dans le perimetre de ta tache)",
                _render(others, max(6, limit // 2))]
    if verdict:
        out += ["", "Synthese du relecteur : %s" % verdict]
    out += [
        "",
        "## Comment proceder",
        "1. Corrige chaque point bloquant ci-dessus, dans les fichiers indiques.",
        "2. Ne touche pas au code hors du perimetre de ta tache et de ces corrections.",
        "3. Si un point est un faux positif, ne le contourne pas : explique en une ligne pourquoi le code est correct, puis continue.",
        "4. N'ajoute ni suppression d'avertissement (NOSONAR, @SuppressWarnings, # noqa) ni desactivation de test pour faire taire un controle.",
        "",
        "Rapport complet : %s" % report_path,
    ]
    return "\n".join(out)


def warn_message(findings: List[Finding], verdict: str, report_path: str, limit: int) -> str:
    headline = ("SUPERVISEUR DE CODE — analyse statique seule, aucun probleme bloquant. "
                if static_only(verdict) else "SUPERVISEUR DE CODE — aucun probleme bloquant. ")
    out = [
        headline + "%d point(s) de qualite releve(s) :" % len(findings),
        "",
        _render(findings, limit),
    ]
    if verdict:
        out += ["", "Synthese du relecteur : %s" % verdict]
    out += ["", "Rapport complet : %s" % report_path]
    return "\n".join(out)


def user_summary(counts: dict, blocked: bool, nb_files: int, verdict: str = "") -> str:
    parts = []
    for sev in (CRITICAL, MAJOR, MINOR):
        if counts.get(sev):
            parts.append("%d %s" % (counts[sev], sev.lower()))
    detail = ", ".join(parts) if parts else "rien a signaler"
    state = "agent renvoye en correction" if blocked else "pas de blocage"
    if static_only(verdict):
        state += ", analyse statique seule : %s" % verdict[:240]
    return "Superviseur de code : %d fichier(s) relu(s), %s — %s." % (nb_files, detail, state)


def full_report(findings: List[Finding], files, counts: dict, verdict: str,
                blocked: bool, session_id: str, round_no: int) -> str:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Rapport du superviseur de code",
        "",
        "- Date : %s" % now,
        "- Session : %s (passe %d)" % (session_id, round_no),
        "- Fichiers relus : %d" % len(files),
        "- Verdict : %s%s" % ("BLOQUANT" if blocked else "non bloquant",
                            " (analyse statique seule)" if static_only(verdict) else ""),
        "- Comptage : %d CRITICAL, %d MAJOR, %d MINOR" % (
            counts.get(CRITICAL, 0), counts.get(MAJOR, 0), counts.get(MINOR, 0)),
        "",
    ]
    if verdict:
        lines += ["> %s" % verdict, ""]
    lines += ["## Fichiers", ""]
    for sf in files:
        lines.append("- `%s`%s" % (sf.path, " (nouveau)" if sf.is_new else ""))
    lines += ["", "## Constats", ""]
    by_cat = {}
    for f in sort_findings(findings):
        by_cat.setdefault(f.category, []).append(f)
    for cat, items in by_cat.items():
        lines += ["### %s (%d)" % (CATEGORY_LABEL.get(cat, cat), len(items)), "", _render(items, 200), ""]
    if not findings:
        lines.append("Aucun constat.")
    return "\n".join(lines)
