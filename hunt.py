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

clues = {
    1:'firstclue.jpg',
    2:'secondclue.jpg',
    3:'thirdclue.jpg',
    4:'fourthclue.jpg',
    5:'fifthclue.jpg'
}

answers = ['carfax', 'pembroke', 'christ church', 'dunno', 'beef lane']


@app.route('/', methods=['POST'])
def incoming():
    logger.debug("received request. post data: {0}".format(request.get_data()))

    if not viber.verify_signature(request.get_data(), request.headers.get('X-Viber-Content-Signature')):
        return Response(status=403)

    viber_request = viber.parse_request(request.get_data())

    if isinstance(viber_request, ViberMessageRequest):
        currentClueNumber = getCurrentClueNumber(viber_request.sender.id)

        if viber_request.message.text == 'get a clue':
            clueNumber = getNextClueNumber(viber_request.sender.id)
            sendClues(viber_request.sender.id, clueNumber)

        elif viber_request.message.text == answers[currentClueNumber]:
            clueNumber = getNextClueNumber(viber_request.sender.id)
            sendClues(viber_request.sender.id, clueNumber)

        elif viber_request.message.text == 'see some phrases':
            sendPhrases(viber_request.sender.id)

        else:
            message = TextMessage(text='would you like to start the treasure hunt, or see some phrases for asking directions?', keyboard=keyboardResponse) 

            viber.send_messages(viber_request.sender.id, [
                message
            ])

    elif isinstance(viber_request, ViberSubscribedRequest):
        viber.send_messages(viber_request.get_user.id, [
            TextMessage(text='you are now subscribed to the madness!')
        ])
    elif isinstance(viber_request, ViberFailedRequest):
        logger.warn('client failed receiving message. failure: {0}'.format(viber_request))

    return Response(status=200)


def sendClues(user_id, clueNumber):
    message = PictureMessage(media="https://grammarbuffet.org/static/viberhuntbot/assets/%s"%(clues[clueNumber]),text="what's the name of this place?")
    viber.send_messages(user_id, [message])

def sendPhrases(user_id):
    message = TextMessage(text='Do you know where this is? Can you help me find this place? How do you get to this place?')
    viber.send_messages(user_id, [message])

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5005)
