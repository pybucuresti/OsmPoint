# encoding: utf-8
from email.parser import Parser
import flask
import unittest2

from mock import patch, Mock


class MailTesting(object):

    def __init__(self):
        self._smtp_patch = patch('osmpoint.mails.smtplib')
        self.mock_smtplib = self._smtp_patch.start()
        self.smtp = self.mock_smtplib.SMTP.return_value
        self._messages = []
        self.smtp.sendmail.side_effect = self._sendmail

    def start(self):
        pass

    def stop(self):
        self._smtp_patch.stop()

    def __getitem__(self, i):
        return self._messages[i]

    def _sendmail(self, msg_from, msg_to, raw_msg):
        self._messages.append(Parser().parsestr(raw_msg))



class MailTests(unittest2.TestCase):

    def setUp(self):
        from page_tests import app_for_testing
        self.app, _cleanup = app_for_testing()
        self.addCleanup(_cleanup)
        self._ctx = self.app.test_request_context()
        self._ctx.push()
        self.addCleanup(self._ctx.pop)
        self.app.config['MAIL_SERVER'] = 'my_mailhost'
        self.app.config['MAIL_FROM'] = 'server@example.com'
        self.app.config['MAIL_ADMIN'] = 'me@example.com'
        self.mails = MailTesting()
        self.mails.start()
        self.addCleanup(self.mails.stop)

    def test_send_mail(self):
        from osmpoint.mails import send_mail
        send_mail(['target@example.com'], u"Hi there", u"Blah șmth ♣")

        self.mails.mock_smtplib.SMTP.assert_called_once_with('my_mailhost')
        self.mails.smtp.quit.assert_called_once_with()

        smtp_args = self.mails.smtp.sendmail.call_args[0]
        raw_msg = smtp_args[2]
        ok_smtp_args = ('server@example.com', ['target@example.com'], raw_msg)
        self.assertEqual(smtp_args, ok_smtp_args)

        msg = Parser().parsestr(raw_msg)
        self.assertEqual(msg['From'], 'server@example.com')
        self.assertEqual(msg['To'], 'target@example.com')
        self.assertEqual(msg['Subject'], u"Hi there")
        self.assertEqual(msg.get_payload(decode=True).decode('utf-8'),
                         u"Blah șmth ♣")

    def test_feedback(self):
        from osmpoint.mails import send_feedback_mail

        send_feedback_mail(u"This app is awesome! ♣")

        msg = self.mails[0]
        self.assertEqual(msg['To'], 'me@example.com')
        self.assertEqual(msg['Subject'], u"Feedback")
        self.assertEqual(msg.get_payload(decode=True).decode('utf-8'),
                         u"This app is awesome! ♣")
