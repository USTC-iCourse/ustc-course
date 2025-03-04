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
import pdfkit
from app.views.search import filter
from flask_login import current_user
from flask import request


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
    token = ts.dumps(email, salt=app.config['EMAIL_CONFIRM_SECRET_KEY'])

    confirm_url = url_for(
        'home.confirm_email',
        action='confirm',
        token=token,
        _external=True,
        _scheme='https')
    html = render_template('email/activate.html',
            confirm_url = confirm_url)

    msg = Message(subject=subject, html=html, recipients=[email])
    mail.send(msg)


def send_reset_password_mail(email, token):
    subject = 'Reset your password'

    reset_url = url_for(
        'home.reset_password',
        token=token,
        _external=True,
        _scheme='https')
    html = render_template('email/reset-password.html',
            reset_url = reset_url)

    msg = Message(subject=subject, html=html, recipients=[email])
    mail.send(msg)


def send_block_review_email(review):
    email = review.author.email
    subject = '您在课程「' + review.course.name + '」中的点评因违反社区规范，已被屏蔽'
    html = render_template('email/block-review.html', review=review)
    msg = Message(subject=subject, html=html, recipients=[email])
    mail.send(msg)

def send_unblock_review_email(review):
    email = review.author.email
    subject = '您在课程「' + review.course.name + '」中的点评已被解除屏蔽'
    html = render_template('email/unblock-review.html', review=review)
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
            img.thumbnail((thumbnail_width, thumbnail_height), Image.LANCZOS)
            img.save(os.path.join(upload_base, new_filename), "PNG")
        except IOError:
            print("Failed to create thumbnail from '" + old_file + "' to '" + new_filename + "'")
            return old_file
        return new_filename
    return old_file

def sanitize(text):
    cleaner = Cleaner(safe_attrs_only=False, style=False)
    text = cleaner.clean_html(text)
    text = re.sub(r'<img ([^>]*) style="height:[0-9]+px; width:[0-9]+px"', r'<img \1', text)
    text = re.sub(r'<img ([^>]*) style="width:[0-9]+px; height:[0-9]+px"', r'<img \1', text)
    # add new rules for CKEditor 5
    text = re.sub(r'<img ([^>]*) width="[0-9]+" height="[0-9]+"', r'<img \1', text)
    text = re.sub(r'<img ([^>]*) height="[0-9]+" width="[0-9]+"', r'<img \1', text)
    return text


@app.template_filter('extract_domain')
def extract_domain_from_url(url):
    match = re.match(r'http[s]*://[a-zA-Z0-9.:-]+/', url)
    if not match:
        return url
    return match.group(0)


@app.template_filter('content_filter')
def content_filter(text):
    return re.sub(r'(脑瘫玩意|傻逼|我艹你妈|艹你妈)', '<span style="background:black;color:black;">请文明用语</span>', text)


@app.template_filter('abstract')
def html_abstract(text):
    abstract = Markup(text).striptags()[0:150]
    return content_filter(abstract)


def find_last_occurence(haystack, needle):
    last_index = -1
    for substr in needle:
        index = haystack.rfind(substr)
        if index >= 0 and index > last_index:
            last_index = index
    return last_index


@app.template_filter('abstract_by_keyword')
def abstract_by_keyword(content, keyword):
    abstract_len = 150
    sentence_max_len = int(abstract_len / 2)

    plaintext = Markup(content).striptags()
    lower_plaintext = plaintext.lower()
    keyword = keyword.lower()
    # remove English and Chinese sentence separators
    sentence = filter(keyword)
    # split sentence into English and Chinese parts
    words = re.findall(r'[A-Za-z0-9]+|[\u4e00-\u9fff]+', sentence)

    first_index = len(plaintext)
    for word in words:
        index = lower_plaintext.find(word)
        if index >= 0 and index < first_index:
            first_index = index
    if first_index == len(plaintext):
        first_index = 0

    last_sentence_end = find_last_occurence(plaintext[:first_index], ['。', '；', '！', '. ', ';', '!'])
    if first_index - last_sentence_end < sentence_max_len:
        first_index = last_sentence_end + 1
    else:
        first_index -= sentence_max_len

    if first_index + abstract_len > len(plaintext):
        first_index = len(plaintext) - abstract_len
        if first_index < 0:
            first_index = 0
    abstract = plaintext[first_index:(abstract_len + first_index)]

    for word in words:
        abstract = re.sub(r'(' + re.escape(word) + ')', '<span style="color:#B22222;font-weight:bold;">\\1</span>', abstract, flags=re.IGNORECASE)
    return content_filter(abstract)


