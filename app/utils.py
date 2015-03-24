from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail
from . import app


mail = Mail(app)
ts = URLSafeTimedSerializer(app.config["SECRET_KEY"])
