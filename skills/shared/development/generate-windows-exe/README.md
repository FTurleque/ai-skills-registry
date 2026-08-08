# Generate Windows Executable

> Empaquette une application en executable Windows (`.exe`) via Inno Setup ou
> jpackage, avec un driver reproductible et verifie de bout en bout.

---

## Presentation

Ce skill guide un assistant IA pour produire un **`.exe` Windows** a partir d'une
application. Il fournit deux recettes eprouvees sur des projets reels :

- **Recette A — Installateur** : un driver PowerShell
  ([`resources/build-exe.ps1`](resources/build-exe.ps1)) transforme n'importe
  quel dossier en installateur `app-setup.exe` (avec assistant et desinstalleur)
  via Inno Setup. Pattern distille du pipeline de release de `mcp-search-net`.
- **Recette B — Lanceur natif** : `jpackage` (fourni avec le JDK) produit un
  lanceur `.exe` autonome pour une application Java. Pattern issu de
  `nexus-context-engine`.

Contrairement a une simple documentation, le skill embarque un **driver
executable** : il ne decrit pas comment faire, il le fait.

## Prerequis

- **Windows** (les binaires produits sont Windows ; `ISCC.exe` et `jpackage`
  ciblent Windows).
- **Inno Setup** pour la recette A : `winget install --id JRSoftware.InnoSetup`.
- **JDK 17+** pour la recette B (fournit `jpackage`).
- Un **payload** : le dossier a empaqueter (build compile + fichiers associes).

## Utilisation

1. Preparer le dossier payload (build de l'app + runtime/config si necessaire).
2. Recette A — generer l'installateur :
   ```powershell
   ./resources/build-exe.ps1 -PayloadDir ./payload -AppName mon-app -Version 1.0.0 -OutputDir ./dist
   ```
3. Recette B — generer un lanceur Java :
   ```powershell
   jpackage --type app-image --name mon-app --input ./input --main-jar app.jar --main-class Main --win-console --dest ./out
   ```
4. Verifier le `.exe` (magic `MZ`, metadonnees, SHA-256) et prouver son
   fonctionnement (installation silencieuse ou execution du lanceur).

Voir [`SKILL.md`](SKILL.md) pour les instructions detaillees et les gotchas.

## Exemple de prompt

```
Empaquette le dossier build/ de mon app en installateur Windows .exe,
nom "mon-app", version 1.2.0, en utilisant le skill generate-windows-exe.
```

## Contenu

| Fichier | Role |
|---------|------|
| `SKILL.md` | Instructions completes, gotchas, troubleshooting |
| `resources/build-exe.ps1` | Driver : dossier payload -> installateur `.exe` |
| `resources/installer.iss.template` | Modele Inno Setup (jetons `@@...@@`) |
| `resources/patterns.md` | Alternatives (fat-jar, GraalVM native-image, Node SEA/pkg) |
| `examples/example.md` | Execution complete avec sorties reelles |

## Compatibilite

| Outil            | Statut |
|------------------|--------|
| generic          | ✅     |
| GitHub Copilot   | ✅     |
| Claude Code      | ✅     |
| ChatGPT          | ⬜     |
| OpenCode         | ⬜     |

## Metadonnees

Voir `metadata.yaml` pour les metadonnees completes.

## Licence

MIT — Fabrice Turleque