def editor_parse_at(text):
    if not text.endswith('\n'):
        text = text + '\n' # the parse function will not work with @somebody
    mentioned_users = []

    # @user_name text...
    non_space_matches = re.finditer('@([^@<>"\':\s]+)', text)
    non_space_usernames = [match.group(1) for match in non_space_matches]
    # @user name text...
    space_matches = re.finditer('@([^@<>"\':]+)', text)
    space_usernames = [match.group(1) for match in space_matches]
    # @username其他中文字符
    connected_matches = re.finditer('@([a-zA-Z0-9_.-]+)', text)
    connected_usernames = [match.group(1) for match in connected_matches]

    all_matches = set(non_space_usernames + space_usernames + connected_usernames)
    for username in all_matches:
        user = User.query.filter_by(username=username).first()
        if user:
            url = url_for('user.view_profile', user_id=user.id)
            # replace @ to Unicode char ＠ to avoid further substitution when review is edited
            atstring = '<a href="' + url + '">' + '＠' + username + '</a>'
            # warn: simple str.replace is wrong.
            # consider the following case: @boj @bojjenny42
            #   @boj is first matched and replaced, then the string becomes <a href="">@boj</a> <a href="">@boj</a>jenny42
            # the following regexp would do the trick.
            text = re.sub("@" + re.escape(username), atstring, text)
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
        term_str = ' '.join([ term_display(t) for t in term[0:NUM_DISPLAY_TERMS] ])
        if len(term) > NUM_DISPLAY_TERMS:
            return term_str + '...'
        else:
            return term_str
    return term_display(term)

@app.template_filter('term_display_one')
def term_display_one(term):
    return term_display_short(term, 1)

