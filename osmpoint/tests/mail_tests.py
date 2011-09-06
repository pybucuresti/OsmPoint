# encoding: utf-8

import flask
import unittest2

from mock import patch, Mock

class MailTests(unittest2.TestCase):

    def setUp(self):
        from page_tests import app_for_testing
        self.app, _cleanup = app_for_testing()
        self.addCleanup(_cleanup)
        self._ctx = self.app.test_request_context()
        self._ctx.push()
        self.addCleanup(self._ctx.pop)
        self.app.config['MAIL_SERVER'] = 'my_mailhost'
        self.app.config['MAIL_FROM'] = 'me@example.com'
        smtp_patch = patch('osmpoint.mails.smtplib')
        self.mock_smtplib = smtp_patch.start()
        self.addCleanup(smtp_patch.stop)
        self.smtp = self.mock_smtplib.SMTP.return_value

    def test_send_mail(self):
        from osmpoint.mails import send_mail
        send_mail(['target@example.com'], u"Hi there", u"Blah șmth ♣")

        self.mock_smtplib.SMTP.assert_called_once_with('my_mailhost')
        self.smtp.quit.assert_called_once_with()

        smtp_args = self.smtp.sendmail.call_args[0]
        raw_msg = smtp_args[2]
        ok_smtp_args = ('me@example.com', ['target@example.com'], raw_msg)
        self.assertEqual(smtp_args, ok_smtp_args)

        from email.parser import Parser
        msg = Parser().parsestr(raw_msg)
        self.assertEqual(msg['From'], 'me@example.com')
        self.assertEqual(msg['To'], 'target@example.com')
        self.assertEqual(msg['Subject'], u"Hi there")
        self.assertEqual(msg.get_payload(decode=True).decode('utf-8'),
                         u"Blah șmth ♣")
