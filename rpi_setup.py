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


def terminal(commands=()):
    for command in commands:
        os.system(command)


def update_pi():
    terminal([
        "sudo apt-get update",
        "sudo apt-get upgrade"
    ])


def download_folder():
    terminal([
        r"cd /home/pi/Desktop",
        r"git clone https://github.com/MhdMartini/Smart_Cabinet.git"
    ])


def install_thingmagic():
    terminal([
        "sudo apt-get install unzip patch xsltproc gcc libreadline-dev",
        "sudo pip3 install python-mercuryapi"
    ])


def install_reqs():
    # Install the python-mercury first, then rest of packages
    install_thingmagic()
    terminal(["pip3 install -r requirements.txt"])


if __name__ == '__main__':
    while not online():
        sleep(5)
        continue
    print("Downloading Required Files. This may take several minutes...")
    sleep(2)
    update_pi()
    download_folder()
    install_reqs()
