import os

requirements_path = r"/home/pi/Desktop/Cabinet/requirements.txt"
requirements_path = r"requirements.txt"

with open(requirements_path) as reqs:
    for line in reqs.readlines():
        cmd = "pip3 install " + line.strip() + " --use-feature=2020-resolver"
        os.system(cmd)
