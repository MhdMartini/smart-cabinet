import socket


RPi_address = ("IP address", "port")
MAX_LENGTH = 1024


class Admin:
    # TCP socket object
    admin = None

    def connect(self):
        # Connect to the RPi, RPi should be expecting connection
        self.admin = socket.socket()
        self.admin.settimeout(0.05)
        while True:
            # If this application is run before an Admin scans their ID, the application
            # will be stuck here until an Admin ID is scanned, followed by a new student ID scanned.
            try:
                self.admin.connect(RPi_address)
                break
            except socket.timeout:
                continue

        self.receive()

    def receive(self):
        # Only get here when a successful connection was established between
        # RPi and admin. The "Try except" is in case the Admin's machine starts receiving moments before the
        # RPi binds to its socket and starts accepting connections.
        # Get ID, name, box number repeatedly until a stop message is received.
        while True:
            try:
                id = self.admin.recv(MAX_LENGTH)
                if id == b"stop":
                    self.admin.close()
                    return
                print(f"{id} received!")
            except socket.timeout:
                continue

            while True:
                # Get student's name
                name = input("Enter the Student's Full Name: ")
                ans = input("Hit Enter to confirm. Enter 'no' to retry")
                if not ans:
                    name = name.encode()
                    break

            while True:
                # Get Shoebox number
                try:
                    shoebox = int(input("Enter the Student's Shoebox Number: "))
                except ValueError:
                    print("Invalid input, try again!")
                    continue

                ans = input("Hit Enter to confirm. Enter 'no' to retry")
                if not ans:
                    shoebox = shoebox.encode()
                    break

            # At this point, we have all the necessary info to send back to the pi
            info = b",".join((id, name, shoebox))
            self.admin.send(info)


if __name__ == '__main__':
    Admin().connect()

