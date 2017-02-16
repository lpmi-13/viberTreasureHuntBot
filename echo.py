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

app = Flask(__name__)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

bot_configuration = BotConfiguration(
    name='TestyMcBot',
    avatar='https://cdn1.iconfinder.com/data/icons/ninja-things-1/1772/ninja-simple-512.png',
    auth_token=os.environ['VIBER_TOKEN']
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
        "ActionBody": "clue",
        "Text": "get a clue",
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
        "ActionBody": "sentence",
        "Text": "correct a sentence",
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
        if viber_request.message.text == 'clue':
            message = PictureMessage(media="https://github.com/lpmi-13/viberbot/blob/grammarbuffet/assets/locations/IMG_20170128_162050.jpg",text="find this place!")
        elif viber_request.message.text == 'sentence':
            message = TextMessage(text='its helpful to correct sentences.')
        else:
            message = TextMessage(text='have a keyboard!', keyboard=keyboardResponse) 

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

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5005) 
