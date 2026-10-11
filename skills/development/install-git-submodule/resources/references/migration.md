# Dossier cible déjà présent, sous-module déjà installé

## Le dossier cible existe

Un sous-module occupe **tout** son dossier : ce dossier devient la copie de travail d'un autre
dépôt. Un fichier propre au projet ne peut donc plus y être versionné par le dépôt consommateur.
C'est le point qui demande réflexion ; le reste est mécanique.

Le script commence par comparer, fichier par fichier, le dossier présent et le contenu de la branche
à installer :

| Classe | Signification | Ce que fait `migrate=preserve` |
|--------|---------------|-------------------------------|
| identiques | même contenu des deux côtés | rien à perdre ; le sous-module les apporte |
| différents | même chemin, contenu différent | la version de la source s'installe ; la vôtre reste dans la sauvegarde |
| suivis ici, absents de la source | fichiers propres au projet, versionnés | replacés dans le sous-module, **non suivis** ; ils cessent d'être versionnés dans ce dépôt |
| non suivis ici, absents de la source | `settings.local.json`, brouillons, fichiers ignorés | replacés tels quels, non suivis |
| apportés par la source | absents ici | installés |
| modifiés | suivis, modifiés depuis le dernier commit | la version du disque est sauvegardée, avec un correctif `tracked-changes.patch` |

### Quand rien ne demande de choix

Si tous les fichiers présents sont identiques à la source, la migration se fait directement, avec
sauvegarde.

### Quand un choix est nécessaire (code 7)

Dès qu'un fichier diffère ou n'existe que dans le projet, le script s'arrête **sans rien modifier**
et liste chaque fichier. La décision appartient à l'utilisateur :

- **`migrate=preserve`** — appliquer le tableau ci-dessus ;
- **ou d'abord déplacer** les fichiers propres au projet hors du dossier cible (par exemple
  `.claude/project-rules.md` vers `docs/`), commiter, puis relancer ;
- **ou les proposer à la source** à la main, par une pull request dans le dépôt producteur, s'ils
  ont vocation à être partagés. Le skill ne le fait jamais de lui-même : exporter vers la source
  partagée un fichier spécifique à un projet le diffuserait à tous les autres consommateurs.

### Ce que fait exactement la migration

1. Copie intégrale du dossier dans `<dépôt>/.git/submodule-sync-backups/<cible>-<horodatage>/files/`,
   vérifiée par empreinte ; correctif des modifications suivies ; `MANIFEST.json` avec le classement.
2. Retrait du dossier de l'index (`git rm --cached`), puis du disque.
3. `git submodule add -b <branche>`.
4. Remise en place des fichiers propres au projet, non suivis.

Si l'étape 3 échoue, le dossier et l'index sont restaurés depuis la sauvegarde. La sauvegarde n'est
jamais supprimée par le script, et elle n'est jamais commitée : elle vit dans `.git/`. La supprimer
à la main une fois la migration validée.

Les fichiers replacés non suivis apparaissent dans `git status` du sous-module. Ils n'empêchent pas
les mises à jour ; si une version future de la source ajoute un fichier au même chemin, git refuse
de l'écraser et la mise à jour s'arrête en le signalant.

## Le chemin est déjà un sous-module

| Situation | Comportement |
|-----------|--------------|
| même URL, même branche | vérification ; la mise à jour automatique est installée ou rafraîchie ; aucun commit s'il n'y a rien à changer |
| même URL, aucune branche déclarée | la branche demandée est inscrite dans `.gitmodules` |
| branche différente | code 7 ; `set-branch=true` pour changer |
| URL différente | code 7 ; `set-url=true` pour changer |

Changer d'URL ou de branche ne déplace pas la référence : c'est la mise à jour suivante qui le fait.
Si la nouvelle tête n'est pas un descendant du commit actuel, elle refuse ; poser
`allow_non_fast_forward` sur ce sous-module dans `.github/submodule-update.json` le temps de la
bascule.

## Mauvaise branche : `.claude/.claude/`

Installer dans `.claude/` la branche principale d'un dépôt qui contient un dossier `.claude/`
produirait `.claude/.claude/`. Le script le détecte et s'arrête (code 7) : la bonne branche est
presque toujours la branche d'export, `submodule/claude`. `allow-nested=true` passe outre quand
c'est réellement voulu.

## Chemin ignoré

Si un `.gitignore` du dépôt ignore le chemin cible (`vendor/`, par exemple), git refuse d'y ajouter
un sous-module. Corriger la règle, ou `force-ignored=true`.
