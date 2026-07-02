# Exemple : Revue d'une classe Java avec mauvaises pratiques

## Contexte

Cet exemple illustre une revue de code Java sur une classe de service contenant plusieurs problèmes typiques : gestion d'exceptions insuffisante, risques de NullPointerException, et ressources non fermées.

## Entrée

**Version Java** : Java 11

**Code fourni** :

```java
public class UserService {

    private Connection connection;

    public UserService() {
        try {
            connection = DriverManager.getConnection("jdbc:mysql://localhost/mydb", "root", "password");
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public String getUserName(int id) {
        String name = null;
        try {
            Statement stmt = connection.createStatement();
            ResultSet rs = stmt.executeQuery("SELECT name FROM users WHERE id = " + id);
            if (rs.next()) {
                name = rs.getString("name");
            }
        } catch (Exception e) {
            System.out.println("Error: " + e.getMessage());
        }
        return name;
    }

    public void deleteUser(int id) {
        try {
            Statement stmt = connection.createStatement();
            stmt.executeUpdate("DELETE FROM users WHERE id = " + id);
        } catch (Exception e) {
            // ignore
        }
    }
}
```

## Sortie attendue

### Résumé

La classe `UserService` présente plusieurs problèmes critiques de sécurité et de robustesse. La gestion des connexions et des ressources est incorrecte, et le code est vulnérable aux injections SQL. Des corrections importantes sont nécessaires avant toute mise en production.

### Problèmes critiques

| # | Localisation | Description | Suggestion |
|---|-------------|-------------|------------|
| 1 | `UserService.java:17` | Injection SQL via concaténation directe de `id` dans la requête | Utiliser `PreparedStatement` avec un paramètre `?` |
| 2 | `UserService.java:27` | Injection SQL via concaténation directe de `id` dans la requête DELETE | Utiliser `PreparedStatement` avec un paramètre `?` |
| 3 | `UserService.java:5` | Credentials en dur dans le code source (`"root"`, `"password"`) | Externaliser dans un fichier de configuration ou des variables d'environnement |
| 4 | `UserService.java:29` | Exception silencieusement ignorée sur `deleteUser` — les erreurs de suppression ne sont pas signalées | Logger l'exception ou la propager |

### Problèmes importants

| # | Localisation | Description | Suggestion |
|---|-------------|-------------|------------|
| 1 | `UserService.java:14-22` | `Statement` et `ResultSet` ne sont jamais fermés — fuite de ressources | Utiliser `try-with-resources` |
| 2 | `UserService.java:25-31` | `Statement` non fermé | Utiliser `try-with-resources` |
| 3 | `UserService.java:21` | Retour `null` si l'utilisateur n'existe pas — risque de NPE pour l'appelant | Retourner `Optional<String>` |
| 4 | `UserService.java:8` | `e.printStackTrace()` en production expose la stack trace | Utiliser un logger (`java.util.logging`, SLF4J, etc.) |

### Propositions de correction

```java
// Correction pour getUserName — PreparedStatement + try-with-resources + Optional
public Optional<String> getUserName(int id) {
    String sql = "SELECT name FROM users WHERE id = ?";
    try (PreparedStatement stmt = connection.prepareStatement(sql)) {
        stmt.setInt(1, id);
        try (ResultSet rs = stmt.executeQuery()) {
            if (rs.next()) {
                return Optional.of(rs.getString("name"));
            }
        }
    } catch (SQLException e) {
        logger.error("Erreur lors de la récupération de l'utilisateur {}", id, e);
    }
    return Optional.empty();
}
```

### Points positifs

- La structure de la classe est simple et lisible
- Les méthodes ont des noms explicites

### Limites de l'analyse

- La gestion du cycle de vie de la connexion (`connection`) au niveau application n'a pas pu être évaluée sans le contexte du projet complet
- Les tests unitaires ne sont pas fournis

## Notes

Cet exemple couvre les problèmes les plus fréquents dans du code Java legacy. La correction complète implique également de revoir l'architecture de gestion des connexions (pool de connexions).
