from naoqi import ALProxy
from naoqi import ALModule
from naoqi import ALBroker

NAO_IP = "localhost"
Template = None

class TemplateModule(ALModule):

    def __init__(self, name):
        ALModule.__init__(self, name)
        self.name = name
        self.tts = ALProxy("ALTextToSpeech")
        self.memory = ALProxy("ALMemory")

    def start(self):
        pass

    def stop(self):
        self.tts.say("You terminated me!")

def main():
    import time

    myBroker = ALBroker("myBroker", "0.0.0.0", 0, NAO_IP, 9559)
    global Template
    Template = TemplateModule("Template")
    Template.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        Template.stop()
        myBroker.shutdown()

if __name__ == "__main__":
    main()

