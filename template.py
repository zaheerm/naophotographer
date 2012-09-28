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

