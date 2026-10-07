"""Corpus de caracterisation : ce que les regles de securite doivent ignorer."""
import ast

# Commentaire : un secret cite dans un commentaire n'en est pas un.
# password = "commentedsecret4"

# Litteraux et commentaires de fin de ligne : les regles lues sur la ligne nettoyee les ignorent.
message = "do not call eval(x), shell=True or os.system(cmd + y)"
value = 1  # eval(user)

# Valeurs factices ou lues dans l'environnement : pas de secret.
password = "changeme-please"
api_key = "your_api_key_here"
DATABASE = "postgres://user:changeme@localhost/db"

# Evaluation reputee sure : exec avec concatenation, mais passee par literal_eval.
exec("x = " + ast.literal_eval(message))

# Alea sans lien avec un secret.
jitter = random.random()

# Le mot qui decide se lit sur la ligne brute : un commentaire de fin de ligne compte.
pause = random.randint(1, 5)  # token bucket
result = eval(expression)  # safe_eval wrapper

# Ces motifs sont propres a d'autres langages (JavaScript, SQL) : pas de constat en Python.
element.innerHTML = value
