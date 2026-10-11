# Contenu sensible, historique et branches réécrites

## Ce qui est contrôlé avant tout push

Le script lit **tout ce qu'il s'apprête à publier**, historique compris, et bloque (code 5) sur :

| Règle | Détecte |
|-------|---------|
| `local-settings` | `settings.local.json`, `*.local.json`, `*.local.md`, `*.local.yaml` |
| `env-file` | `.env`, `.env.*` (sauf `.env.example` et assimilés) |
| `key-file`, `credentials-file` | `*.pem`, `*.key`, `id_rsa`, `.credentials.json`, `.netrc`… |
| `aws-key`, `github-token`, `slack-token`, `anthropic-key`, `private-key`, `jwt` | secrets au format reconnaissable |
| `personal-path` | répertoire personnel d'un poste (Windows, Linux, macOS) cité dans un fichier |

Chaque constat indique le fichier, la ligne, et s'il se trouve dans le **dernier commit** ou dans
l'**historique publié**. La valeur d'un secret n'est jamais affichée.

Limites : seuls les formats connus sont reconnus ; les fichiers binaires et ceux de plus d'un
mégaoctet ne sont pas lus. Ce contrôle complète une relecture, il ne la remplace pas. Les fichiers
non suivis ne sont jamais publiés : seuls les commits de la branche distante le sont.

## `git subtree split` n'est pas un filtre

Une extraction subtree reproduit l'historique du dossier. Conséquence : retirer un fichier du
dernier commit ne le retire pas de ce qui sera publié, et il n'existe aucun moyen d'« exclure » un
fichier d'une extraction subtree sans réécrire l'historique. Le skill ne réécrit jamais l'historique
de la source.

## Les trois issues d'un constat

1. **Corriger la source.** `git rm --cached <fichier>`, l'ajouter au `.gitignore`, commiter, pousser.
   Suffit pour un constat « dernier commit » quand le fichier vient d'être ajouté ; s'il a déjà été
   commité, le constat revient en « historique publié ».
2. **Publier sans historique** : `strategy=snapshot`, éventuellement avec `exclude=<motif>`.
   Chaque publication crée un commit dont l'arbre est celui du dossier, moins les exclusions ; son
   message porte `Source-Commit:`. L'historique de la source n'est pas publié, donc un fichier
   retiré ou exclu n'y figure pas. Contrepartie : les consommateurs ne voient pas le détail des
   commits de la source. Motifs : `*.local.json` (nom de fichier, à toute profondeur), `tmp/`
   (dossier), `skills/*/notes.md` (chemin).
3. **Accepter en connaissance de cause** : `accept-findings=true` enregistre l'empreinte de chaque
   constat dans la configuration ; il ne rebloque plus, un nouveau constat si. À réserver aux faux
   positifs et aux chemins personnels anodins. Un secret réellement exposé se **révoque** d'abord :
   une fois poussé, il doit être considéré comme connu.

Un secret présent dans l'historique de la branche source reste lisible par quiconque lit le dépôt,
quelle que soit la stratégie d'export : seule sa révocation règle le problème.

## Branche d'export non descendante (code 4)

La publication pousse en avance rapide. Elle refuse quand la branche d'export existante n'est pas un
ancêtre du nouvel export, ce qui arrive quand :

- l'historique du dossier source a été réécrit (`rebase`, `commit --amend`, `push --force`) ;
- quelqu'un a commité directement sur la branche d'export ;
- le nom choisi est celui d'une branche sans rapport.

Rien n'est écrasé par défaut. Après vérification : `force=true` pour cette fois, ou
`allow-force=true` pour l'inscrire dans la configuration. Le push utilise alors
`--force-with-lease` sur le SHA lu, jamais une force aveugle. Côté consommateur, la mise à jour
refusera de suivre une branche réécrite tant que `allow_non_fast_forward` n'y est pas posé.

Passer de `subtree` à `snapshot` ne réécrit rien : le premier instantané se pose par-dessus
l'export existant. L'ancien historique reste donc publié ; pour l'effacer, supprimer la branche
d'export sur le remote avant de republier, puis autoriser la mise à jour chez les consommateurs.
