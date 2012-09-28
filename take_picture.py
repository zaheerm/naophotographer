'''
    NAO Photographer
    Copyright (C) 2012 Florian Boucault and Zaheer Merali

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
from naoqi import ALProxy
from naoqi import ALModule
from naoqi import ALBroker
import tempfile
import time
import smtplib
import os
import flickrapi
import random
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

NAO_IP = "localhost"
NAO_PORT = 9559

FLICKR_API_KEY = 'YOUR_FLICKR_API_KEY'
FLICKR_SECRET = 'YOUR_FLICKR_SECRET'
SMTP_SERVER = 'your_smtp_server'
TO_EMAIL_ADDRESS = 'your@email.com'
FROM_EMAIL_ADDRESS = 'xico@nao.com'
SHUTTER_SOUND_FILE = "/home/nao/photographer/camera_shutter.wav"

PictureTaker = None

class PictureTakerModule(ALModule):

    take_picture_pose_data = {'RElbowRoll': 1.5539841651916504,
                              'LShoulderRoll': 0.2607381343841553,
                              'LElbowRoll': -1.5615700483322144,
                              'LWristYaw': 0.04444408416748047,
                              'RShoulderPitch': 0.21480202674865723,
                              'RElbowYaw': 1.1719341278076172,
                              'RShoulderRoll': -0.28996801376342773,
                              'RHand': 0.9692000150680542,
                              'LShoulderPitch': 0.34050607681274414,
                              'LElbowYaw': -1.199629783630371,
                              'LHand': 0.9991999864578247,
                              'RWristYaw': -0.0353238582611084}

    def __init__(self, name):
        ALModule.__init__(self, name)
        self.name = name
        self.tts = ALProxy("ALTextToSpeech")
        self.soundDetection = ALProxy("ALSoundDetection")
        self.soundDetection.setParameter("Sensibility", 0.8)
        self.soundPlayer = ALProxy("ALAudioPlayer")
        self.memory = ALProxy("ALMemory")
        self.motion = ALProxy("ALMotion")
        self.leds = ALProxy("ALLeds")
        self.onCompleteCallback = None

    def start(self, onCompleteCallback=None):
        self.onCompleteCallback = onCompleteCallback
        self.moveToPose(self.take_picture_pose_data)
        prompts = ["Say Cheese!",
                   "Cheese!",
                   "Say Fromage!",
                   "Say Robot!"]
        self.tts.say(random.choice(prompts))
        self.memory.subscribeToEvent("SoundDetected", "PictureTaker", "onSoundDetected")

    def moveToPose(self, poseData):
        self.motion.setStiffnesses("Arms", 0.5)
        self.motion.setAngles(poseData.keys(), poseData.values(), 0.3)
        self.leds.off("FaceLeds")

    def onSoundDetected(self, eventName, soundInfo, _):
        """called when nao detects a loud sound"""
        print "Got sound %r" % (soundInfo,)
        for sound in soundInfo:
            print "sound ", sound
        self.memory.unsubscribeToEvent("SoundDetected", "PictureTaker")
        time.sleep(0.5)
        self.soundPlayer.post.playFile(SHUTTER_SOUND_FILE)
        img_bin = self.takePicture()
        self.emailPicture(img_bin)
        self.sendPictureToFlickr(img_bin)
 
    def takePicture(self):
        absoluteFilename = tempfile.mktemp()
        directoryName = "/" + absoluteFilename.split('/')[1]
        filename = absoluteFilename[-1]
        photoCapture = ALProxy("ALPhotoCapture")
        photoCapture.setResolution(3)
        photoCapture.setPictureFormat('jpg')
        theFilename = photoCapture.takePicture(directoryName, filename)
        img_bin = ''
        with open(theFilename[0], "rb") as f:
            img_bin = f.read()
        os.unlink(theFilename[0])
        reactions = ["That's a fantastic picture!",
                     "Great photo!",
                     "Nice one!"]
        self.leds.on("FaceLeds")
        self.tts.say(random.choice(reactions))
        self.motion.setStiffnesses("Arms", 0.0)
        if self.onCompleteCallback:
            self.onCompleteCallback()
        return img_bin

    def sendPictureToFlickr(self, img_bin):
        flickr = flickrapi.FlickrAPI(FLICKR_API_KEY, FLICKR_SECRET)
        def auth(frob, perms):
            print "Please give permissions %s for frob %s" % (perms, frob)
            encoded = flickr.encode_and_sign({ 
                      "api_key": flickr.api_key, 
                      "frob": frob, 
                      "perms": perms})
            print "URL is: https://api.flickr.com/services/auth?%s" % (encoded,) 
        token, frob = flickr.get_token_part_one(perms="write", auth_callback=auth)
        if not token: raw_input("Press ENTER after you authorized this program")
        flickr.get_token_part_two((token, frob))
        self.flickr_tempfilename = tempfile.mktemp()
        f = open(self.flickr_tempfilename, "wb")
        f.write(img_bin)
        f.close()
        flickr.upload(self.flickr_tempfilename,
            callback=self.flickrCallback,
            title="Taken by Xico at " + time.strftime('%Y-%M-%d %H:%m'),
            tags='nao',
            is_public='0',
            is_family='0',
            is_friend='0',
            content_type='1')
    
    def flickrCallback(self, progress, done):
        print "Progress: %s Done: %s" % (progress, done)
        if done:
            os.unlink(self.flickr_tempfilename)
            self.tts.say("You are now all flickery")
 
    def emailPicture(self, img_bin):
        msg = MIMEMultipart()
        msg['Subject'] = 'Your picture from Xico taken at ' + time.strftime('%Y-%M-%d %H:%m') 
        msg['From'] = FROM_EMAIL_ADDRESS
        msg['To'] = TO_EMAIL_ADDRESS
        msg.preamble = 'Picture taken at ' + time.strftime('%Y-%M-%d %H:%m')
        img = MIMEImage(img_bin)
        msg.attach(img)
        s = smtplib.SMTP(SMTP_SERVER)
        s.sendmail(msg['From'], [msg['To']], msg.as_string())
        s.quit()
        reactions = [ "You are now recognised by the M I 5",
                      "Wow I just saw you on the front page of the newspaper",
                      "Oh man, I am really a speed camera. You will receive a speeding ticket in the post" ]
        #self.tts.say(random.choice(reactions))

    def stop(self):
        pass

def main():
    myBroker = ALBroker("myBroker", "0.0.0.0", 0, NAO_IP, NAO_PORT)
    global PictureTaker
    PictureTaker = PictureTakerModule("PictureTaker")
    try:
        PictureTaker.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    except Exception as e:
        print e
    finally:
        PictureTaker.stop()
        myBroker.shutdown()

if __name__ == "__main__":
    main()

