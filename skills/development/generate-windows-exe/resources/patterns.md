# Patterns d'empaquetage en executable

Recueil de patterns eprouves sur des projets reels. Les recettes A (Inno Setup)
et B (jpackage) sont pilotees et verifiees depuis le `SKILL.md`. Les patterns
ci-dessous sont documentes comme references d'architecture.

---

## 1. Distribution auto-portee (Node) — pattern `mcp-search-net`

Une app Node/TypeScript n'a pas de `.exe` natif : on **embarque le runtime Node**
puis on empaquete le tout avec Inno Setup (recette A). Le pipeline reel enchaine
trois etapes :

1. **Assembler la distribution** (`build-windows-distribution.ps1`) :
   - `npm ci` + `npm run build` (compilation TypeScript vers `build/`)
   - copie de `build/`, `migrations/`, `config/`, `package.json`
   - `npm ci --omit=dev` dans le dossier app (dependances de prod seulement)
   - extraction du runtime `node-v<version>-win-x64.zip` dans `runtime/`
   - `BUILD-MANIFEST.json` + `THIRD-PARTY-NOTICES.txt`
2. **Compiler l'installateur** (`build-windows-installer.ps1` -> recette A).
3. **Publier** (`publish-windows-release.ps1`) : ZIP + `.exe` + SHA-256 sur la Release.

Le point cle : l'installateur ne contient pas que le code, mais **code + runtime +
config**, si bien que l'utilisateur final n'installe ni Node ni dependances.

Points d'integration a retenir du modele `.iss` d'origine :
- `[Tasks]` pour ajouter `bin\` au `PATH` utilisateur (case a cocher).
- `[Registry]` (HKCU) pour exposer un `HOME` de l'app et permettre un
  desinstalleur propre.
- Section `[Code]` Pascal : pages d'assistant personnalisees, detection de
  clients, hook post-install (`CurStepChanged` -> `ssPostInstall`).

---

## 2. Fat-jar + lanceur — pattern `nexus-context-engine` (Java)

Pour une app Java, l'approche la plus simple est un **fat-jar** (toutes les
dependances dans un seul JAR) lance par un script `.cmd` :

- `maven-shade-plugin` produit `nexus-context-engine-<version>-cli.jar`
  (JAR autonome, ~25 Mo, avec `Main-Class`).
- Un lanceur `nexus.cmd` resout le JAR et appelle `java -jar "<jar>" %*`.
- `maven-assembly-plugin` empaquette `lib/*.jar` + `bin/*.cmd` + `README` en ZIP.

Ce n'est pas un `.exe`, mais un lanceur portable. Pour transformer le lanceur en
vrai `.exe`, deux options :

- **jpackage** (recette B) : JDK 17+, produit un lanceur `.exe` embarquant un
  runtime Java reduit (via `jlink`). Aucun JRE requis chez l'utilisateur.
- **Launch4j** : enveloppe un JAR dans un `.exe` fin (le JRE reste requis, sauf
  si bundle). Utile pour un simple double-clic.

---

## 3. Executable natif (GraalVM `native-image`)

Pour un binaire natif sans JVM (demarrage instantane, un seul `.exe`) :

```
native-image -jar app.jar app
```

`nexus-context-engine` est base sur **Quarkus** (`quarkus-maven-plugin` present),
qui pilote `native-image` via :

```
mvn package -Dnative -Dquarkus.native.container-build=false
```

Contraintes : necessite GraalVM + Visual Studio Build Tools (compilateur C sous
Windows) ; la reflexion doit etre declaree (config Quarkus). Le resultat est un
`.exe` autonome de plusieurs dizaines de Mo.

---

## 4. Node Single Executable Application (SEA) / `pkg`

Pour transformer un script Node en `.exe` sans installateur :

- **SEA** (Node 20+, natif) : `node --experimental-sea-config sea-config.json`
  puis injection du blob dans une copie de `node.exe` via `postject`.
- **`@yao-pkg/pkg`** (fork maintenu de `vercel/pkg`) : `pkg app.js --targets node22-win-x64`
  produit directement `app.exe`.

Choix pratique : SEA pour rester sur l'outillage officiel ; `pkg` pour la
simplicite. Dans les deux cas, les modules natifs (`.node`) doivent etre copies a
cote du `.exe`.

---

## Aide-memoire du choix

| Vous voulez... | Recette |
|----------------|---------|
| Un installateur avec assistant + PATH + desinstalleur | A (Inno Setup) |
| Un dossier app + lanceur `.exe` (Java, sans JRE) | B (jpackage) |
| Un simple lanceur portable Java | Fat-jar + `.cmd` |
| Un binaire natif sans JVM | GraalVM `native-image` |
| Un `.exe` unique depuis un script Node | Node SEA ou `pkg` |