@app.template_filter('name_display_short')
def name_display_short(name_str, NUM_DISPLAY_NAMES=3):
    if isinstance(name_str, str):
        name_list = name_str.split(',')
        if len(name_list) > NUM_DISPLAY_NAMES:
            name_str = ', '.join(name_list[:NUM_DISPLAY_NAMES])
            return name_str + '...'
    return name_str

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
    from flask_login import current_user
    from flask import request
    import re
    
    # First, process existing <a> tags that link to uploaded files
    # Regular expression to find <a> tags
    a_tag_pattern = re.compile(r'<a\s+(?:[^>]*?\s+)?href="([^"]*)"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
    
    # Process all <a> tags in the text
    def replace_link(match):
        url = match.group(1)
        link_text = match.group(2)
        
        # Check if this is a file link (not an image or external link)
        is_file_link = '/uploads/files/' in url
        is_image_link = '/uploads/images/' in url or url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp'))
        is_external_link = not (url.startswith('/') or url.startswith('#') or 'ustc-course' in url)
        
        # Replace file links with login modal link for non-logged-in users
        if is_file_link and not (current_user and current_user.is_authenticated):
            # If the link text is the same as the URL, replace it
            if link_text == url:
                link_text = "Please login to download the attachment"
            
            return f'<a href="#" data-toggle="modal" data-target="#signin">{link_text}</a>'
        elif is_external_link:
            # For external links, add target="_blank"
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{link_text}</a>'
        else:
            # Keep other links as they are
            return match.group(0)
            
    text = a_tag_pattern.sub(replace_link, text)
    
    # Then process plain URLs
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
                # External link - add target="_blank"
                middle = '<a href="http://%s" target="_blank" rel="noopener noreferrer">%s</a>' % (middle, trim_url(middle))
            if middle.startswith('http://') or \
               middle.startswith('https://'):
                # Check if this is a link to an uploaded file (not an image)
                is_file_link = '/uploads/files/' in middle
                is_image_link = '/uploads/images/' in middle or middle.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp'))
                is_external_link = not ('icourse.club' in middle)
                
                # For non-logged-in users, replace file links with login modal
                if is_file_link and not (current_user and current_user.is_authenticated):
                    # Get the text between the tags
                    link_text = trim_url(middle)
                    # If the link text is the same as the URL, replace it
                    if link_text == middle:
                        link_text = "Please login to download the attachment"
                    
                    # Create a link that opens the login modal
                    middle = '<a href="#" data-toggle="modal" data-target="#signin">%s</a>' % link_text
                elif is_external_link:
                    # External link - add target="_blank"
                    middle = '<a href="%s" target="_blank" rel="noopener noreferrer">%s</a>' % (middle, trim_url(middle))
                else:
                    middle = '<a href="%s"%s%s>%s</a>' % (middle,
                        nofollow_attr, target_attr, trim_url(middle))
            if '@' in middle and not middle.startswith('www.') and \
               not ':' in middle and _simple_email_re.match(middle):
                middle = '<a href="mailto:%s">%s</a>' % (middle, middle)
            if lead + middle + trail != word:
                words[i] = lead + middle + trail
    return u''.join(words)

RESERVED_USERNAME = set(['管理员', 'admin', 'root',
    'administrator', 'example', 'test', '匿名', 'anonymous'])

def validate_username(username, check_db=True):
    username = username.lower()
    if re.search('[@&<>"\':\s]', username):
        return ('此用户名含有非法字符，不能注册！')
    if username in RESERVED_USERNAME:
        return ('此用户名已被保留，不能注册！')
    for reserved_name in RESERVED_USERNAME:
        if username.find(reserved_name) != -1:
            return ('此用户名含有被保留的关键词，不能注册！')
    if check_db and User.query.filter_by(username=username).count() != 0:
        return ('此用户名已被他人使用！')
    return 'OK'

def validate_email(email):
    regex = re.compile("[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@(mail\.)?ustc\.edu\.cn")
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

def get_rankings_history_base():
    return os.path.join(app.config['UPLOAD_FOLDER'], 'rankings-history')

def utils_export_rankings_pdf():
    date_str = datetime.now().strftime('%Y-%m-%d')
    pdf_folder = get_rankings_history_base()
    os.makedirs(pdf_folder, exist_ok=True)
    pdf_filename = 'icourse-rankings-' + date_str + '.pdf'
    pdf_path = os.path.join(pdf_folder, pdf_filename)

    url = url_for('stats.view_ranking', show_all=1, _external=True)
    return pdfkit.from_url(url, pdf_path)

def get_rankings_history_file_list():
    pdf_folder = get_rankings_history_base()
    try:
        files = os.listdir(pdf_folder)
        dates = []
        for f in files:
            match = re.search(r'[0-9]+-[0-9]+-[0-9]+', f)
            if match:
                date = match.group(0)
                dates.append((date, f))
        dates = sorted(dates, key=lambda date: date[0])
        year_months = {}
        for date_tuple in dates:
            date = date_tuple[0]
            year_month = date.split('-')[0] + ' 年 ' + date.split('-')[1].strip('0') + ' 月'
            if year_month not in year_months:
                year_months[year_month] = [date_tuple]
            else:
                # only preserve one history file per week
                curr_day = int(date.split('-')[2].strip('0'))
                prev_date = year_months[year_month][-1][0]
                prev_day = int(prev_date.split('-')[2].strip('0'))
                if curr_day - prev_day >= 7:
                    year_months[year_month].append(date_tuple)
        return year_months
    except:
        return []

# Print query/statement with parameters replaced in output
def print_sqlalchemy_statement(statement) -> None:
    from sqlalchemy.dialects import mysql
    import sqlalchemy.orm
    import flask_sqlalchemy.query
    if type(statement) == sqlalchemy.orm.Query or flask_sqlalchemy.query.Query:
        statement = statement.statement
    print(statement.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}))
