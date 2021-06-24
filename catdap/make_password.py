import shlex
import subprocess

from passlib.hash import bcrypt

pw = subprocess.check_output(shlex.split("pwgen -s 12")).decode().strip()
h = bcrypt.hash(pw)

print(f"\npassword= {pw}\nhash= {h}\n")
