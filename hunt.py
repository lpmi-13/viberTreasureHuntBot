import os

from flask import Flask, request, Response
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.messages import PictureMessage
import logging

from viberbot.api.viber_requests import ViberFailedRequest
from viberbot.api.viber_requests import ViberMessageRequest
from viberbot.api.viber_requests import ViberSubscribedRequest

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
    avatar='https://grammarbuffet.org/static/viberhuntbot/assets/ninja-simple-512.png',
    auth_token=os.environ['VIBER_HUNT_TOKEN']
)

viber = Api(bot_configuration)

initialKeyboardResponse = {
    "Type": "keyboard",
    "DefaultHeight": False,
    "BgColor": "#FFFFFF",
    "Buttons": [{
        "Columns": 3,
        "Rows": 1,
        "BgColor": "#008383",
        "ActionType": "reply",
        "ActionBody": "get a clue",
        "Text": "get first clue",
        "Silent": True,
        "TextVAlign": "middle",
        "TextHAlign": "center",
        "TextOpacity": 60,
        "TextSize": "regular"
    }, {
        "Columns": 3,
        "Rows": 1,
        "BgColor": "#7EDFDF",
        "ActionType": "reply",
        "ActionBody": "see some phrases",
        "Text": "see some phrases",
        "Silent": True,
        "TextVAlign": "middle",
        "TextHAlign": "center",
        "TextOpacity": 60,
        "TextSize": "regular"
    }]
 }

keyboardResponse = {
    "Type": "keyboard",
    "DefaultHeight": False,
    "BgColor": "#FFFFFF",
    "Buttons": [{
        "Columns": 6,
        "Rows": 1,
        "BgColor": "#008383",
        "ActionType": "reply",
        "ActionBody": "get a clue",
        "Text": "see clue again",
        "Silent": True,
        "TextVAlign": "middle",
        "TextHAlign": "center",
        "TextOpacity": 60,
        "TextSize": "regular"
    }, {
        "Columns": 6,
        "Rows": 1,
        "BgColor": "#7EDFDF",
        "ActionType": "reply",
        "ActionBody": "see some phrases",
        "Text": "see some phrases",
        "Silent": True,
        "TextVAlign": "middle",
        "TextHAlign": "center",
        "TextOpacity": 60,
        "TextSize": "regular"
    }, {
       "Columns": 6,
       "Rows": 1,
       "BgColor": "#000fff",
       "ActionType": "reply",
       "ActionBody": "send location",
       "Text": "how do I send location?",
       "Silent": True,
       "TextVAlign": "middle",
       "TextHAlign": "center",
       "TextOpacity": 60,
       "TextSize": "regular"
    }]
 }

