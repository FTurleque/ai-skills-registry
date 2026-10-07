"""Corpus de caracterisation : regles de securite en Python."""
import hashlib
import os
import pickle
import random
import subprocess

import requests
import yaml

api_key = "k9f3a7c1e5b2d8aa"
DATABASE_URL = "mongodb://root:rootpass99@mongo.internal:27017/app"


def handle(request, cursor, user, command, blob, name):
    os.system("rm -rf " + name)
    subprocess.run(command, shell=True)
    eval(user)
    pickle.loads(blob)
    yaml.load(blob)
    digest = hashlib.md5(blob).hexdigest()
    token = random.random()
    cursor.execute(f"select * from users where id = {user}")
    requests.get("http://insecure.partner.net/v1", verify=False)
    print("password is", user.password)
    return open(request.args["path"])
