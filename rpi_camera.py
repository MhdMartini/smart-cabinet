# Run in RPi terninal:
# sudo apt-get install python3-picamera
import picamera
from datetime import datetime as dt


class CabinetCamera:
    camera = picamera.PiCamera()

    def start(self):
        # Save the video in the corresponding-day folder (e.g. Monday)
        path = "some_path"
        path += dt.now().strftime("%A")
        self.camera.start_recording(path + ".h264")

    def stop(self):
        self.camera.stop_recording()
