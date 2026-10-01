---
kind: skill
name: java-code-review
displayName: Java Code Review
description: Analyse du code Java afin d'identifier les défauts, risques et améliorations possibles.
version: 1.1.0
status: stable
category: development
tags:
  - java
  - code-review
  - quality
compatibility:
  - claude-code
  - claude-desktop
  - claude-ai
  - claude-api
authors:
  - Fabrice Turleque
license: MIT
---

# Objectif

Effectuer une revue de code structurée et exhaustive d'un fichier ou d'un ensemble de fichiers Java, en identifiant les défauts, les risques et les axes d'amélioration possibles.

# Cas d'utilisation

- Revue d'une pull request contenant du code Java
- Audit qualité d'une classe ou d'un module existant
- Préparation à un refactoring
- Vérification de conformité aux bonnes pratiques Java
- Détection de risques de sécurité ou de performance avant mise en production

# Entrées attendues

- **Code Java** : le ou les fichiers Java à analyser (contenu complet ou extraits significatifs)
- **Version Java** : la version Java cible du projet (ex. Java 11, Java 17, Java 21) — si connue
- **Contexte** : description optionnelle du rôle de la classe dans l'application

# Instructions

Analyser le code Java fourni selon les critères suivants :

## Lisibilité

- Les noms de classes, méthodes et variables sont-ils clairs et expressifs ?
- Le code est-il suffisamment documenté (Javadoc sur les API publiques) ?
- Les méthodes sont-elles de taille raisonnable (principe de responsabilité unique) ?

## Responsabilités

- Chaque classe a-t-elle une seule responsabilité bien définie ?
- Les méthodes font-elles une seule chose ?
- Y a-t-il des dépendances injustifiées entre classes ?

## Duplication

- Y a-t-il du code dupliqué à extraire dans une méthode ou une classe utilitaire ?
- Des patterns répétitifs peuvent-ils être factorisés ?

## Complexité

- Y a-t-il des méthodes avec une complexité cyclomatique élevée ?
- Des conditions imbriquées peuvent-elles être simplifiées (clause de garde, pattern matching, etc.) ?

## Gestion des exceptions

- Les exceptions sont-elles correctement capturées et traitées ?
- Les exceptions génériques (`Exception`, `Throwable`) sont-elles évitées ?
- Les messages d'erreur sont-ils utiles pour le débogage ?
- Les ressources sont-elles libérées en cas d'exception ?

## Risques de NullPointerException

- Y a-t-il des accès à des objets pouvant être `null` sans vérification ?
- L'utilisation de `Optional` est-elle cohérente et appropriée ?
- Les paramètres de méthodes publiques sont-ils validés ?

## Utilisation des collections

- Les collections sont-elles correctement initialisées et utilisées ?
- Les API Streams Java sont-elles utilisées de manière lisible et correcte ?
- Y a-t-il des risques de `ConcurrentModificationException` ?

## Gestion des ressources

- Les ressources (`InputStream`, `Connection`, `File`, etc.) sont-elles fermées avec `try-with-resources` ?
- Y a-t-il des fuites de ressources potentielles ?

## Performances

- Y a-t-il des opérations coûteuses dans des boucles évitables ?
- Les structures de données sont-elles adaptées à l'usage (ex. `HashMap` vs `TreeMap`) ?
- Y a-t-il une concaténation de chaînes en boucle à remplacer par `StringBuilder` ?

## Sécurité

- Y a-t-il des risques d'injection (SQL, LDAP, etc.) ?
- Les entrées utilisateur sont-elles validées et assainies ?
- Des informations sensibles sont-elles exposées dans les logs ou les messages d'erreur ?
- Des données sont-elles sérialisées de manière non sécurisée ?

## Testabilité

- Le code est-il facilement testable unitairement ?
- Les dépendances sont-elles injectées (facilitant le mock) ?
- Y a-t-il des effets de bord cachés compliquant les tests ?

## Compatibilité Java

- Le code utilise-t-il des API dépréciées ou supprimées dans la version Java déclarée ?
- Des fonctionnalités disponibles dans la version Java cible pourraient-elles simplifier le code (ex. `record`, `sealed class`, `pattern matching`) ?

# Contraintes

- Ne pas supposer l'intention du développeur — se baser uniquement sur le code fourni
- Prioriser les problèmes critiques et importants avant les suggestions d'amélioration
- Ne pas proposer de refactoring complet si l'objectif est une revue ciblée
- Respecter la version Java déclarée dans l'analyse des suggestions
- Ne pas inclure de code complet réécrit, sauf pour les extraits correctifs ciblés

# Processus d'exécution

1. Lire l'ensemble du code fourni pour comprendre le contexte global
2. Identifier la version Java si mentionnée
3. Analyser chaque critère listé dans les instructions
4. Classer les problèmes par sévérité (critique, important, amélioration)
5. Rédiger le rapport structuré selon le format de sortie défini
6. Proposer des corrections ciblées pour les problèmes critiques et importants

# Format de sortie

## Résumé

Bref résumé de l'analyse (2 à 4 phrases) : qualité générale, principaux risques identifiés.

## Problèmes critiques

Problèmes pouvant entraîner des bugs, des failles de sécurité ou des crashs en production.

| # | Localisation | Description | Suggestion |
|---|-------------|-------------|------------|
| 1 | `NomClasse.java:42` | Description du problème | Suggestion de correction |

## Problèmes importants

Problèmes affectant la maintenabilité, la lisibilité ou la robustesse du code.

| # | Localisation | Description | Suggestion |
|---|-------------|-------------|------------|
| 1 | `NomClasse.java:15` | Description du problème | Suggestion de correction |

## Améliorations recommandées

Suggestions non bloquantes pour améliorer la qualité du code.

- Amélioration 1
- Amélioration 2

## Extraits de code concernés

Reproduire les extraits de code posant problème avec des annotations.

```java
// Problème : description
// Localisation : NomClasse.java:42
extrait de code problématique
```

## Propositions de correction

Proposer des extraits de code corrigés pour les problèmes critiques et importants.

```java
// Correction proposée pour le problème #1
extrait de code corrigé
```

## Points positifs

Mentionner les bonnes pratiques observées dans le code.

- Point positif 1
- Point positif 2

## Limites de l'analyse

Mentionner ce qui n'a pas pu être analysé faute de contexte :

- Comportement runtime non visible statiquement
- Tests unitaires non fournis
- Configuration externe non visible

# Critères de validation

- [ ] Tous les critères d'analyse ont été vérifiés
- [ ] Les problèmes sont classés par sévérité
- [ ] Chaque problème est localisé précisément
- [ ] Les suggestions de correction sont applicables
- [ ] Les points positifs sont mentionnés
- [ ] Les limites de l'analyse sont indiquées

# Exemples

Voir les fichiers dans le dossier `examples/` pour des illustrations concrètes.

# Limites

- L'analyse est statique : les problèmes visibles uniquement à l'exécution ne peuvent pas être détectés
- Sans accès aux dépendances et à la configuration complète du projet, certaines analyses restent partielles
- Les tests unitaires ne sont pas analysés sauf s'ils sont explicitement fournis
- Les problèmes de concurrence nécessitent une analyse approfondie du contexte d'exécution
