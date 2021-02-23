from passlib.hash import pbkdf2_sha256
import os
import json

def check_password(user, passw, json_file="./auth/pass.json"):
    # Read json
    with open(json_file) as f:
        data = json.load(f)

    check_compleet = False
    # Check username and password
    if user == data["users"]["name"] and pbkdf2_sha256.verify(passw, data["users"]["password"]):
        check_compleet = True

    return check_compleet