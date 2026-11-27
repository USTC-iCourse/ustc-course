"""Database-free template regression tests for Yexi Bookshelf integration."""

import unittest
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, select_autoescape


PROJECT_ROOT = Path(__file__).resolve().parents[1]
YEXI_SITE_URL = 'https://twinjades.github.io/USTC_Study_Materials_Navigation/'


class TagCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self._open_link = None

    def handle_starttag(self, tag, attrs):
        attr_map = dict(attrs)
        entry = {'tag': tag, 'attrs': attr_map, 'text': ''}
        self.tags.append(entry)
        if tag == 'a':
            self._open_link = entry

    def handle_data(self, data):
        if self._open_link is not None:
            self._open_link['text'] += data

    def handle_endtag(self, tag):
        if tag == 'a':
            self._open_link = None


def build_template_env():
    env = Environment(
        loader=FileSystemLoader(PROJECT_ROOT / 'app' / 'templates'),
        autoescape=select_autoescape(('html',)),
    )
    env.globals['url_for'] = lambda endpoint, **values: f'/{endpoint}'
    env.globals['csrf_token'] = lambda: 'test-csrf-token'
    env.globals['current_user'] = SimpleNamespace(
        is_authenticated=False,
        is_active=False,
        is_admin=False,
        is_blocked_now=False,
        is_student=False,
        student_id=None,
        courses_joined=[],
    )
    env.globals['user'] = env.globals['current_user']
    env.globals['request'] = SimpleNamespace(path='/', args={})
    env.globals['this_module'] = 'course.index'
    env.globals['keyword'] = ''
    env.globals['title'] = '测试页面'
    env.globals['hide_title'] = False
    env.globals['description'] = None
    env.globals['course_type'] = None
    env.globals['course_type_dict'] = {}
    env.globals['sort_by'] = None
    env.globals['turnstile_site_key'] = None
    env.globals['date'] = SimpleNamespace(year=2026)

    env.filters['term_display'] = lambda v: ''
    env.filters['term_display_one'] = lambda v: ''
    env.filters['term_display_short'] = lambda v: ''
    env.filters['name_display_short'] = lambda v: v or ''
    env.filters['utctime'] = lambda v: ''
    env.filters['my_urlize'] = lambda v, **kw: v or ''
    return env


class YexiBookshelfTemplateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = build_template_env()

    def _make_course(self, course_id=1, code=None, courseries='00104601', has_term=True):
        latest_term = (
            SimpleNamespace(code=code, courseries=courseries)
            if has_term
            else None
        )
        rate = SimpleNamespace(
            average_rate=0,
            difficulty=None,
            homework=None,
            grading=None,
            gain=None,
        )
        return SimpleNamespace(
            id=course_id,
            name='数值分析',
            teachers=[],
            teachers_count=0,
            teacher_names_display='',
            term_ids=[],
            courseries=courseries if has_term else '',
            latest_term=latest_term,
            course_groups=[],
            review_count=0,
            rate=rate,
            join_type='',
            teaching_type='',
            course_type='',
            dept='',
            course_level='',
            credit=3,
            homepage=None,
            introduction=None,
            summary=None,
            admin_announcement=None,
            reviewed=False,
            following=False,
            follow_count=0,
            downvoted=False,
            downvote_count=0,
            upvoted=False,
            upvote_count=0,
            joined=False,
            related_courses=[],
            num_blocked_reviews=0,
            num_deleted_reviews=0,
            review_per_term_dist=lambda: [],
        )

    def test_desktop_and_mobile_navbars_include_yexi_link_and_script(self):
        layout_html = self.env.get_template('layout.html').render()
        layout_parser = TagCollector()
        layout_parser.feed(layout_html)

        nav_links = [
            t for t in layout_parser.tags
            if t['tag'] == 'a' and t['attrs'].get('href') == YEXI_SITE_URL
        ]
        self.assertEqual(len(nav_links), 1)
        self.assertEqual(nav_links[0]['text'].strip(), '资源')
        self.assertEqual(nav_links[0]['attrs'].get('target'), '_blank')
        self.assertIn('noopener', nav_links[0]['attrs'].get('rel', ''))

        scripts = [
            t for t in layout_parser.tags
            if t['tag'] == 'script'
            and '/static/js/yexi-bookshelf.js' in t['attrs'].get('src', '')
        ]
        self.assertEqual(len(scripts), 1)
        self.assertIn('defer', scripts[0]['attrs'])

        mobile_html = self.env.get_template('mobile-navbar.html').render()
        mobile_parser = TagCollector()
        mobile_parser.feed(mobile_html)
        mobile_links = [
            t for t in mobile_parser.tags
            if t['tag'] == 'a' and t['attrs'].get('href') == YEXI_SITE_URL
        ]
        self.assertEqual(len(mobile_links), 1)
        self.assertEqual(mobile_links[0]['text'].strip(), '资源')
        self.assertEqual(mobile_links[0]['attrs'].get('target'), '_blank')

    def test_course_detail_slot_renders_safely_with_and_without_term(self):
        tmpl = self.env.get_template('course.html')

        html_with_term = tmpl.render(
            course=self._make_course(code=None, courseries='PHYS1008B+01'),
            reviews=[],
            sort_dict={},
            sort_by='upvote',
            term=None,
            rating=None,
            review_num=0,
        )
        parser = TagCollector()
        parser.feed(html_with_term)
        slots = [
            t for t in parser.tags
            if t['attrs'].get('data-yexi-course-slot') == 'detail'
        ]
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]['attrs']['data-course-code'], '')
        self.assertEqual(slots[0]['attrs']['data-course-series'], 'PHYS1008B+01')
        self.assertIn('display:none', slots[0]['attrs'].get('style', ''))

        html_without_term = tmpl.render(
            course=self._make_course(has_term=False),
            reviews=[],
            sort_dict={},
            sort_by='upvote',
            term=None,
            rating=None,
            review_num=0,
        )
        parser_empty = TagCollector()
        parser_empty.feed(html_without_term)
        slots_empty = [
            t for t in parser_empty.tags
            if t['attrs'].get('data-yexi-course-slot') == 'detail'
        ]
        self.assertEqual(len(slots_empty), 1)
        self.assertEqual(slots_empty[0]['attrs']['data-course-code'], '')
        self.assertEqual(slots_empty[0]['attrs']['data-course-series'], '')

    def test_course_list_slots_render_and_escape_special_characters(self):
        tmpl = self.env.get_template('course-list.html')
        courses = SimpleNamespace(
            items=[
                self._make_course(course_id=1, code='CS1001A', courseries='CS1001A.01'),
                self._make_course(course_id=2, code=None, courseries='00104601'),
                self._make_course(course_id=3, has_term=False),
                self._make_course(course_id=4, code='A"<>', courseries='B"&'),
            ]
        )
        rendered = tmpl.render(courses=courses)
        parser = TagCollector()
        parser.feed(rendered)
        slots = [
            t for t in parser.tags
            if t['attrs'].get('data-yexi-course-slot') == 'list'
        ]
        self.assertEqual(len(slots), 4)
        self.assertEqual(slots[0]['attrs']['data-course-code'], 'CS1001A')
        self.assertEqual(slots[0]['attrs']['data-course-series'], 'CS1001A.01')
        self.assertEqual(slots[1]['attrs']['data-course-code'], '')
        self.assertEqual(slots[1]['attrs']['data-course-series'], '00104601')
        self.assertEqual(slots[2]['attrs']['data-course-code'], '')
        self.assertEqual(slots[2]['attrs']['data-course-series'], '')
        self.assertEqual(slots[3]['attrs']['data-course-code'], 'A"<>')
        self.assertEqual(slots[3]['attrs']['data-course-series'], 'B"&')


if __name__ == '__main__':
    unittest.main()
