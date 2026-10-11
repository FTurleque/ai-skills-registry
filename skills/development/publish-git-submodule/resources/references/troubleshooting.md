# Diagnostic et reprise

```bash
python3 .github/submodule-sync/publish.py status        # export contre source, sans rien écrire
python3 .github/submodule-sync/publish.py run --all     # simulation : n'écrit rien sans --push
git ls-remote --heads origin 'submodule/*'              # branches d'export publiées
```

| Symptôme | Cause | Reprise |
|----------|-------|---------|
| Code 2, « n'existe pas dans le commit source » | dossier supprimé ou jamais poussé | pousser le dossier ; l'export existant n'a pas été touché |
| Code 2, « déjà un sous-module » | le dossier est un sous-module du dépôt | installer directement le dépôt qu'il référence |
| Code 2, « ne peut pas coexister » | une branche `submodule` existe, ou `submodule/x/y` | choisir un autre `export` |
| Code 3 | remote injoignable, branche source absente du remote | vérifier `git remote -v`, pousser la branche |
| Code 4 | export non descendant | [security-and-history.md](security-and-history.md) |
| Code 5 | contenu sensible | [security-and-history.md](security-and-history.md) |
| Code 6 | push refusé (protection de la branche d'export, droits) | autoriser l'écriture du workflow sur `submodule/*`, sans toucher aux protections de la branche source |
| `git subtree` absent | git installé sans `contrib/subtree` | installer `git-subtree`, ou `strategy=snapshot` |
| Workflow jamais déclenché | absent de la branche source, ou push sans fichier concerné | vérifier le filtre de chemins, lancer à la main |
| Notification en échec, HTTP 404 ou 403 | jeton sans accès au consommateur | corriger `SUBMODULE_DISPATCH_TOKEN` ([automation.md](automation.md)) |

## Reprendre après une interruption

Relancer la même commande. Tout est rejouable : la configuration est fusionnée par nom de
publication, l'extraction est déterministe, un export déjà à jour ne produit ni commit ni push.

## Modifier une publication

Relancer le skill avec le même `source` et les paramètres à changer. Changer `export` crée une
nouvelle branche ; l'ancienne reste en place, à supprimer à la main une fois les consommateurs
migrés (`git push origin --delete <ancienne>`).

## Désactiver

- Une publication : `"auto": false` dans `.github/submodule-publish.json`, puis relancer le skill.
- Tout : supprimer `.github/workflows/submodule-publish.yml`.
- Retirer complètement : supprimer aussi `.github/submodule-publish.json` et, si le dépôt n'est pas
  consommateur, `.github/submodule-sync/`.

Les branches d'export déjà publiées restent utilisables : les consommateurs gardent leur référence.
