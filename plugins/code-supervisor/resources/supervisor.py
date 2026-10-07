#!/usr/bin/env python3
"""Superviseur de code — hook Stop / SubagentStop de Claude Code.

Se declenche quand un agent a fini d'implementer. Relit uniquement ce qui a change,
croise une analyse statique portable et une relecture par modele, puis renvoie
l'agent corriger si un probleme bloquant est trouve.

Usages :
  echo '<payload>' | python3 supervisor.py          # mode hook (stdin JSON)
  python3 supervisor.py --check [chemins...]        # relecture manuelle, sortie lisible
  python3 supervisor.py --self-test                 # verifie le moteur sur les fixtures

Ce fichier n'est que le point d'entree : la logique vit dans supervisor/runner.py.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main(args) -> int:
    # Les modules du moteur s'importent entre eux par leur nom court : leur dossier doit etre
    # sur le chemin d'import avant le premier import, d'ou l'import ici et non en tete de fichier.
    sys.path.insert(0, os.path.join(HERE, "supervisor"))
    import runner
    return runner.main(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
