"""Regles de securite : secrets, injections, crypto, configuration dangereuse."""
from __future__ import annotations

import re
from typing import List

from model import CRITICAL, MAJOR, MINOR, CAT_SECURITY, Finding
from source import SourceFile

PLACEHOLDER = re.compile(
    r"(?i)(xxx|yyy|zzz|todo|changeme|change_me|placeholder|example|sample|dummy|fake|"
    r"your[_-]?|<[^>]+>|\$\{|%s|%\(|\{\{|\{\d|env\.|getenv|process\.env|system\.getenv|"
    r"config\.|settings\.|secret_name|redacted|\*\*\*|null|none|empty)"
)

# Chaque regle : (id, langs|None, regex, severite, message, correctif)
PATTERNS = [
    # ---------------------------------------------------------------- secrets
    ("SEC.AWS_KEY", None, re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), CRITICAL,
     "Cle d'acces AWS en clair dans le code.",
     "Retirer la cle, la lire depuis une variable d'environnement ou un gestionnaire de secrets, et la revoquer : elle doit etre consideree comme compromise."),
    ("SEC.PRIVATE_KEY", None, re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"), CRITICAL,
     "Cle privee embarquee dans un fichier source.",
     "Deplacer la cle hors du depot (keystore, coffre de secrets) et la regenerer."),
    ("SEC.JWT", None, re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}"), CRITICAL,
     "Jeton JWT en dur dans le code.",
     "Supprimer le jeton et le recuperer a l'execution depuis la configuration."),
    ("SEC.SLACK_GH_TOKEN", None, re.compile(r"\b(?:xox[baprs]-[A-Za-z0-9-]{10,}|gh[pousr]_[A-Za-z0-9]{20,})"), CRITICAL,
     "Jeton d'API (Slack / GitHub) en clair.",
     "Supprimer le jeton du code, le revoquer et le lire depuis l'environnement."),
    ("SEC.HARDCODED_SECRET", None, re.compile(
        r"(?i)\w*?(password|passwd|pwd|secret|api[_-]?key|apikey|access[_-]?token|auth[_-]?token|"
        r"client[_-]?secret|private[_-]?key|motdepasse|mot_de_passe|token)\b\s*(?::\s*\w+\s*)?[=:]\s*[\"']([^\"']{6,})[\"']"), CRITICAL,
     "Secret ecrit en dur dans le code.",
     "Externaliser la valeur (variable d'environnement, fichier de configuration hors depot, coffre) et ne laisser aucune valeur par defaut exploitable."),
    ("SEC.CONNSTRING", None, re.compile(
        r"(?i)(?:jdbc:|mongodb(?:\+srv)?://|postgres(?:ql)?://|mysql://|amqp://|redis://)[^\s\"']*:[^\s\"'@/]{4,}@"), CRITICAL,
     "Chaine de connexion contenant un mot de passe.",
     "Retirer les identifiants de l'URL et les injecter via la configuration d'execution."),

    # ---------------------------------------------------------------- injection
    ("SEC.SQL_CONCAT", None, re.compile(
        r"(?i)(?:execute|executeQuery|executeUpdate|executeBatch|createQuery|createNativeQuery|"
        r"prepareStatement|rawQuery|query|exec)\s*\(\s*(?:[\"'][^\"']*(?:select|insert|update|delete|drop|where|from)[^\"']*[\"']\s*\+|"
        r"[\"'][^\"']*[\"']\s*\+)"), CRITICAL,
     "Requete SQL construite par concatenation de chaines : injection SQL possible.",
     "Utiliser une requete parametree (PreparedStatement avec ?, parametres nommes JPA, bind variables) au lieu de concatener les valeurs."),
    ("SEC.SQL_CONCAT", None, re.compile(
        r"(?i)([\"'])(?:(?!\1).)*?\b(?:select\s|insert\s+into|update\s|delete\s+from|where\s|values\s*\()(?:(?!\1).)*\1\s*\+"), CRITICAL,
     "Requete SQL assemblee par concatenation de chaines : injection SQL possible.",
     "Construire la requete avec des parametres lies (PreparedStatement, parametres nommes) et ne jamais concatener une valeur dans le texte SQL."),
    ("SEC.SQL_FSTRING", ("python",), re.compile(
        r"(?i)(?:execute|executemany)\s*\(\s*f[\"']|(?:execute|executemany)\s*\(\s*[\"'][^\"']*%s[^\"']*[\"']\s*%"), CRITICAL,
     "Requete SQL interpolee (f-string ou %) : injection SQL possible.",
     "Passer les valeurs en parametres a execute() au lieu de les interpoler dans la requete."),
    ("SEC.CMD_INJECTION", None, re.compile(
        r"(?i)(?:Runtime\.getRuntime\(\)\.exec|new\s+ProcessBuilder|child_process\.exec(?!File)|"
        r"os\.system|os\.popen|subprocess\.(?:call|run|Popen|check_output))\s*\([^)]*(?:\+|\$\{|%s|f[\"']|`)"), CRITICAL,
     "Commande systeme construite a partir de valeurs dynamiques : injection de commande possible.",
     "Passer les arguments sous forme de tableau sans shell (ProcessBuilder(List), subprocess avec liste et shell=False) et valider les entrees."),
    ("SEC.SHELL_TRUE", ("python",), re.compile(r"shell\s*=\s*True"), MAJOR,
     "Appel systeme avec shell=True.",
     "Passer la commande en liste d'arguments avec shell=False ; si le shell est indispensable, echapper via shlex.quote."),
    ("SEC.EVAL", None, re.compile(r"(?<![\w.])(?:eval|new\s+Function)\s*\(|(?<![\w.])exec\s*\(\s*[^)]*(?:\+|f[\"'])"), CRITICAL,
     "Evaluation dynamique de code.",
     "Supprimer eval/exec : utiliser un parseur dedie (JSON, expression whitelistee) ou une table de dispatch."),
    ("SEC.XSS_SINK", ("js", "ts"), re.compile(
        r"(?:\.innerHTML\s*=|\.outerHTML\s*=|document\.write\s*\(|dangerouslySetInnerHTML|\$\(\s*[^)]*\)\.html\s*\()"), MAJOR,
     "Injection de HTML non echappe : XSS possible.",
     "Utiliser textContent, un moteur de template echappant par defaut, ou assainir le HTML (DOMPurify)."),
    ("SEC.DESERIALIZE", None, re.compile(
        r"(?:ObjectInputStream\s*\(|readObject\s*\(\s*\)|pickle\.loads?\s*\(|cPickle\.loads?\s*\(|"
        r"yaml\.load\s*\((?![^)]*Safe)|XMLDecoder\s*\(|unserialize\s*\()"), CRITICAL,
     "Deserialisation de donnees non fiables : execution de code possible.",
     "Remplacer par un format de donnees sans execution (JSON) ou restreindre strictement les classes autorisees ; yaml.safe_load pour YAML."),
    ("SEC.PATH_TRAVERSAL", None, re.compile(
        r"(?:new\s+File\s*\(|Paths\.get\s*\(|FileInputStream\s*\(|open\s*\(|fs\.read(?:File|FileSync)\s*\()"
        r"[^)]*(?:request|req\.|param|query|body|userInput|user_input|argv|getParameter)"), MAJOR,
     "Chemin de fichier construit depuis une entree utilisateur : traversee de repertoire possible.",
     "Normaliser le chemin puis verifier qu'il reste sous la racine autorisee, ou n'accepter qu'une liste blanche de noms."),

    # ---------------------------------------------------------------- crypto / tls
    ("SEC.WEAK_HASH", None, re.compile(
        r"(?i)(?:MessageDigest\.getInstance\s*\(\s*[\"'](?:MD5|SHA-?1)[\"']|hashlib\.(?:md5|sha1)\s*\(|"
        r"createHash\s*\(\s*[\"'](?:md5|sha1)[\"'])"), MAJOR,
     "Fonction de hachage cassee (MD5/SHA-1).",
     "Utiliser SHA-256 ou plus ; pour un mot de passe, utiliser bcrypt, scrypt ou Argon2 avec sel."),
    ("SEC.WEAK_CIPHER", None, re.compile(
        r"(?i)Cipher\.getInstance\s*\(\s*[\"'](?:DES|DESede|RC2|RC4|Blowfish|AES/ECB)[^\"']*[\"']"), MAJOR,
     "Algorithme ou mode de chiffrement faible (DES, RC4, ECB).",
     "Utiliser AES-GCM (ou AES-CBC avec HMAC) avec un IV aleatoire par message."),
    ("SEC.INSECURE_RANDOM", None, re.compile(
        r"(?i)(?:new\s+Random\s*\(|Math\.random\s*\(|random\.(?:random|randint|choice)\s*\()"
        r"[^;\n]{0,80}|(?:token|secret|password|salt|nonce|otp|session)[\w]*\s*=\s*(?:new\s+Random|Math\.random|random\.)"), MINOR,
     "Generateur pseudo-aleatoire non cryptographique.",
     "Si la valeur est un secret (jeton, sel, mot de passe), utiliser SecureRandom / secrets / crypto.randomBytes."),
    ("SEC.TLS_DISABLED", None, re.compile(
        r"(?i)(?:verify\s*=\s*False|rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED|"
        r"setHostnameVerifier\s*\(|ALLOW_ALL_HOSTNAME_VERIFIER|TrustAllCerts|trustAllCertificates|"
        r"InsecureSkipVerify\s*:\s*true|CURLOPT_SSL_VERIFYPEER\s*,\s*(?:0|false))"), CRITICAL,
     "Verification du certificat TLS desactivee.",
     "Retablir la validation du certificat et de l'hote ; pour un environnement de test, ajouter le certificat au magasin de confiance plutot que desactiver le controle."),
    ("SEC.HTTP_URL", None, re.compile(r"[\"']http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])[\w.-]+"), MINOR,
     "URL en HTTP non chiffre.",
     "Passer l'appel en HTTPS."),

    # ---------------------------------------------------------------- divers
    ("SEC.LOG_SECRET", None, re.compile(
        r"(?i)(?:log(?:ger)?\.(?:trace|debug|info|warn|error)|console\.(?:log|info|warn|error)|print(?:ln)?)\s*\("
        r"[^;\n]*\b(?:password|passwd|pwd|secret|token|apikey|api_key|credential|authorization|cookie|cvv|iban)\b"), MAJOR,
     "Donnee sensible ecrite dans les journaux.",
     "Retirer la donnee du message de log ou la masquer (seuls les 4 derniers caracteres, ou un identifiant non reversible)."),
    ("SEC.XXE", None, re.compile(
        r"(?:DocumentBuilderFactory|SAXParserFactory|XMLInputFactory|TransformerFactory)\.newInstance\s*\(\s*\)"), MAJOR,
     "Fabrique XML creee sans durcissement : XXE possible.",
     "Desactiver les entites externes et les DTD (setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true) et disallow-doctype-decl)."),
    ("SEC.CSRF_OFF", None, re.compile(r"(?i)(?:csrf\(\)\.disable\(\)|csrf\s*:\s*false|@?CsrfExempt)"), MAJOR,
     "Protection CSRF desactivee.",
     "Reactiver la protection CSRF, ou justifier l'exception par un commentaire explicite si l'endpoint est sans etat et authentifie par jeton."),
    ("SEC.PERMIT_ALL", None, re.compile(r"(?i)(?:permitAll\s*\(\s*\)|anonymous\(\)\.|AllowAnyOrigin|\"\\*\"\s*\)\s*;?\s*//\s*cors|setAllowedOrigins\s*\(\s*[\"']\*)"), MINOR,
     "Autorisation ou CORS ouverts a tous.",
     "Restreindre aux origines et roles necessaires."),
]


