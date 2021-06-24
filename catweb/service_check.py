import shlex
import subprocess

import argh


def go():
    # sp3 systemd service status
    try:
        lines = (
            subprocess.check_output(
                shlex.split("systemctl --user --plain --no-pager"), timeout=1
            )
            .decode()
            .split("\n")
        )
    except Exception as e:
        print(str(e))
        return "Service check error: couldn't get systemd service status within 1 second. This may be because of your journal size. Consider reducing your journal size."

    ret = list()
    for line in lines:
        l = line.strip().split()
        if len(l) >= 5 and l[4] == "SP3":
            ret.append({"name": l[0], "status": l[3]})
    return ret


if __name__ == "__main__":
    argh.dispatch_command(go)
