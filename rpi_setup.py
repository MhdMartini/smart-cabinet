"""
Script to Recover the Smart Cabinet RPi in case of replacement of damage
Run this file after you install NOOBS
Script will update the system and install the necessary python packages
"""

import os
import socket
from time import sleep

requirements_path = r"/home/pi/Desktop/Smart_Cabinet/requirements.txt"


def online():
    # Function to know whether there is internet connection.
    # Thanks to miraculixx:
    # https://stackoverflow.com/questions/20913411/test-if-an-internet-connection-is-present-in-python/20913928
    try:
        host = socket.gethostbyname("one.one.one.one")
        s = socket.create_connection((host, 80), 2)
        s.close()
        return True
    except socket.gaierror:
        return False


def terminal(commands=[]):
    for command in commands:
        os.system(command)


def download_files():
    terminal([
        r"cd /home/pi/Desktop",
        r"git clone https://github.com/MhdMartini/Smart_Cabinet.git"
    ])


def update_pi():
    print("Updating the Pi ...")
    terminal([
        "sudo apt-get update",
    ])
    print("Pi Successfully Updated!")


def install_thingmagic():
    terminal([
        r"cd /home/pi/Desktop/Smart_Cabinet"
        "sudo apt-get install unzip patch xsltproc gcc libreadline-dev",
        "sudo pip3 install python-mercuryapi"
    ])


def install_reqs():
    # Install the python-mercury first, then rest of packages
    install_thingmagic()
    with open(requirements_path) as requirements:
        for line in requirements.readlines():
            cmd = "pip3 install " + line.strip() + " --use-feature=2020-resolver"
            terminal([cmd])


if __name__ == '__main__':
    while not online():
        sleep(5)
        continue
    download_files()
    update_pi()
    install_reqs()
