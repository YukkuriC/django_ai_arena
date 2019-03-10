from django.shortcuts import redirect
from django.http import JsonResponse
from django.utils import timezone
from django.core import mail
from django.conf import settings
from django.template import loader
from . import usr_models
from email.mime.image import MIMEImage
import json

def add_img(src, img_id):
    with open(src, 'rb') as f:
        msg_image = MIMEImage(f.read())
    msg_image.add_header('Content-ID', img_id)
    return msg_image


def send_util(from_mail, recipient_list, subject):
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Title</title>
    </head>
    <body>
    牛逼呀小伙子，你成功了
    <img src="cid:test_cid"/>
    </body>
    </html>
    '''
    msg = mail.EmailMessage(subject, html, from_mail, recipient_list)
    msg.content_subtype = 'html'
    msg.encoding = 'utf-8'
    image = add_img('assets/喵爪爪.gif', 'test_cid')
    msg.attach(image)
    if msg.send():
        return True
    else:
        return False