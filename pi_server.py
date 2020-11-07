import socket

RPi_address = ("10.0.0.157", 4236)
MAX_LENGTH = 1024


class PiServer:
    def __init__(self):
        # Bind to TCP socket and wait for Admin App to connect
        self.sock = socket.socket()
        self.sock.bind(RPi_address)
        self.sock.listen()
        # Connect to Admin object (Admin application).
        # When connection is successful, the Admin App will notify Admin
        self.admin, _ = self.sock.accept()

    def get_command(self):
        return self.admin.recv(MAX_LENGTH)

    def send_msg(self, msg):
        self.admin.send(msg)