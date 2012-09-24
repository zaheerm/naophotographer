from naoqi import ALProxy
from naoqi import ALModule
from naoqi import ALBroker
import take_picture
import picture_framer
import headmove
import random

NAO_IP = "localhost"
Photographer = None
PictureTaker = None
PictureFramer = None

class PhotographerModule(ALModule):

    def __init__(self, name):
        ALModule.__init__(self, name)
        self.name = name
        self.tts = ALProxy("ALTextToSpeech")
        self.asr = ALProxy("ALSpeechRecognition")
        self.memory = ALProxy("ALMemory")
        self.posture = ALProxy("ALRobotPosture")
        self.motion = ALProxy("ALMotion")
        self.minimumPeople = 1
        self.numbers = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        self.many = ["many", "lot", "all", "lots", "everybody"]
        self.wordRecognizedCallback = None
        self.wordRecognizedMinimumConfidence = 0.0
        self.lastPhoto = False
        self.pickedUp = False
        self.placed = False
        self.framing = ""

    def start(self):
        self.posture.goToPosture("StandInit", 0.5)
        self.waitForPhotoWord()

    def stop(self):
        try:
            self.memory.unsubscribeToEvent("WordRecognized", self.name)
        except RuntimeError:
            pass
        self.tts.say("You terminated me!")
        self.posture.goToPosture("Sit", 0.5)
        self.motion.stiffnessInterpolation("Body", 0.0, 1.0)
 
    def waitForWords(self, triggerWords, callback, minimumConfidence=0.5):
        try:
            self.memory.unsubscribeToEvent("WordRecognized", self.name)
        except:
            pass
        self.asr.setAudioExpression(False)
        self.asr.setVocabulary(triggerWords, True)
        self.wordRecognizedCallback = callback
        self.wordRecognizedMinimumConfidence = minimumConfidence
        self.memory.subscribeToEvent("WordRecognized", self.name, "onWordRecognized")

    def onWordRecognized(self, eventName, value, subscriberIdentifier):
        recognizedWord = value[0]
        confidence = value[1]
        print "onWordRecognized: '%s' with confidence %f" % (recognizedWord, confidence)

        if confidence < 0.5:
            return
        else:
            self.memory.unsubscribeToEvent("WordRecognized", self.name)
            self.wordRecognizedCallback(recognizedWord)

    def waitForPhotoWord(self):
        triggers = ["photo", "photograph", "picture", "shot", "portrait"]
        self.waitForWords(triggers, self.onPhotoWordRecognized, 0.3)

    def onPhotoWordRecognized(self, recognizedWord):
        print "onPhotoWordRecognized"
        self.tts.say("Of course!")
        HeadMove.start(self.askPeopleNumber)

    def askPeopleNumber(self):
        print "askPeopleNumber"
        self.tts.say("How many people will be on the photo?")
        self.waitForWords(self.numbers + self.many, self.onPeopleNumberWordRecognized, 0.5)

    def onPeopleNumberWordRecognized(self, recognizedWord):
        print "onPhotoWordRecognized"

        reactions = None
        if (recognizedWord in self.many):
            self.minimumPeople = 2
        else:
            self.minimumPeople = int(recognizedWord)

            if self.minimumPeople == 1:    
                reactions = ["It is just you and me then!",
                             "I love taking photos of you!",
                             "Let's make a very personal photo."]
            elif self.minimumPeople == 2:
                reactions = ["You make such a cute couple!",
                             "Let's capture this moment."]
            elif self.minimumPeople == 3:
                reactions = ["It is going to be an incredible trio!",
                             "Go team!"]
        if not reactions:
            reactions = ["Great! I love group shots!",
                         "That's one big family!",
                         "Let's see if we can fit that many!"]

        reaction = random.choice(reactions)
        self.tts.say(reaction)

        questions = ["Where do you want to take the picture?",
                     "Would you like to do it here?"]
        self.tts.say(random.choice(questions))
        self.decideOnNextPhoto()
        if self.framing != "headshot":
            self.waitForPickUp()
            self.waitForPositionWord()
        else:
            self.takeNextPhoto()

    def decideOnNextPhoto(self):
        if self.minimumPeople == 1:
            possibilities = list(PictureFramer.framingSizes)
            self.framing = random.choice(possibilities)
        else:
            possibilities = list(PictureFramer.framingSizes)
            possibilities.remove("headshot")
            self.framing = random.choice(possibilities)

    def takeNextPhoto(self):
        print "BOUDIOU", self.minimumPeople, self.framing
        PictureFramer.frame(self.minimumPeople, self.framing, self.onPictureFramed)
 
    def waitForPickUp(self):
        self.memory.subscribeToEvent("footContactChanged", self.name, "onFootContactChanged")

    def onFootContactChanged(self, eventName, value, subscriberIdentifier):
        print "onFootContactChanged:", value
        if not value:
            self.pickedUp = True

        if self.pickedUp and value:
            self.placed = True
            self.memory.unsubscribeToEvent("footContactChanged", self.name)
            reactions = ["Thank you! That's great.",
                         "Thanks, that will do.",
                         "Perfect, thank you."]
            self.tts.say(random.choice(reactions))
            reactions = ["Let's take a great shot!"]
            self.tts.say(random.choice(reactions))
            self.takeNextPhoto()

    def askToBePlaced(self):
        self.tts.say("Can you place me in front of you then?")

    def waitForPositionWord(self):
        triggers = ["there", "over", "background", "direction"]
        self.waitForWords(triggers, self.onPositionWordRecognized, 0.5)

    def onPositionWordRecognized(self, recognizedWord):
        self.askToBePlaced()

    def onPictureFramed(self):
        PictureTaker.start(self.onPictureTaken)

    def onPictureTaken(self):
        if self.lastPhoto:
            reactions = ["Thanks a lot, that was a great photoshoot.",
                         "That was a lot of fun."]
            self.tts.say(random.choice(reactions))
            reactions = ["All the photos are in your email and on your flicker",
                         "I sent all the shots to your email and flicker"]
            self.tts.say(random.choice(reactions))
            return

        if random.choice([True, False]):
            reactions = ["Let's take another photo",
                         "And another one"]
            self.tts.say(random.choice(reactions))
            self.takeNextPhoto()
        else:
            self.lastPhoto = True
            reactions = ["Let's take a last one",
                         "Ok, great, final photo!"]
            self.tts.say(random.choice(reactions))
            self.takeNextPhoto()
            

def main():
    import time

    myBroker = ALBroker("myBroker", "0.0.0.0", 0, NAO_IP, 9559)
    global Photographer
    global PictureTaker
    global PictureFramer
    global HeadMove
    PictureFramer = picture_framer.PictureFramerModule("PictureFramer")
    PictureTaker = take_picture.PictureTakerModule("PictureTaker")
    HeadMove = headmove.HeadMoveModule("HeadMove")
    Photographer = PhotographerModule("Photographer")
    Photographer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        Photographer.stop()
        myBroker.shutdown()

if __name__ == "__main__":
    main()

