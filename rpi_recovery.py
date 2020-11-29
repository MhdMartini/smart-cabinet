"""
Script to Recover the Smart Cabinet RPi in case of replacement of damage
Run this file after you install NOOBS
Script will update the system and install the necessary python packages
"""

import os
from main import online
from time import sleep

requirements_path = r"/home/pi/Desktop/Cabinet/requirements.txt"


def update_pi():
    os.system("sudo apt-get update")
    os.system("sudo apt-get dist-upgrade")


def install_reqs():
    # Install the python-mercury first, then rest of packages
    os.system("sudo apt-get install unzip patch xsltproc gcc libreadline-dev")
    with open(requirements_path) as requirements:
        for line in requirements.readlines():
            cmd = "pip3 install " + line.strip() + " --use-feature=2020-resolver"
            os.system(cmd)


if __name__ == '__main__':
    while not online():
        sleep(5)
        continue
    update_pi()
    install_reqs()
