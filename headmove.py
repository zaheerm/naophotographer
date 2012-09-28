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
import time

HEAD_POSITION_KEY = "Device/SubDeviceList/HeadYaw/Position/Sensor/Value"

NAO_IP = "localhost"
HeadMove = None

class FaceDetectedEvent:

    def __init__(self, timestamp, faces, cameraId):
        self.timestamp = timestamp
        self.faces = faces
        self.cameraId = cameraId

class HeadMoveModule(ALModule):

    def __init__(self, name):
        ALModule.__init__(self, name)
        self.name = name
        self.tts = ALProxy("ALTextToSpeech")
        self.memory = ALProxy("ALMemory")
        self.motion = ALProxy("ALMotion")
        self.faceDetection = ALProxy("ALFaceDetection")
        self.posture = ALProxy("ALRobotPosture")
        self.seenFace = False
        self.onCompleteCallback = None

    def stiffness(self, value, timevalue, joint="Head"):
        self.motion.stiffnessInterpolation(joint, value, timevalue)

    @staticmethod
    def getIncrement(gap):
        if gap == 0.:
            return 0.
        idealIncrement = 0.7
        return gap/math.ceil(abs(gap/idealIncrement))

    @staticmethod
    def getAngles(current_value=-2.080062):
        if current_value < 0:
            last_value = -2.0
            step = -HeadMoveModule.getIncrement(current_value - last_value)
        else:
            last_value = 2.0
            step = HeadMoveModule.getIncrement(last_value - current_value)
        print "step %f last_value %f current_value %f" % (step, last_value, current_value)
        value = current_value
        for i in range(0, 2):
            if step > 0:
                while value <= 2.080062:
                    yield value
                    value += 0.666665
            else:
                while value >= -2.080062:
                    yield value
                    value -= 0.666665
            step = -step

    def onFaceDetected(self, eventName, value, _):
        if len(value) == 0:
            return
        event = FaceDetectedEvent(value[0], value[1][:-1], value[4])
        print "onFaceDetected:", "%d faces on camera %d (%d)" % (len(event.faces), event.cameraId, event.timestamp[0])
        if len(event.faces) > 0:
            self.seenFace = True
 
        if self.seenFace:
            self.stopDetectingFace()
            self.motion.killAll()
            headAngle = self.memory.getData(HEAD_POSITION_KEY)
            #self.tts.say("I spotted you!")
            faceAngleX = value[1][:-1][0][0][1]
            #print faceAngleX
            self.moveBodyToFaceHuman(headAngle + faceAngleX)
            #self.posture.goToPosture("Sit", 0.5)
            #time.sleep(0.5)
            #self.stiffness(0.0, 1.0, joint="Body")
            #self.stiffness(0.0, 1.0)
            #self.tts.say("Finished moving")
            if self.onCompleteCallback:
                self.onCompleteCallback()

    def moveBodyToFaceHuman(self, targetAngle):
        print "About to move body to %f" % (targetAngle,)
        self.motion.post.moveTo(0., 0., targetAngle)
        self.motion.setAngles("HeadYaw", 0.0, 0.5)

    def stopDetectingFace(self):
        try:
            self.faceDetection.unsubscribe(self.name)
            self.memory.unsubscribeToEvent("FaceDetected", self.name)
        except Exception:
            pass
        
    def start(self, onCompleteCallback=None):
        #self.posture.goToPosture("StandInit", 0.5)
        #self.tts.say("I am looking for you")
        refreshPeriod = 100 # ms
        self.onCompleteCallback = onCompleteCallback
        self.faceDetection.subscribe(self.name, refreshPeriod, 0.0)
        self.memory.subscribeToEvent("FaceDetected", self.name, "onFaceDetected")

        current_pos = self.memory.getData(HEAD_POSITION_KEY)
        self.motion.setAngles("HeadPitch", 0.0, 0.5)

        leftTarget = -1.6
        rightTarget = 1.6
        if current_pos < 0:
            targets = [leftTarget, rightTarget]
        else:
            targets = [rightTarget, leftTarget]

        self.motion.setStiffnesses("Head", 1.0)
        for angle in targets:
            self.motion.post.angleInterpolationWithSpeed("HeadYaw", angle, 0.09)
#        self.motion.setStiffnesses("Head", 0.0)
#        self.stopDetectingFace()

    def stop(self):
        self.tts.say("You terminated me!")
        self.stopDetectingFace()

def main():
    import time

    myBroker = ALBroker("myBroker", "0.0.0.0", 0, NAO_IP, 9559)
    global HeadMove
    HeadMove = HeadMoveModule("HeadMove")
    HeadMove.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        HeadMove.stop()
        myBroker.shutdown()

if __name__ == "__main__":
    main()

