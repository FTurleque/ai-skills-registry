# Compatibilité entre outils IA

Ce document décrit la matrice de compatibilité initiale du dépôt **AI Skills Registry** et explique comment documenter la compatibilité pour chaque skill.

---

## Principe

Chaque skill déclare les outils IA avec lesquels il est compatible dans son front matter YAML, via le champ `compatibility`.

Exemple :

```yaml
compatibility:
  - generic
  - github-copilot
  - claude-code
```

---

## Identifiants de compatibilité

| Identifiant      | Outil ciblé              |
|------------------|--------------------------|
| `generic`        | Tout assistant compatible |
| `github-copilot` | GitHub Copilot            |
| `claude-code`    | Claude Code               |
| `chatgpt`        | ChatGPT                   |
| `opencode`       | OpenCode                  |

---

## Matrice de compatibilité initiale

| Skill                           | generic | github-copilot | claude-code | chatgpt | opencode |
|---------------------------------|:-------:|:--------------:|:-----------:|:-------:|:--------:|
| `java-code-review`              | ✅      | ✅             | ✅          | ⬜      | ⬜       |

**Légende :**
- ✅ Testé et confirmé compatible
- ⬜ Non testé ou non vérifié
- ❌ Incompatible ou non supporté

---

## Niveaux de compatibilité

### `generic`

Un skill marqué `generic` doit fonctionner avec n'importe quel assistant IA capable de comprendre des instructions en langage naturel en Markdown. Il ne doit pas dépendre de fonctionnalités propres à un outil.

### `github-copilot`

GitHub Copilot peut utiliser des skills sous forme de fichiers d'instructions personnalisées. Les skills compatibles doivent respecter les limites de contexte et le format attendu par l'outil.

### `claude-code`

Claude Code supporte les instructions structurées en Markdown. Les skills doivent être clairs, explicites et ne pas supposer de mémoire persistante entre les sessions.

### `chatgpt`

ChatGPT peut utiliser des skills comme base de prompts systèmes ou d'instructions personnalisées. La compatibilité dépend de la version utilisée (GPT-4, GPT-4o, etc.).

### `opencode`

OpenCode est un outil de développement IA en ligne de commande. Les skills compatibles doivent être adaptés à une utilisation dans un contexte de terminal et de fichiers de code.

---

## Vérifier et documenter la compatibilité

1. Tester le skill avec l'outil ciblé sur un ou plusieurs cas d'usage représentatifs
2. Mettre à jour le champ `compatibility` dans le front matter de `SKILL.md` et dans `metadata.yaml`
3. Mettre à jour la matrice ci-dessus
4. Documenter les éventuelles limitations ou adaptations nécessaires dans le `README.md` du skill
5. Indiquer la version de l'outil utilisée lors du test si elle est pertinente

---

## Ajouter un nouvel outil

Pour ajouter la compatibilité avec un nouvel outil IA :

1. Définir un identifiant en kebab-case (ex. `gemini`, `mistral-ai`)
2. Ajouter une ligne dans la matrice ci-dessus
3. Ajouter une colonne dans les tableaux de métadonnées des skills concernés
4. Créer un dossier dans `skills/<identifiant>/` si des skills spécifiques sont nécessaires
5. Documenter les particularités de l'outil dans cette section
