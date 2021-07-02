import shlex
import subprocess
import sys

sk = subprocess.check_output(shlex.split(f"pwgen -s 32")).decode().strip()
with open(".catweb-secret-key", "w") as f:
    f.write(sk)
