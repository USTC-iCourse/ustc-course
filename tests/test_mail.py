import sys
sys.path.append('..')  # fix import directory

from app import app
from app.utils import mail
from flask_mail import Mail, Message

def send_test():
    with app.app_context():
        msg = Message("Hello",
                    sender="test@ibat.me",
                    recipients=["ch888@mail.ustc.edu.cn",'ibat@ibat.me'])

        mail.send(msg)


if __name__ == '__main__':
    send_test()
