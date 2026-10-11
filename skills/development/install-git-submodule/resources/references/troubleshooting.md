# Diagnostic, retour arrière et désactivation

```bash
python3 .github/submodule-sync/update.py status   # référence enregistrée contre tête de branche
python3 .github/submodule-sync/update.py run      # mise à jour locale, sans push
git submodule status                              # état des sous-modules du clone
git log -3 --format=%B -- <chemin>                # SHA ancien, nouveau et source des mises à jour
```

Chaque commit de mise à jour porte `Submodule-Old`, `Submodule-New` et, quand il vient d'un événement
du producteur, `Source-Commit` : de quoi remonter du commit installé au commit source. Le résumé de
chaque exécution du workflow reprend ces SHA.

| Symptôme | Cause | Reprise |
|----------|-------|---------|
| Code 3 à l'installation | dépôt source illisible, ou branche absente | vérifier l'accès ; publier la branche d'export avec `/publish-git-submodule` |
| Code 3 dans le workflow | dépôt source privé sans `SUBMODULE_FETCH_TOKEN` | [permissions.md](permissions.md) |
| Code 4 | la branche suivie a été réécrite, ou la référence a été épinglée hors de la branche | vérifier côté source ; `allow_non_fast_forward` le temps de la bascule |
| Code 6, « protected branch » | push direct interdit | `mode=pr` ([permissions.md](permissions.md)) |
| Code 6, conflit après rebase | une autre mise à jour a changé la même référence | relancer : l'exécution repart de l'état distant |
| Code 7 dans `update.py` | fichier suivi modifié, ou commit local, dans le sous-module | commiter ou annuler ce travail local ; rien n'a été écrasé |
| « contrôle échoué » | un `check` du dépôt refuse la nouvelle version | corriger la source ou le contrôle ; la référence n'a pas bougé |
| « événement ignoré » | la source ou la branche de l'événement ne correspond à aucun sous-module géré | vérifier l'URL de `.gitmodules` et l'inscription côté producteur |
| Workflow jamais déclenché | fichier absent de la branche par défaut | fusionner le commit d'installation dans la branche par défaut |
| Planification muette | retard de GitHub, ou désactivation après soixante jours d'inactivité | lancer à la main ; réactiver le workflow |
| `.claude/` vide après un clone | sous-modules non initialisés | `git submodule update --init --recursive` |

## Revenir à un ancien commit

Sans précaution, la prochaine exécution refuserait de « reculer » ou ré-avancerait la référence.
Geler d'abord, déplacer ensuite :

1. Dans `.github/submodule-update.json`, poser `"hold": true` sur le sous-module.
2. `git -C <chemin> checkout <sha>` puis `git add <chemin> .github/submodule-update.json`.
3. Commiter et pousser.

Pour reprendre les mises à jour : retirer `hold`. Si l'ancien commit n'est pas un ancêtre de la tête
de branche, poser aussi `allow_non_fast_forward` le temps de revenir sur la branche.

Annuler seulement la dernière mise à jour : `git revert <commit de mise à jour>`, avec `hold` pour
qu'elle ne soit pas refaite à l'exécution suivante.

## Désactiver

- **Un sous-module** : `"hold": true`, ou le retirer de la liste `submodules`.
- **La planification** : relancer le skill avec `schedule=none`.
- **Tout** : supprimer `.github/workflows/submodule-update.yml`. Le sous-module reste installé et se
  met à jour à la main : `git submodule update --remote <chemin>`.
- **Se désinscrire de l'événement**, dans le dépôt source :
  `/publish-git-submodule unregister name=<publication> consumer=<ce dépôt>`.

## Retirer le sous-module

```bash
git submodule deinit -f -- <chemin>
```

```bash
git rm -f -- <chemin>
```

Puis retirer son entrée de `.github/submodule-update.json`, commiter, et supprimer à la main
`.git/modules/<nom>` si le sous-module ne doit pas être réinstallé.

## Reprendre après une interruption

Relancer la même commande du skill. Une installation déjà faite est vérifiée, pas refaite. Une
migration interrompue a restauré le dossier depuis sa sauvegarde ; celle-ci reste dans
`.git/submodule-sync-backups/` dans tous les cas.
