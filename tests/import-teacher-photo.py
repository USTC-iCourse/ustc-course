#!/usr/bin/env python3
import sys
sys.path.append('..')  # fix import directory

from app import app, db
from app.models import *
from PIL import Image
from app.utils import rand_str
import os
import tempfile
from datetime import datetime

PHOTODIR = '../data/teacher-photos'
LISTFILE = '../data/teacher-photo.txt'
MAX_SIZE = 192

def import_one(name, url):
    _, extension = os.path.splitext(url)
    extension = extension.lower()
    if extension == '.gif':
        extension = '.png'
    path = os.path.join(PHOTODIR, name + extension)
    try:
        img = Image.open(path)
    except:
        print("Failed to open " + path)
    try:
        width, height = img.size
        if height > width:
            img = img.crop((0, 0, width, width))
        if width > height:
            img = img.crop((int((width - height)/2), 0, int((width + height)/2), height))
        img.thumbnail((MAX_SIZE, MAX_SIZE), Image.ANTIALIAS)
    except:
        print("Failed to thumbnail " + path)

    if extension not in ['.jpg', '.gif', '.png', '.bmp']:
        extension = '.png'
    new_filename = rand_str() + extension
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], 'images')
    try:
        img.save(os.path.join(upload_path, new_filename))
    except FileNotFoundError:
        os.makedirs(upload_path)
        img.save(os.path.join(upload_path, new_filename))
    except Exception as e:
        print("failed to move file to upload path: " + str(e))
        return

    img_obj = ImageStore(url, new_filename)
    # ImageStore class requires CurrentUser, which does not exist in import script
    # so we need to set the attributes manaully
    img_obj.filename = url
    img_obj.upload_time = datetime.now()
    img_obj.stored_filename = new_filename
    db.session.add(img_obj)

    teachers = Teacher.query.filter_by(name=name).all()
    for teacher in teachers:
        teacher._image = new_filename
        teacher.save()

    print("Saved " + name)

def import_photos():
    f = open(LISTFILE)
    for line in f:
        fields = line.split('\t')
        if len(fields) != 2:
            continue
        if fields[1].strip() == '':
            continue
        import_one(fields[0].strip(), fields[1].strip())

    db.session.commit()

import_photos()
