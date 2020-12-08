import RPi.GPIO as GPIO
from time import sleep
import schedule
import time
from camera_google import googleCamera
from camera_file import dir_entries
from picamera import PiCamera
from datetime import datetime



GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

camera = PiCamera()
camera.resolution = (640, 480)


buzz= 2
button=27
recording=False




GPIO.setup(buzz, GPIO.OUT)
GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP)



def cam_record():
    
    timestamp = datetime.now().isoformat()
    
    camera.annotate_text = timestamp
    camera.annotate_text_size = 50
    #camera.annotate_foreground = Color("yellow")
    
    camera.start_preview(fullscreen=False,window=(1200,200,640,480))
    #camera.start_preview()
    camera.start_recording('/home/pi/Desktop/cabinet/%s.h264'% timestamp)
    
    
def cam_stop():
    camera.stop_recording()
    camera.stop_preview()
    
    
def camera_file(service):  # SAM: Integrating the local and google file sync
	dir_entries()  # SAM: Khaled file management
	googleCamera.camera(service)  # SAM: Run this to sync the file.

drive_service_v3 = googleCamera.login('credentials_drive.json', 'drive_v3')  # SAM: Initialize to link with google account
schedule.every().day.at("23:59").do(camera_file, drive_service_v3) # SAM: Set file sync schedule to everyday at 23:59

while True:
    x=GPIO.input(button)
    
    if x==0:#button is pressed
        cc=cc+1
        sleep(.1)
        print(cc)
        
        
    if x==1:#button is not pressed
        cc=0
        GPIO.output(buzz, GPIO.LOW)
        if recording==True:
            cam_stop()
            recording=False
            googleCamera.camera(drive_service_v3)  # SAM: Run this to sync the file when door closed.
        
        
        
        
        
    if cc>20:
        if recording==False:
            cam_record()
            recording=True
    
    
        
    if cc>600:
        GPIO.output(buzz, GPIO.HIGH)


    schedule.run_pending()  # SAM: Run schedule
    time.sleep(0.5)
    