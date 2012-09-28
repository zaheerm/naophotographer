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
import math
import random

NAO_IP = "localhost"
PictureFramer = None

class FaceDetectedEvent:

    def __init__(self, timestamp, faces, cameraId):
        self.timestamp = timestamp
        self.faces = faces
        self.cameraId = cameraId

class FaceShapeInfo:

    def __init__(self, shapeInfoRaw):
        self.position = shapeInfoRaw[0][1]
        self.sizeX = shapeInfoRaw[0][3]
        self.sizeY = shapeInfoRaw[0][4]
        self.leftEyeX = shapeInfoRaw[1][3][0]
        self.rightEyeX = shapeInfoRaw[1][4][0]
        self.leftMouthX = shapeInfoRaw[1][8][0]
        self.rightMouthX = shapeInfoRaw[1][8][2]
 
class PictureFramerModule(ALModule):

    def __init__(self, name):
        ALModule.__init__(self, name)
        self.name = name
        self.memory = ALProxy("ALMemory")
        self.tts = ALProxy("ALTextToSpeech")
        self.faceDetection = ALProxy("ALFaceDetection")
        self.motion = ALProxy("ALMotion")
        self.previousFaceEvent = None
        self.faceNumber = 0
        self.framing = "medium" # value is in ["medium", "closeup", "headshot"]
       # self.framingSizes = {"medium": 0.15, "closeup": 0.3, "headshot": 0.6}
        self.framingSizes = {"medium": 0.15, "headshot": 0.6}
        self.framingSizeRange = 0.05
        self.onPictureFramed = None

    def start(self):
        #self.frame(1, "closeup")
        self.frame(2, "medium")

    def stop(self):
        self.tts.say("You terminated me!")
        self.motion.stopMove()
        self.faceDetection.unsubscribe(self.name)
        self.memory.unsubscribeToEvent("FaceDetected", self.name)

    def frame(self, faceNumber=1, framing="medium", onPictureFramed=None):
         #self.faceDetection.enableRecognition(False) # makes naoqi crash
