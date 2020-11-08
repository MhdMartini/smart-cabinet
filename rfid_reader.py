"""
Script to Interface with the ThingMagic RFID Reader and the Smart Cabinet Inventory Application.
Interfacing is done with the python-mercuryapi module:
****************************************************************************
The MIT License (MIT)

Copyright (c) 2016-2020 Petr Gotthard

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
Script is to be run on RPi Noobs
****************************************************************************
"""

import mercury
import time


class RFIDReader:
    reader = None
    SCAN_TIME = 1000

    def __init__(self, port):
        # Create and configure the reader object
        self.PORT = port
        self.reader = mercury.Reader(self.PORT)
        self.reader.set_region("NA")
        self.reader.set_read_plan([1], "GEN2")
        self.reader.enable_exception_handler(self.error_handle)

    @staticmethod
    def error_handle(error):
        print(error)

    def scan(self):
        # return a set of scanned items (1 second scanning)
        tags = self.reader.read(timeout=self.SCAN_TIME)
        tags = {tag.epc.decode() for tag in tags} if tags else set()
        return tags

    def scan_until(self):
        # Scan inventory, then keep scanning until a new inventory item is detected.
        # Return that item
        starting_inventory = self.scan()
        while True:
            new_inventory = self.scan()
            diff = starting_inventory ^ new_inventory
            if diff:
                return diff.pop()
            time.sleep(1)
