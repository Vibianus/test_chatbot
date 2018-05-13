#coding:utf-8
import os
import sys
import json
import editdistance
import threading, time
import template_json
import urllib2
import urllib
import re

import requests
from flask import Flask, request
from send_msg import send_template_message, send_message
from set_workflow import set_temp
from handle_msg import handle_message

app = Flask(__name__)

user_dict = {}
thread_flag = False

def check_user_status():
    global user_dict
    while True :
        for key in user_dict.keys() :
            if time.time() - user_dict[key] > 1800 :
                user_dict.pop(key, None)

        time.sleep(1800)



@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/', methods=['POST'])
def webhook():

    # endpoint for processing incoming messaging events

    global thread_flag   #only run this thread one time
    global user_dict
    if not thread_flag :
        threading.Thread(target = check_user_status, args = (), name = 'check_thread').start()
        thread_flag = True


    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    if data["object"] == "page":

        for entry in data["entry"]:
            if "messaging" in entry :
                for messaging_event in entry["messaging"]:

                    if messaging_event.get("message"):  # someone sent us a message

                        sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                        recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                        if "text" in messaging_event["message"] :
                            message_text = messaging_event["message"]["text"]  # the message's text
                            message_text = message_text.encode('utf-8').lower()

                            # dorm internet workflow
                            if "quick_reply" in messaging_event["message"] :
                                payload = messaging_event["message"]["quick_reply"]["payload"]
                                if payload == 'GOT_IT' :
                                    send_message( sender_id, '很高興能為你幫上忙🙂' )
                                elif payload == 'ROLL_BACK' :
                                    faq = template_json.Template_json(sender_id,template_type=2,
                                          text="是否曾申請過帳號呢? (請用是/否按扭回答以便記錄)", payload_yes = "START_STATE_YES", payload_no = "START_STATE_NO" )
                                    send_template_message( faq )
                                else :
                                    reply = set_temp(payload, sender_id)
                                    send_template_message( reply )

                            else :
                                reply = handle_message( message_text, sender_id )

                                for key in user_dict.keys() :
                                    print(key)
                                    print(user_dict[key])

                                if not sender_id in user_dict : # not in time interval
                                    #暫時拿掉限制
                                    #if reply == '抱歉> < 我還無法處理這個問題，請您等待專人為您回答🙂 ' : user_dict[sender_id] = time.time() #使用者待專人回答, chatbot對該使用者暫停
                                    if type(reply) == str :
                                        send_message( sender_id, reply )
                                    else : #template
                                        send_template_message(reply)
                                pass

                    if messaging_event.get("delivery"):  # delivery confirmation
                        pass

                    if messaging_event.get("optin"):  # optin confirmation
                        pass

                    if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                        sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                        recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                        message_text = messaging_event["postback"]["payload"]  # the message's text
                        message_text = message_text.encode('utf-8').lower()
                        reply = handle_message( message_text, sender_id )
                        if not sender_id in user_dict : # not in time interval
                            user_dict[sender_id] = time.time()
                            send_message( sender_id, reply )

    return "ok", 200

def log(message):  # simple wrapper for logging to stdout on heroku
    print str(message)
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)
