#!/usr/bin/env python3
"""<Ce que fait le hook, et sur quel evenement.>

Entree : un objet JSON sur l'entree standard, decrit dans hooks/README.md du registre.
Sortie : rien, ou un objet JSON sur la sortie standard.

Regles tenues par ce squelette :
  - toute erreur interne sort en 0 sans rien dire, pour ne jamais casser la session ;
  - aucun chemin absolu ;
  - pas de recursion : voir la garde ci-dessous.
"""
from __future__ import annotations

import json
import os
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    # Anti-boucle, pour un hook Stop ou SubagentStop : respecter ce drapeau n'est pas facultatif.
    if payload.get("stop_hook_active"):
        return 0
    # Anti-recursion, si le hook relance Claude : poser une variable de garde et la tester ici.
    if os.environ.get("MON_HOOK_ACTIF"):
        return 0

    try:
        # ... le travail du hook ...
        result = {}
    except Exception:
        return 0          # degradation propre : la session continue

    if result:
        sys.stdout.write(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