#        reactions = ["Let's take a great shot!"]
#        self.tts.say(random.choice(reactions))
        if framing == "headshot":
            prompts = ["Please take me in your arms"]
            self.tts.say(random.choice(prompts))

        self.faceNumber = faceNumber
        self.framing = framing
        self.onPictureFramed = onPictureFramed
        refreshPeriod = 200 # ms
        self.faceDetection.subscribe(self.name, refreshPeriod, 0.0)
        self.memory.subscribeToEvent("FaceDetected", self.name, "onFaceDetected")

    @staticmethod
    def median(values):
        median = sorted(values)[len(values)/2]
        return median

    @staticmethod
    def average(values):
        if len(values) != 0:
            return sum(values) / len(values)
        else:
            return 0

    @staticmethod
    def distanceFromVisualAngle(visualAngle, size):
        return size / (2.0 * math.tan(visualAngle / 2.0))

    @staticmethod
    def sizeFromVisualAngle(visualAngle, distance):
        return 2.0 * distance * math.tan(visualAngle / 2.0)

    @staticmethod
    def sideSize(side1Size, side2Size, oppositeAngle):
        return math.sqrt(side1Size*side1Size + side2Size*side2Size - 2*side1Size*side2Size*math.cos(oppositeAngle))

    @staticmethod
    def oppositeAngle(oppositeSideSize, side1Size, side2Size):
        return math.acos((side1Size*side1Size + side2Size*side2Size - oppositeSideSize*oppositeSideSize) / (2.0 * side1Size * side2Size))

    def onFaceDetected(self, eventName, value, subscriberIdentifier):
        if len(value) == 0:
            # there were faces and now there are none
            return

        event = FaceDetectedEvent(value[0], value[1][:-1], value[4])
        print "onFaceDetected:", "%d faces on camera %d (%d)" % (len(event.faces), event.cameraId, event.timestamp[0])
        shapeInfos = [ FaceShapeInfo(shapeInfoRaw) for shapeInfoRaw in event.faces ]
        sizes = [ shapeInfo.sizeX for shapeInfo in shapeInfos ]
        averageSize = PictureFramerModule.average(sizes)

        #standardFaceHeight = 0.15
        #standardEyeDistance = 0.045
        #standardMouthWidth = 0.045
        #angle = 0.51 # to compute from face size proportions
        #distance = PictureFramerModule.distanceFromVisualAngle(shapeInfos[0].sizeX, standardFaceHeight)
        #eyeAngle = shapeInfos[0].leftEyeX - shapeInfos[0].rightEyeX
        #eyeDistance = PictureFramerModule.sizeFromVisualAngle(eyeAngle, distance)
        #mouthAngle = shapeInfos[0].leftMouthX - shapeInfos[0].rightMouthX
        #mouthWidth = PictureFramerModule.sizeFromVisualAngle(mouthAngle, distance)
        #angle = math.acos(eyeDistance / standardEyeDistance)
        #targetAngle = self.framingSizes[self.framing]
        #targetDistance = PictureFramerModule.distanceFromVisualAngle(targetAngle, standardFaceHeight)
        #walkingDistance = PictureFramerModule.sideSize(distance, targetDistance, angle)
        #walkingAngle = PictureFramerModule.oppositeAngle(targetDistance, walkingDistance, distance)

        if self.framing == "headshot":
            if self.isTooClose(averageSize):
                self.tts.say("I'm a bit too close")
            elif self.isTooFar(averageSize):
                self.tts.say("I'm a bit too far")
        else:
            if self.isTooClose(averageSize):
                print "too close", shapeInfo.sizeX
                if not self.motion.moveIsActive():
                    self.motion.moveToward(-0.8, 0.0, 0.0)
            elif self.isTooFar(averageSize):
                print "too far",shapeInfo.sizeX
                if not self.motion.moveIsActive():
                    self.motion.moveToward(0.8, 0.0, 0.0)
            else:
                self.motion.stopMove()

        if self.previousFaceEvent:
            elapsedSincePrevious = event.timestamp[0] - self.previousFaceEvent.timestamp[0]

            if elapsedSincePrevious <= 4 and \
                len(event.faces) == len(self.previousFaceEvent.faces):

                missingFaces = self.faceNumber - len(event.faces)
                print "missingFaces", missingFaces
                if missingFaces >= 0 and elapsedSincePrevious >= 2:
                    self.missingFaces(missingFaces)
                    return
                else:
                    self.pictureFramed()

        self.previousFaceEvent = event

    def isTooClose(self, faceSize):
        targetSize = self.framingSizes[self.framing]
        return faceSize >= targetSize + self.framingSizeRange

    def isTooFar(self, faceSize):
        targetSize = self.framingSizes[self.framing]
        return faceSize <= targetSize - self.framingSizeRange

    def pictureFramed(self):
        self.faceDetection.unsubscribe(self.name)
        self.memory.unsubscribeToEvent("FaceDetected", self.name)
        print "Picture is framed and ready to be taken."
        reactions = ["Good, that's good, everybody is in.",
                     "Nice, that's right.",
                     "That should be good now."]
        self.tts.say(random.choice(reactions))
        if self.onPictureFramed:
            self.onPictureFramed()

    def missingFaces(self, missingFaces):
        print "Some faces are missing!"
        reactions = ["We are missing people.",
                     "Come on everybody, I cannot see you.",
                     "You are outside the photo!"]
        self.tts.say(random.choice(reactions))

def main():
    import time

    myBroker = ALBroker("myBroker", "0.0.0.0", 0, NAO_IP, 9559)
    global PictureFramer
    PictureFramer = PictureFramerModule("PictureFramer")
    PictureFramer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        PictureFramer.stop()
        myBroker.shutdown()

if __name__ == "__main__":
    main()

