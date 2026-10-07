"""Corpus de caracterisation : plus de cinq nombres magiques dans un meme fichier (le rapport est plafonne)."""
PORT = 8080
TIMEOUT = 30000
version = "2.10.41"


def compute(total):
    a = total * 4242
    b = total + 31337
    c = total - 86400
    d = total / 7919
    e = total % 1234
    f = total * 5678
    g = total + 9876
    h = total * 1024
    return a + b + c + d + e + f + g + h
