import os

from flask import Flask, request, Response
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.messages import PictureMessage
import logging

from viberbot.api.viber_requests import ViberConversationStartedRequest
from viberbot.api.viber_requests import ViberFailedRequest
from viberbot.api.viber_requests import ViberMessageRequest
from viberbot.api.viber_requests import ViberSubscribedRequest
from viberbot.api.viber_requests import ViberUnsubscribedRequest

from db import getCurrentClueNumber
from db import getNextClueNumber
from db import checkUserStatus

app = Flask(__name__)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

bot_configuration = BotConfiguration(
    name='HuntBot',
    avatar='https://cdn1.iconfinder.com/data/icons/ninja-things-1/1772/ninja-simple-512.png',
    auth_token=os.environ['VIBER_HUNT_TOKEN']
)

viber = Api(bot_configuration)

keyboardResponse = {
    "Type": "keyboard",
    "DefaultHeight": True,
    "BgColor": "#FFFFFF",
    "Buttons": [{
        "Columns": 3,
        "Rows": 2,
        "BgColor": "#008383",
        "BgLoop": True,
        "ActionType": "reply",
        "ActionBody": "get a clue",
        "Text": "get first clue",
        "TextVAlign": "middle",
        "TextHAlign": "center",
        "TextOpacity": 60,
        "TextSize": "regular"
    }, {
        "Columns": 3,
        "Rows": 2,
        "BgColor": "#7EDFDF",
        "BgLoop" : True,
        "ActionType": "reply",
        "ActionBody": "see some phrases",
        "Text": "see some phrases",
        "TextVAlign": "middle",
        "TextHAlign": "center",
        "TextOpacity": 60,
        "TextSize": "regular"
    }]
 } 

@app.route('/', methods=['POST'])
def incoming():
    logger.debug("received request. post data: {0}".format(request.get_data()))

    if not viber.verify_signature(request.get_data(), request.headers.get('X-Viber-Content-Signature')):
        return Response(status=403)

    viber_request = viber.parse_request(request.get_data())

    if isinstance(viber_request, ViberMessageRequest):
        user_id = viber_request.sender.id

        userStartedHunt = checkUserStatus(user_id)

        if userStartedHunt:

            currentClueNumber = getCurrentClueNumber(user_id)
            if viber_request.message._message_type == 'text':

                if viber_request.message.text.lower() == 'get a clue':
                    sendClues(user_id, currentClueNumber)

                elif viber_request.message.text.lower() == checkAnswer(currentClueNumber):
                    clueNumber = getNextClueNumber(user_id)
                    if clueNumber == 0:
                        message = TextMessage(text='Hurray! You finished.')
                        viber.send_messages(user_id, [
                            message
                        ])
                    else:
                        sendClues(user_id, clueNumber) 

                else:
                    message = TextMessage(text='sorry, if you think you\'re at the right place, try sending your location again. Type "get a clue" to see the clue again')
                    viber.send_messages(user_id, [
                        message
                    ])

            else:
                longitude = viber_request.message.location.longitude
                latitude = viber_request.message.location.latitude

                currentClueNumber = getCurrentClueNumber(user_id)
                correctCoordinates = checkLocation(currentClueNumber)

                if (abs(longitude - correctCoordinates.lon) < .001) and (abs(latitude - correctCoordinates.lat) < .001):

                    message = TextMessage(text='You found the place! Here\'s your next clue...')
                    viber.send_messages(user_id, [
                        message
                    ])

                    clueNumber = getNextClueNumber(user_id)
                    if clueNumber == 0:
                        message = TextMessage(text='Hurray! You finished.')
                        viber.send_messages(user_id, [
                            message
                        ])
                    else:
                        sendClues(user_id, clueNumber) 

                else:
                    message = TextMessage(text='sorry, you haven\'t found it yet. Ask somebody else and try to find the place. Then send your location.')
                    viber.send_messages(user_id, [
                        message
                    ])
        else:
            if viber_request.message.text == 'get a clue':
                clueNumber = getNextClueNumber(user_id)
                sendClues(user_id, clueNumber)
            else:
                message = TextMessage(text='would you like to start the treasure hunt, or see some phrases for asking directions?', keyboard=keyboardResponse) 

                viber.send_messages(user_id, [
                    message
                ])

    elif isinstance(viber_request, ViberSubscribedRequest):
        viber.send_messages(viber_request.get_user.id, [
            TextMessage(text='you are now subscribed to the madness!')
        ])
    elif isinstance(viber_request, ViberFailedRequest):
        logger.warn('client failed receiving message. failure: {0}'.format(viber_request))

    return Response(status=200)

def sendDebugMessage(user_id, clueNumber):
    message = TextMessage(text="the current clue number is %s"%(clueNumber))
    viber.send_messages(user_id, [message])

def checkLocation(clue):
    answers = {
        1: {
            'lon': -1.259794,
            'lat': 51.751595
        },
        2: {
           'lon': -1.261547,
           'lat': 51.752013
        },
        3: {
            'lon': -1.261657,
            'lat': 51.754027
        },
        4: {
            'lon': -1.262711,
            'lat': 51.752446
        },
        5: {
           'lon': -1.256197,
           'lat': 51.753333
        }
    }
    return answers[clue]

def checkAnswer(clue):
    answers = {
        1:'carfax',
        2:'pembroke',
        3:'christ church',
        4:'dunno',
        5:'beef lane'
    }
    return answers[clue]

def sendClues(user_id, clueNumber):
    clues =  {
        1:'firstclue-beta.jpg',
        2:'secondclue-beta.jpg',
        3:'thirdclue-beta.jpg',
        4:'fourthclue-beta.jpg',
        5:'fifthclue-beta.jpg'
    }

    message = PictureMessage(media="https://grammarbuffet.org/static/viberhuntbot/assets/%s"%(clues[clueNumber]),text="Find this place and send your location.")
    viber.send_messages(user_id, [message])

def sendPhrases(user_id):
    message = TextMessage(text='Do you know where this is? Can you help me find this place? How do you get to this place?')
    viber.send_messages(user_id, [message])

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5005)
