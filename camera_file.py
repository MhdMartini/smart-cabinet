from datetime import datetime
from os import scandir
import time
import os

m_duration=336#14days*24hour
my_path='/home/pi/Desktop/cabinet'

def dir_entries():
    dir_entries = scandir(my_path)
    for entry in dir_entries:
        if entry.is_file():
        info = entry.stat()
        filelife=(time.time())-(info.st_mtime)
        filelife=filelife/3600 #60seconds*60min=hour
        filelife_str = "{:.2f}".format(filelife)
        print(f'{entry.name} {filelife_str} min')
        if filelife>=m_duration:
            os.remove(f'{my_path}/{entry.name}')
            print(f'{entry.name} was deleted')
        time.sleep(3600)