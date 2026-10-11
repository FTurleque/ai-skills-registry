# Surfaces Claude et compatibilité

Ce document décrit les surfaces sur lesquelles un artefact du registre peut fonctionner, et la
matrice de compatibilité du dépôt.

---

## Principe

Chaque artefact déclare ses surfaces dans le champ `compatibility` de ses métadonnées. La valeur est
une liste, et chaque entrée est l'une des quatre surfaces ci-dessous. Toute autre valeur est une
erreur de validation.

```yaml
compatibility:
  - claude-code
  - claude-desktop
```

Le registre ne cible que Claude. Les autres assistants ne sont pas une dimension de ce dépôt : ce
qui est portable au-delà de Claude le reste par nature, mais ce n'est ni déclaré, ni testé, ni
documenté ici.

---

## Les quatre surfaces

| Identifiant | Surface | Ce qu'elle sait charger |
|-------------|---------|-------------------------|
| `claude-code` | Claude Code, en terminal ou dans l'onglet Code de l'application | tout : skills, plugins, hooks, sous-agents, commandes, MCP, styles de sortie |
| `claude-desktop` | L'application de bureau, mode Cowork | skills, plugins, sous-agents, commandes, MCP |
| `claude-ai` | claude.ai, dans le navigateur ou sur mobile | skills, MCP |
| `claude-api` | API et Agent SDK | skills, sous-agents, outils que vous câblez vous-même |

### `claude-code`

La surface la plus complète, et la seule qui exécute des hooks. Un artefact qui repose sur un
événement de session ne peut déclarer qu'elle, et éventuellement `claude-desktop`.

### `claude-desktop`

Partage l'essentiel des mécanismes de Claude Code. Les différences portent sur l'exécution locale :
un artefact qui suppose un terminal, un `git` disponible ou un accès à un port local doit le dire
dans son `requires` plutôt que de l'exclure d'emblée.

### `claude-ai`

Pas d'exécution de code côté utilisateur, pas de hooks. Une skill y fonctionne si son contenu est
du raisonnement et de la méthode. Une skill qui appelle un script dans `resources/` n'y fonctionne
pas : elle ne doit pas déclarer cette surface.

### `claude-api`

Les skills s'y chargent, les sous-agents aussi, mais tout le reste est à câbler par l'appelant. Un
artefact déclare cette surface quand il ne suppose rien de l'environnement d'exécution.

---

## Matrice de compatibilité

| Artefact | Type | `claude-code` | `claude-desktop` | `claude-ai` | `claude-api` |
|----------|------|:-------------:|:----------------:|:-----------:|:------------:|
| `java-code-review` | skill | ✅ | ✅ | ✅ | ✅ |
| `generate-windows-exe` | skill | ✅ | ✅ | ❌ | ❌ |
| `code-to-openspec` | skill | ✅ | ✅ | ❌ | ❌ |
| `audit-application` | skill | ✅ | ✅ | ❌ | ❌ |
| `adr-audit` | skill | ✅ | ⬜ | ❌ | ❌ |
| `adr-author` | skill | ✅ | ⬜ | ❌ | ❌ |
| `adr-check` | skill | ✅ | ⬜ | ❌ | ❌ |
| `adr-policy` | skill | ✅ | ⬜ | ❌ | ❌ |
| `publish-git-submodule` | skill | ✅ | ⬜ | ❌ | ❌ |
| `install-git-submodule` | skill | ✅ | ⬜ | ❌ | ❌ |
| `git-submodule-common` | skill | ✅ | ⬜ | ❌ | ❌ |
| `code-supervisor` | plugin | ✅ | ✅ | ❌ | ❌ |

**Légende**

- ✅ déclaré compatible et vérifié sur au moins un cas d'usage réel
- ⬜ plausible mais non vérifié — à ne pas déclarer dans `compatibility`
- ❌ hors de portée par conception, et non un défaut à corriger

Un `❌` n'est pas une lacune. `generate-windows-exe` lance un script PowerShell : il n'a rien à
faire sur claude.ai. `code-supervisor` repose sur des hooks : il n'existe que là où il y a des
hooks.

---

## Vérifier et déclarer

1. Exercer l'artefact sur la surface visée, sur un cas d'usage représentatif.
2. Renseigner `compatibility` dans les métadonnées — et dans le front matter du `SKILL.md` s'il y en
   a un, avec exactement les mêmes valeurs.
3. Ajouter ou mettre à jour la ligne de la matrice ci-dessus.
4. Documenter dans le `README.md` de l'artefact les limitations propres à une surface.

Le validateur avertit quand un artefact est absent de cette matrice. Il ne peut pas vérifier que les
coches sont vraies : c'est à l'auteur de ne cocher que ce qu'il a essayé.
