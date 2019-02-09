#!/usr/bin/env python3
import sys
sys.path.append('..')  # fix import directory

from app import app
from app.models import User
from PIL import Image
from app.utils import rand_str

ctx = app.test_request_context()
ctx.push()

users = User.query.all()
for u in users:
    if u._avatar:
        with Image.open('../uploads/images/' + u._avatar) as img:
            image_width, image_height = img.size
            thumbnail_width = 192
            thumbnail_height = 192
            if image_width <= thumbnail_width and image_height <= thumbnail_height:
                continue
            # generate thumbnail if the avatar is too large
            new_filename = rand_str() + '.png'
            try:
                img.thumbnail((thumbnail_width, thumbnail_height), Image.ANTIALIAS)
                img.save('../uploads/images/' + new_filename, "PNG")
            except IOError:
                print("Failed to create thumbnail from '" + u._avatar + "' to '" + new_filename + "'")
            u._avatar = new_filename
            u.save()
            print('User ID ' + str(u.id) + ' original ' + u._avatar + ' thumbnail ' + new_filename)
