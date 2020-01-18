from wtforms.csrf.session import SessionCSRF
from datetime import timedelta


class MyBaseForm(FlaskForm):
    class Meta:
        csrf = True
        csrf_class = SessionCSRF
        csrf_secret = app.config['CSRF_SECRET_KEY']
        csrf_time_limit = timedelta(hours=8)

        @property
        def csrf_context(self):
            return request.session
