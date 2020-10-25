from flask import current_app, url_for, render_template
import os
import binascii
import sys
from PIL import Image
from src.email import send_email

def save_picture(form_picture, old_picture_fn):
    random_hex = binascii.hexlify(os.urandom(3)).hex()
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    try:
        if old_picture_fn != 'default.jpg':
            path = os.path.join(current_app.root_path, 'static/profile_pics', old_picture_fn)
            os.remove(path)
    except:
        app.logger.error('Error while deleting old picture', exc_info=sys.exc_info())

    return picture_fn

def send_reset_email(user):
    token = user.get_reset_token()
    send_email('Reset Your Password',
        sender='noreply@demo.com',
        recipients=[user.email],
        text_body=render_template('reset_password.txt', user=user, token=token)
        )