# Regles evaluees sur la ligne brute : le contenu des litteraux fait partie du signal.
_RAW_RULES = {
    "SEC.AWS_KEY", "SEC.PRIVATE_KEY", "SEC.JWT", "SEC.SLACK_GH_TOKEN",
    "SEC.HARDCODED_SECRET", "SEC.CONNSTRING", "SEC.HTTP_URL",
    "SEC.SQL_CONCAT", "SEC.SQL_FSTRING", "SEC.WEAK_HASH", "SEC.WEAK_CIPHER",
    "SEC.DESERIALIZE", "SEC.PERMIT_ALL",
}
# Regles ou une valeur factice ou une lecture d'environnement annule l'alerte.
_SECRET_RULES = {
    "SEC.AWS_KEY", "SEC.PRIVATE_KEY", "SEC.JWT", "SEC.SLACK_GH_TOKEN",
    "SEC.HARDCODED_SECRET", "SEC.CONNSTRING",
}
# Secrets a format connu : meme en code de test, ils restent critiques.
_KEEP_SEVERITY_IN_TESTS = ("SEC.AWS_KEY", "SEC.PRIVATE_KEY", "SEC.JWT", "SEC.SLACK_GH_TOKEN", "SEC.CONNSTRING")
_COMMENT_PREFIXES = ("//", "#", "*", "/*")
_MAX_LINE_CHARS = 2000        # au-dela, la ligne brute est tronquee (fichier minifie, donnees embarquees)
_EVIDENCE_WIDTH = 200
# Un generateur pseudo-aleatoire ne pose probleme que s'il produit un secret : il lui faut un mot-cle voisin.
_RANDOM_CONTEXT = re.compile(r"(?i)(token|secret|password|passwd|salt|nonce|otp|session|key|iv|uuid|id\b)")
_SAFE_EVAL = re.compile(r"(?i)\b(?:safe_?eval|ast\.literal_eval)\b")


