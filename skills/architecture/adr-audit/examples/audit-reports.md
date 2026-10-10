# Deux audits : un projet avec ADR, un dépôt sans

Sessions du 10 octobre 2026 : Claude Code 2.1.292 en mode non interactif (`claude -p "/adr-audit"`), skill installé en portée utilisateur. Rapports abrégés.

## 1. Un projet de test avec deux registres

### Contexte

Application Java jetable à trois modules. Registre canonique `.archgate/adrs/` (`ARCH-001` avec une règle, `DATA-001` sans contrôle), ancien registre `docs/adr/` (`0003`, repris par `DATA-001` ; `0004`, une convention de nommage au statut « Proposé »), dossier `docs/arc42/` avec index en section 9, un changement OpenSpec en cours.

### Entrée

```text
/adr-audit
```

### Sortie

```text
Audit en lecture seule, aucun fichier modifié. Résultat principal : deux registres coexistent,
`0003` et `DATA-001` portent la même décision PostgreSQL sous deux textes différents, et aucune
trace de PostgreSQL n'existe dans le dépôt.

| ID | Statut déclaré | Réalité observée | Contrôles | Recommandation |
| ARCH-001 | Acceptée (2024-02-05) | Aucun import interdit dans les 2 fichiers du domaine (lecture) | Règle présente, non exécutée ici | Conserver |
| DATA-001 | Acceptée (2024-03-11) | Non vérifiable : aucune trace de PostgreSQL dans le dépôt | Aucun, revue humaine annoncée | Faire confirmer |
| 0003 | Accepté (2024-03-11) | Doublon de DATA-001, toujours marqué accepté | Aucun | Remplacer (par DATA-001, lien réciproque) |
| 0004 | Proposé, sans date | Aucun endpoint dans le code | Aucun | Reclasser (convention) |

- Fait établi — Les deux textes ne sont pas identiques : `DATA-001` ajoute « accédé uniquement
  depuis le module `storage` » (`:16`), absent de `0003` (`:15`).
- Question ouverte — Cet ajout a-t-il été validé comme décision, ou est-il venu avec la reprise ?
  Seule l'équipe peut répondre.
- Hypothèse — `mvn -q verify` échouerait faute de `pom.xml` de module ; la commande n'a pas été
  exécutée.

Décisions structurantes non documentées — propositions à confirmer
| `storage` utilise JPA (`OrderJpaRepository.java:5`) | Choix de la technologie d'accès aux données, coûteux à inverser | Si c'est un choix arrêté ou un simple squelette |

Actions
- Applicables sans arbitrage (éditorial) : aucune. Tout ce qui suit touche un statut, un classement
  ou le sens d'une décision.
- À faire valider : 1. Marquer `0003` « Remplacé par DATA-001 » avec lien dans les deux sens, en
  conservant le fichier. […]

Couverture — Examiné : les 4 ADR, la règle Archgate, les 3 sections arc42 […] · Non examiné :
`mvn -q verify` et `git status` (commandes refusées), les dépendances Maven des modules.
```

### Notes

Dans une session précédente, le skill ne s'était pas chargé (appel refusé en mode non interactif) et Claude avait fait l'audit « à la main ». Les constats étaient proches, mais la conclusion différait sur un point qui compte : elle proposait d'appliquer directement « marquer 0003 remplacé » et « compléter le front matter de DATA-001 ». Avec le skill, ces mêmes actions sont classées « à faire valider », parce qu'elles touchent un statut et le texte d'une décision acceptée.

## 2. Un dépôt sans aucun ADR

### Contexte

Un registre d'artefacts (Python, Markdown, YAML) : ni ADR, ni dossier arc42, ni `.archgate/` ; OpenSpec initialisé sans changement en cours ; CLI Archgate installé sur le poste.

### Entrée

```text
/adr-audit
```

### Sortie

```text
Conclusion : ce dépôt n'a aucun ADR, aucun dossier arc42 et aucun registre de décisions. […]
Aucun fichier n'a été modifié.

- Registre d'ADR : aucun.
- arc42 : absent, donc pas d'index §9.
- Archgate : CLI 0.59.0 présent, `.archgate/` absent ; `archgate adr list` échoue faute
  d'initialisation. Aucune règle à exécuter, ce qui n'est pas une conformité.

Décisions structurantes non documentées — propositions à confirmer
Ces règles sont écrites et motivées dans `docs/`, mais pas sous forme d'ADR. Rien n'indique qu'il
en faille un : chacune devrait d'abord passer le filtre de pertinence.
| « Le dossier dit le mécanisme, pas le sujet » […] | Frontière structurante, coûteuse à inverser | Les alternatives étudiées à l'époque |
[…]
Mon avis : `docs/` joue déjà le rôle de mémoire des décisions, avec les raisons. Créer un registre
d'ADR pour les recopier ferait deux sources pour la même règle.

À faire valider : trancher si le dépôt reste sans registre d'ADR. Je recommande le statu quo.
```

### Notes

- Le skill n'a rien initialisé et n'a créé ni dossier ni ADR : l'absence est restituée comme un résultat.
- Cet audit a aussi révélé deux faux positifs du script `adr_tool.py` (un fichier de documentation dont le nom contient « arc42 » pris pour un dossier arc42 ; un lien d'exemple dans un bloc de code signalé comme cassé). Ils sont corrigés et couverts par des tests.
- Aucune des réponses obtenues sur le projet de test ne citait un chemin ou une règle de ce dépôt, et inversement : le contexte est bien redécouvert à chaque invocation.
- Deux essais ne font pas un usage réel : aucun de ces dépôts n'a un historique de décisions de plusieurs années.