finalKeyboardResponse = {
    "Type": "keyboard",
    "DefaultHeight": False,
    "BgColor": "#FFFFFF",
    "Buttons": [{
        "Columns": 3,
        "Rows": 2,
        "BgColor": "#008383",
        "ActionType": "reply",
        "ActionBody": "get a clue",
        "Text": "play again",
        "Silent": True,
        "TextVAlign": "middle",
        "TextHAlign": "center",
        "TextOpacity": 60,
        "TextSize": "regular"
    }, {
        "Columns": 3,
        "Rows": 2,
        "BgColor": "#7EDFDF",
        "ActionType": "reply",
        "ActionBody": "see some phrases",
        "Text": "see some phrases",
        "Silent": True,
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
        logger.debug("received interaction from user id: {}".format(user_id))       
        logger.debug("received interaction from user name: {}".format(viber_request.sender.name))
        userStartedHunt = checkUserStatus(user_id)

        if userStartedHunt:

            currentClueNumber = getCurrentClueNumber(user_id)
            if viber_request.message._message_type == 'text':

                if viber_request.message.text.lower() == 'get a clue':
                    sendClues(user_id, currentClueNumber,keyboardResponse)

                elif viber_request.message.text.lower() == 'see some phrases':
                    sendPhrases(user_id, keyboardResponse)

                elif viber_request.message.text.lower() == 'send location':
                    message = TextMessage(text='tap "..." below and select "Send Location" from the menu', keyboard=keyboardResponse)
                    viber.send_messages(user_id, [
                        message
                    ])

                else:
                    message = TextMessage(text='sorry, if you think you\'re at the right place, try sending your location again. Press "get a clue" to see the clue again', keyboard=keyboardResponse)
                    viber.send_messages(user_id, [
                        message
                    ])

            elif viber_request.message._message_type == 'location':
                longitude = viber_request.message.location.longitude
                latitude = viber_request.message.location.latitude

                currentClueNumber = getCurrentClueNumber(user_id)
                correctCoordinates = checkLocation(currentClueNumber)

                if (abs(longitude - correctCoordinates['lon']) < .001) and (abs(latitude - correctCoordinates['lat']) < .001):

                    clueNumber = getNextClueNumber(user_id)
                    if clueNumber == 0:
                        message = PictureMessage(media="https://grammarbuffet.org/static/viberhuntbot/assets/congrats.jpg", text = "Hurray! You finished!",keyboard = finalKeyboardResponse)
                        viber.send_messages(user_id, [
                            message
                        ])
                    else:
                        message = TextMessage(text = 'You found the place! Here\'s your next clue...')
                        viber.send_messages(user_id, [
                            message
                        ])
                        sendClues(user_id, clueNumber, keyboardResponse)

                else:
                    message = TextMessage(text = 'sorry, you haven\'t found it yet. Ask somebody else and try to find the correct place. Then send your location.', keyboard = keyboardResponse)
                    viber.send_messages(user_id, [
                        message
                    ])

            else:
                message = TextMessage(text = 'I\'m not sure about that. Try tapping one of the buttons below or sending your location', keyboard = keyboardResponse)
                viber.send_messages(user_id, [
                   message
                ])

        else:

            if viber_request.message._message_type == 'text':
                if viber_request.message.text.lower() == 'get a clue':
                    clueNumber = getNextClueNumber(user_id)
                    sendClues(user_id, clueNumber, keyboardResponse)

                elif viber_request.message.text.lower() == 'see some phrases':
                    sendPhrases(user_id, initialKeyboardResponse)

                else:
                    message = TextMessage(text = 'would you like to start the treasure hunt, or see some phrases for asking directions?', keyboard=initialKeyboardResponse) 

                    viber.send_messages(user_id, [
                        message
                    ])

            elif viber_request.message._message_type == 'location':
                message = TextMessage(text ='you haven\'t seen the first clue yet', keyboard = initialKeyboardResponse)
                viber.send_messages(user_id, [
                    message
                ])

            else:
                message = TextMessage(text = 'I\'m not sure about that. Try tapping one of the buttons below to see the first clue or see some phrases for asking directions', keyboard = initialKeyboardResponse)
                viber.send_messages(user_id, [
                   message
                ])

    elif isinstance(viber_request, ViberSubscribedRequest):
        logger.debug("received subscribed request from user id: {}".format(viber_request.get_user.id))
        logger.debug("received subscribed request from user name: {}".format(viber_request.get_user.name))
        viber.send_messages(viber_request.get_user.id, [
            TextMessage(text = 'you are now subscribed to the treasure hunt!')
        ])
    elif isinstance(viber_request, ViberFailedRequest):
        logger.warn('client failed receiving message. failure: {0}'.format(viber_request))

    return Response(status = 200)


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


def sendClues(user_id, clueNumber, keyboard):
    clues =  {
        1:'firstclue-beta.jpg',
        2:'secondclue-beta.jpg',
        3:'thirdclue-beta.jpg',
        4:'fourthclue-beta.jpg',
        5:'fifthclue-beta.jpg'
    }

    message = PictureMessage(media = "https://grammarbuffet.org/static/viberhuntbot/assets/%s"%(clues[clueNumber]), text = "Find this place and send your location.", keyboard = keyboard)
    viber.send_messages(user_id, [message])

def sendPhrases(user_id, keyboard):
    message = TextMessage(text = 'TO GET ATTENTION:\n\n- Excuse me...\n- Sorry...\n- Ummm...\n\nTO ASK FOR DIRECTIONS:\n\n- Do you know where this is?\n- Can you help me find this place?\n- How do you get to this place?\n\nTO THANK FOR HELP:\n\n- Thanks very much\n- Thanks for your help\n- Thank you\n- Thanks\n\nIF THEY DON\'T KNOW:\n\n- No worries\n- That\'s alright\n- That\'s okay', keyboard = keyboard)
    viber.send_messages(user_id, [message])

if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 5005)
