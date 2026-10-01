# Nom du Serveur

Une phrase : ce que ce serveur apporte à Claude.

## Les outils apportés

| Outil | Ce qu'il fait |
|-------|---------------|
| `mcp__mon-serveur__<outil>` | ... |

## Prérequis

Runtime, binaire, accès réseau, VPN, compte. Tout ce qui doit être vrai avant que le branchement
fonctionne.

## Ce que le serveur lit et écrit

**Section obligatoire.** Un serveur MCP tourne avec les droits du processus qui le lance. Dire
quelles données il voit, ce qu'il modifie, et ce qu'il envoie à l'extérieur.

## Installation

Fusionner `.mcp.json` dans le projet, renseigner les secrets par variables d'environnement, puis
vérifier dans une nouvelle session que les outils apparaissent.

## Limites

Ce que le serveur ne sait pas faire, ses quotas, ses latences. Section obligatoire.
