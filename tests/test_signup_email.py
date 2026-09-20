'''The rules that decide what a registration address means.

A single email box on the signup form let a student register as a teacher by
leaving `mail.` out of the domain, which produced an account whose activation
mail went to a mailbox that does not exist.  These are the checks that stand
behind the split field.
'''
import unittest
from unittest.mock import patch

from app.utils import (EMAIL_DOMAIN_IDENTITY, identity_for_email,
                       validate_email_parts, email_identity_warning)


def _query_returning(result):
    '''A stand-in for Model.query whose filter_by(...).first() is fixed.'''
    class _Query:
        @staticmethod
        def filter_by(**kwargs):
            class _Result:
                @staticmethod
                def first():
                    return result
            return _Result
    return _Query


def _no_user_exists():
    return patch('app.utils.User', **{'query': _query_returning(None)})


def _roster_holds(teacher):
    return patch('app.utils.Teacher', **{'query': _query_returning(teacher)})


class IdentityForEmailTests(unittest.TestCase):
    def test_student_domain_means_student(self):
        self.assertEqual(identity_for_email('a@mail.ustc.edu.cn'), 'Student')

    def test_staff_domain_means_teacher(self):
        self.assertEqual(identity_for_email('a@ustc.edu.cn'), 'Teacher')

    def test_domain_is_matched_case_insensitively(self):
        self.assertEqual(identity_for_email('a@MAIL.USTC.EDU.CN'), 'Student')

    def test_foreign_domain_has_no_identity(self):
        self.assertIsNone(identity_for_email('a@gmail.com'))

    def test_every_accepted_domain_maps_to_an_identity(self):
        for domain, identity in EMAIL_DOMAIN_IDENTITY.items():
            self.assertIn(identity, ('Student', 'Teacher'), domain)


class ValidateEmailPartsTests(unittest.TestCase):
    def test_accepts_a_bare_prefix(self):
        with _no_user_exists():
            self.assertEqual(validate_email_parts('zhangsan', 'mail.ustc.edu.cn'), 'OK')

    def test_surrounding_space_is_ignored(self):
        with _no_user_exists():
            self.assertEqual(validate_email_parts('  zhangsan  ', 'ustc.edu.cn'), 'OK')

    def test_a_pasted_address_is_named_as_such(self):
        # Rather than reported as a malformed mailbox, which is what a naive
        # concatenation would produce.
        with _no_user_exists():
            message = validate_email_parts('zhangsan@ustc.edu.cn', 'mail.ustc.edu.cn')
        self.assertNotEqual(message, 'OK')
        self.assertIn('@', message)

    def test_empty_prefix_is_refused(self):
        with _no_user_exists():
            self.assertNotEqual(validate_email_parts('', 'mail.ustc.edu.cn'), 'OK')

    def test_a_domain_outside_the_map_is_refused(self):
        # The form offers a choice, so this only happens on a forged post.
        with _no_user_exists():
            self.assertNotEqual(validate_email_parts('zhangsan', 'evil.com'), 'OK')

    def test_a_taken_address_is_refused(self):
        with patch('app.utils.User', **{'query': _query_returning(object())}):
            self.assertNotEqual(validate_email_parts('zhangsan', 'mail.ustc.edu.cn'), 'OK')


class EmailIdentityWarningTests(unittest.TestCase):
    def test_student_domain_is_never_warned_about(self):
        with _roster_holds(None):
            self.assertIsNone(email_identity_warning('zhangsan@mail.ustc.edu.cn'))

    def test_staff_address_in_the_roster_is_not_warned_about(self):
        with _roster_holds(object()):
            self.assertIsNone(email_identity_warning('prof@ustc.edu.cn'))

    def test_staff_address_outside_the_roster_is_warned_about(self):
        with _roster_holds(None):
            self.assertIsNotNone(email_identity_warning('zhangsan@ustc.edu.cn'))

    def test_the_warning_names_the_student_domain(self):
        # Its whole job is to tell a student what to switch to.
        with _roster_holds(None):
            self.assertIn('mail.ustc.edu.cn', email_identity_warning('zhangsan@ustc.edu.cn'))


if __name__ == '__main__':
    unittest.main()