def _is_false_match(sf: SourceFile, rule_id: str, match, raw: str) -> bool:
    """Exceptions propres a certaines regles : une correspondance du motif qui n'est pas un constat."""
    if rule_id in _SECRET_RULES and PLACEHOLDER.search(match.group(0)):
        return True
    if rule_id == "SEC.INSECURE_RANDOM":
        return not _RANDOM_CONTEXT.search(raw)
    if rule_id == "SEC.EVAL":
        return bool(_SAFE_EVAL.search(raw))
    if rule_id == "SEC.HTTP_URL":
        return sf.is_test
    return False


def _severity(sf: SourceFile, rule_id: str, severity: str) -> str:
    if sf.is_test and severity == CRITICAL and rule_id not in _KEEP_SEVERITY_IN_TESTS:
        return MAJOR     # code de test : on alerte sans bloquer la boucle
    return severity


def _line_findings(sf: SourceFile, idx: int, raw: str, clean: str, stripped: str) -> List[Finding]:
    findings: List[Finding] = []
    for rule_id, langs, rx, severity, message, fix in PATTERNS:
        if langs and sf.lang not in langs:
            continue
        # Les regles "secret" se lisent sur la ligne brute (le litteral compte),
        # les autres sur la ligne nettoyee (pour ignorer commentaires et chaines).
        match = rx.search(raw if rule_id in _RAW_RULES else clean)
        if not match or _is_false_match(sf, rule_id, match, raw):
            continue
        findings.append(Finding(
            rule=rule_id, category=CAT_SECURITY, severity=_severity(sf, rule_id, severity), message=message, fix=fix,
            file=sf.path, line=idx, evidence=stripped[:_EVIDENCE_WIDTH],
        ))
    return findings


def check(sf: SourceFile) -> List[Finding]:
    findings: List[Finding] = []
    for idx, raw in enumerate(sf.lines, start=1):
        if not sf.is_changed(idx):
            continue
        raw = raw[:_MAX_LINE_CHARS]
        clean = sf.clean_lines[idx - 1] if idx - 1 < len(sf.clean_lines) else ""
        stripped = raw.strip()
        if not stripped or stripped.startswith(_COMMENT_PREFIXES):
            continue
        findings.extend(_line_findings(sf, idx, raw, clean, stripped))
    return findings
