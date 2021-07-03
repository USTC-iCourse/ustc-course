from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail,Message
from . import app
from flask import render_template, url_for, Markup
from random import randint
from datetime import datetime
from app.models import ImageStore, User
import hashlib
import os
from lxml.html.clean import Cleaner
import pytz
import re
from PIL import Image
from email.utils import format_datetime
import lxml.html
from hashlib import sha256


mail = Mail(app)
ts = URLSafeTimedSerializer(app.config["SECRET_KEY"])


def rand_str():
    random_num = randint(100000,999999)
    raw_str = str(datetime.utcnow()) + str(randint(100000,999999)) + str(randint(100000,999999))
    hash_fac = hashlib.new('ripemd160')
    hash_fac.update(raw_str.encode('utf-8'))
    return hash_fac.hexdigest()


def send_confirm_mail(email):
    subject = 'Confirm your email.'
    token = ts.dumps(email, salt='email-confirm-key')

    confirm_url = url_for(
        'home.confirm_email',
        action='confirm',
        token=token,
        _external=True)
    html = render_template('email/activate.html',
            confirm_url = confirm_url)

    msg = Message(subject=subject, html=html, recipients=[email])
    mail.send(msg)

def send_reset_password_mail(email):
    subject = 'Reset your password'
    token = ts.dumps(email, salt='password-reset-key')

    reset_url = url_for(
        'home.reset_password',
        token=token,
        _external=True)
    html = render_template('email/reset-password.html',
            reset_url = reset_url)

    msg = Message(subject=subject, html=html, recipients=[email])
    mail.send(msg)



def allowed_file(filename,type):
    return '.' in filename and \
            filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS'][type]

def handle_upload(file,type):
    ''' type is the file type,for example:image.
    more file type to be added in the future.'''
    if file and allowed_file(file.filename,type):
        old_filename = file.filename
        file_suffix = old_filename.split('.')[-1]
        new_filename = rand_str() + '.' + file_suffix
        try:
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'],type+'s/')
            file.save(os.path.join(upload_path, new_filename))
        except FileNotFoundError:
            os.makedirs(upload_path)
            file.save(os.path.join(upload_path, new_filename))
        except Exception as e:
            return False,e
        img = ImageStore(old_filename,new_filename)
        img.save()
        return True,new_filename
    return False,"File type disallowd!"

def resize_avatar(old_file):
    upload_base = os.path.join(app.config['UPLOAD_FOLDER'],'image'+'s/')
    with Image.open(os.path.join(upload_base, old_file)) as img:
        image_width, image_height = img.size
        thumbnail_width = 192
        thumbnail_height = 192
        if image_width <= thumbnail_width and image_height <= thumbnail_height:
            return old_file
        # generate thumbnail if the avatar is too large
        new_filename = rand_str() + '.png'
        try:
            img.thumbnail((thumbnail_width, thumbnail_height), Image.ANTIALIAS)
            img.save(os.path.join(upload_base, new_filename), "PNG")
        except IOError:
            print("Failed to create thumbnail from '" + old_file + "' to '" + new_filename + "'")
            return old_file
        return new_filename
    return old_file

def sanitize(text):
    if text.strip():
        cleaner = Cleaner(safe_attrs_only=False, style=False)
        return cleaner.clean_html(text)
    else:
        return text

@app.template_filter('abstract')
def html_abstract(text):
    return Markup(text).striptags()[0:150]

def editor_parse_at(text):
    if not text.endswith('\n'):
        text = text + '\n' # the parse function will not work with @somebody
    mentioned_users = []
    matches = re.finditer('@([^@<>"\'\s]+)', text)
    if not matches:
        return text, set(mentioned_users)
    for username in set([match.group(1) for match in matches]):
        if len(username) > 30:
            continue
        user = User.query.filter_by(username=username).first()
        if user:
            url = url_for('user.view_profile', user_id=user.id)
            # replace @ to Unicode char ＠ to avoid further substitution when review is edited
            atstring = '<a href="' + url + '">' + '＠' + username + '</a>'
            # warn: simple str.replace is wrong.
            # consider the following case: @boj @bojjenny42
            #   @boj is first matched and replaced, then the string becomes <a href="">@boj</a> <a href="">@boj</a>jenny42
            # the following regexp would do the trick.
            text = re.sub("@" + re.escape(username) + '([@<>"\'\s])',
                          atstring + '\\1', text)
            mentioned_users.append(user)
    return text, set(mentioned_users)

@app.template_filter('utctime')
def utctime(date):
    local = pytz.utc.localize(date, is_dst=False)
    return local.strftime('%m/%d/%Y %H:%M:%S')

@app.template_filter('localtime')
def localtime_minute(date):
    local = pytz.utc.localize(date, is_dst=False).astimezone(pytz.timezone('Asia/Shanghai'))
    return local.strftime('%Y-%m-%d %H:%M')

@app.template_filter('rfc822time')
def rfc822time(date):
    # used for RSS <pubDate>
    return format_datetime(date)

