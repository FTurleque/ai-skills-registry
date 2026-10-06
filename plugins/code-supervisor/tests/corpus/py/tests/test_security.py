"""Corpus de caracterisation : en code de test, les constats critiques sont abaisses et les URL http ignorees."""
import hashlib
import pickle
import subprocess

password = "testpassword123"
URL = "http://insecure.partner.net/v1"


def test_security(blob, command):
    subprocess.run(command, shell=True)
    pickle.loads(blob)
    assert hashlib.md5(blob).hexdigest()
