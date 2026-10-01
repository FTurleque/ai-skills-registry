# Exemple : un diff fautif, le verdict, et ce que l'agent recoit

## Le diff relu

Un agent ajoute une methode de recherche dans un service Java.

```java
public List<String> findUsers(Connection cnx, String nom, String role) throws Exception {
    Statement st = cnx.createStatement();
    String sql = "SELECT * FROM users WHERE name = '" + nom + "' AND role = '" + role + "'";
    List<String> data = new ArrayList<>();
    if (nom == "admin") {
        data.add("admin");
    }
    try {
        st.execute(sql);
    } catch (Exception e) {
    }
    return data;
}
```

## Le verdict rendu

```
- CRITICAL / securite — src/main/java/demo/UserService.java:19
  - Probleme : Requete SQL assemblee par concatenation de chaines : injection SQL possible.
  - A faire : Construire la requete avec des parametres lies (PreparedStatement, parametres
    nommes) et ne jamais concatener une valeur dans le texte SQL.
  - Code : String sql = "SELECT * FROM users WHERE name = '" + nom + "'...

- CRITICAL / bug — src/main/java/demo/UserService.java:27-28
  - Probleme : Exception capturee puis ignoree : l'erreur disparait sans trace.
  - A faire : Journaliser l'exception avec son contexte, ou la propager ; un bloc catch vide
    n'est acceptable qu'avec un commentaire expliquant pourquoi l'erreur peut etre ignoree.
  - Code : } catch (Exception e) {

- MAJOR / bug — src/main/java/demo/UserService.java:22
  - Probleme : Comparaison de chaines avec == : compare les references, pas le contenu.
  - A faire : Utiliser equals, ou Objects.equals pour tolerer null.
  - Code : if (nom == "admin") {

- MAJOR / bug — src/main/java/demo/UserService.java:18
  - Probleme : Ressource ouverte sans fermeture garantie.
  - A faire : Ouvrir la ressource dans un try-with-resources.
  - Code : Statement st = cnx.createStatement();

- MAJOR / nommage — src/main/java/demo/UserService.java:20
  - Probleme : La variable `data` ne dit pas ce qu'elle contient.
  - A faire : La renommer d'apres la donnee qu'elle porte, par exemple `utilisateursTrouves`.

Verdict : bloquant — 2 critical, 3 major, 0 minor
```

## Ce que l'agent recoit

En declenchement automatique, les deux `CRITICAL` deviennent un blocage. Le message transmis a
l'agent contient les constats bloquants, les autres en information, puis la marche a suivre :

```
SUPERVISEUR DE CODE — correction requise avant de rendre la main.

2 probleme(s) bloquant(s) detecte(s) dans les fichiers que tu viens de modifier.

## A corriger maintenant
[les deux constats CRITICAL, avec fichier, ligne et action]

## Signale sans blocage (a traiter si c'est dans le perimetre de ta tache)
[les constats MAJOR et MINOR]

## Comment proceder
1. Corrige chaque point bloquant ci-dessus, dans les fichiers indiques.
2. Ne touche pas au code hors du perimetre de ta tache et de ces corrections.
3. Si un point est un faux positif, ne le contourne pas : explique en une ligne pourquoi le
   code est correct, puis continue.
4. N'ajoute ni suppression d'avertissement (NOSONAR, @SuppressWarnings, # noqa) ni
   desactivation de test pour faire taire un controle.

Rapport complet : <projet>/.claude/supervisor/rapport-20261001-224500.md
```

L'agent corrige, puis rend la main. Le superviseur repasse : si les deux `CRITICAL` ont disparu,
il laisse passer avec les `MAJOR` en avertissement.

## Le meme lot de problemes, trois fois

Si l'agent ne parvient pas a corriger et que le superviseur retrouve exactement les memes
constats trois fois de suite, l'empreinte du lot est liberee : le quatrieme passage avertit sans
bloquer, et le message indique que le point est a arbitrer manuellement. La session ne tourne
pas en rond.