@app.template_filter('updatetime')
def updatetime_minute(date):
    local = pytz.utc.localize(date, is_dst=False).astimezone(pytz.timezone('Asia/Shanghai'))
    now = datetime.now()
    if (now.date() - local.date()).days == 0:
        return local.strftime('今天 %H:%M')
    elif (now.date() - local.date()).days == 1:
        return local.strftime('昨天 %H:%M')
    elif now.year == local.year:
        return str(local.month) + '月' + str(local.day) + '日 ' + local.strftime('%H:%M')
    else:
        return str(local.year) + '年' + str(local.month) + '月' + str(local.day) + '日 ' + local.strftime('%H:%M')

@app.template_filter('term_display')
def term_display(term):
    if isinstance(term, list):
        return ' '.join([ term_display(t) for t in term ])
    try:
        if term[4] == '1':
            return term[0:4] + '秋'
        elif term[4] == '2':
            return str(int(term[0:4])+1) + '春'
        elif term[4] == '3':
            return str(int(term[0:4])+1) + '夏'
        else:
            return '未知'
    except:
        return '未知'

@app.template_filter('term_display_short')
def term_display_short(term, NUM_DISPLAY_TERMS=2):
    if isinstance(term, list):
        str = ' '.join([ term_display(t) for t in term[0:NUM_DISPLAY_TERMS] ])
        if len(term) > NUM_DISPLAY_TERMS:
            return str + '...'
        else:
            return str
    return term_display(term)

@app.template_filter('term_display_one')
def term_display_one(term):
    return term_display_short(term, 1)

_word_split_re = re.compile(r'''([<>\s]+)''')
_punctuation_re = re.compile(
    '^(?P<lead>(?:%s)*)(?P<middle>.*?)(?P<trail>(?:%s)*)$' % (
        '|'.join(map(re.escape, ('(', '<', '&lt;'))),
        '|'.join(map(re.escape, ('.', ',', ')', '>', '\n', '&gt;')))
    )
)
_simple_email_re = re.compile(r'^\S+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+$')
_striptags_re = re.compile(r'(<!--.*?-->|<[^>]*>)')
_entity_re = re.compile(r'&([^;]+);')
_letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
_digits = '0123456789'

@app.template_filter('my_urlize')
def my_urlize(text, trim_url_limit=None, nofollow=False, target=None):
    """Converts any URLs in text into clickable links. Works on http://,
    https:// and www. links. Links can have trailing punctuation (periods,
    commas, close-parens) and leading punctuation (opening parens) and
    it'll still do the right thing.
    If trim_url_limit is not None, the URLs in link text will be limited
    to trim_url_limit characters.
    If nofollow is True, the URLs in link text will get a rel="nofollow"
    attribute.
    If target is not None, a target attribute will be added to the link.
    """
    trim_url = lambda x, limit=trim_url_limit: limit is not None \
                         and (x[:limit] + (len(x) >=limit and '...'
                         or '')) or x
    words = _word_split_re.split(text)
    nofollow_attr = nofollow and ' rel="nofollow"' or ''
    if target is not None and isinstance(target, string_types):
        target_attr = ' target="%s"' % escape(target)
    else:
        target_attr = ''
    for i, word in enumerate(words):
        match = _punctuation_re.match(word)
        if match:
            lead, middle, trail = match.groups()
            if middle.startswith('www.') or (
                '@' not in middle and
                not middle.startswith('http://') and
                not middle.startswith('https://') and
                len(middle) > 0 and
                middle[0] in _letters + _digits and (
                    middle.endswith('.org') or
                    middle.endswith('.net') or
                    middle.endswith('.com')
                )):
                middle = '<a href="http://%s"%s%s>%s</a>' % (middle,
                    nofollow_attr, target_attr, trim_url(middle))
            if middle.startswith('http://') or \
               middle.startswith('https://'):
                middle = '<a href="%s"%s%s>%s</a>' % (middle,
                    nofollow_attr, target_attr, trim_url(middle))
            if '@' in middle and not middle.startswith('www.') and \
               not ':' in middle and _simple_email_re.match(middle):
                middle = '<a href="mailto:%s">%s</a>' % (middle, middle)
            if lead + middle + trail != word:
                words[i] = lead + middle + trail
    return u''.join(words)

RESERVED_USERNAME = set(['管理员', 'admin', 'root',
    'Administrator', 'example', 'test'])

def validate_username(username, check_db=True):
    if re.search('[@&<>"\'\s]', username):
        return ('此用户名含有非法字符，不能注册！')
    if username in RESERVED_USERNAME:
        return ('此用户名已被保留，不能注册！')
    if check_db and User.query.filter_by(username=username).first():
        return ('此用户名已被他人使用！')
    return 'OK'

def validate_email(email):
    regex = re.compile("[a-zA-Z0-9_]+@(mail\.)?ustc\.edu\.cn")
    if not regex.fullmatch(email):
        return ('必须使用科大邮箱注册!')
    if User.query.filter_by(email=email).first():
        return ('此邮件地址已被注册！')
    return 'OK'

@app.template_filter('text')
def text(html_string):
    document = lxml.html.document_fromstring(html_string)
    return document.text_content()

@app.template_filter('link_absolute')
def absolute(html_string):
    return lxml.html.make_links_absolute(html_string, base_url="https://icourse.club")

def cal_validation_code(user):
    expected = user.email + user.password
    return sha256(expected.encode('utf-8')).hexdigest()
