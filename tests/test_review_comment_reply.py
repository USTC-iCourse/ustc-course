"""Regression tests for safely rendering review-comment reply links."""

import unittest
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, select_autoescape


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ReplyLinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == 'a' and 'reply-comment' in attributes.get('class', '').split():
            self.links.append(attributes)


class ReviewCommentReplyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        environment = Environment(
            loader=FileSystemLoader(PROJECT_ROOT / 'app' / 'templates'),
            autoescape=select_autoescape(('html',)),
        )
        environment.globals['url_for'] = lambda endpoint, **values: '/user/1'
        environment.filters['content_filter'] = lambda value: value
        environment.filters['utctime'] = lambda value: value
        cls.template = environment.get_template('review-comments.html')

    def render_reply_link(self, username):
        author = SimpleNamespace(id=1, username=username)
        comment = SimpleNamespace(
            author=author,
            content='comment',
            id=2,
            publish_time='2026-09-04',
        )
        review = SimpleNamespace(id=102614, comments=[comment])
        user = SimpleNamespace(is_active=True, is_admin=False)

        rendered = self.template.render(review=review, user=user)
        parser = ReplyLinkParser()
        parser.feed(rendered)
        self.assertEqual(len(parser.links), 1)
        return rendered, parser.links[0]

    def test_username_ending_in_backslash_is_not_embedded_in_javascript(self):
        rendered, link = self.render_reply_link('wwh\\')

        self.assertEqual(link['href'], '#review-comment-input-102614')
        self.assertEqual(link['data-review-id'], '102614')
        self.assertEqual(link['data-reply-to'], 'wwh\\')
        self.assertNotIn('javascript:', rendered)

    def test_legacy_special_characters_remain_data(self):
        username = "legacy'\"<&\\"
        rendered, link = self.render_reply_link(username)

        self.assertEqual(link['data-reply-to'], username)
        self.assertNotIn(username, rendered)
        self.assertNotIn('onclick', link)

    def test_click_handler_reads_the_username_from_the_data_attribute(self):
        script = (
            PROJECT_ROOT / 'app' / 'templates' / 'scripts' / 'review-ajax.html'
        ).read_text(encoding='utf-8')

        self.assertIn("$(document).on('click', '.reply-comment'", script)
        self.assertIn("$(this).attr('data-reply-to')", script)


if __name__ == '__main__':
    unittest.main()
