"""
Script:     rpi_setup.py
Project:    Smart Cabinet
Author:     Mohamed Martini
Version:    1.0 - Tested
Purpose:    Recover the Smart Cabinet RPi in case of replacement of damage
"""

import os
import socket
from time import sleep

url = r"https://github.com/UML-ECE-LAB/Smart_Cabinet"

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
    print("Updating the Raspberry Pi...")
    sleep(1)
    terminal([
        "sudo apt-get update",
        "sudo apt-get upgrade"
    ])


def download_folder():
    print("Downloading Project Folder...")
    sleep(1)
    terminal([
        r"cd /home/pi/Desktop"
    ])
    if os.path.exists("Smart_Cabinet"):
        terminal([
            r"sudo rm -r Smart_Cabinet"
        ])
    terminal([
        f"git clone {url}"
    ])


def install_thingmagic():
    terminal([
        "sudo apt-get install unzip patch xsltproc gcc libreadline-dev",
        "sudo pip3 install python-mercuryapi"
    ])


if __name__ == '__main__':
    while not online():
        sleep(5)
        continue
    print("Downloading Required Files. This may take several minutes...")
    sleep(1)
    print("You may be prompted to confirm downloads. Make sure to Enter Y when prompted. ")
    sleep(3)

    sleep(2)
    update_pi()
    download_folder()
    install_thingmagic()
