# encoding: utf-8
from time import sleep
import unittest2
try:
    from selenium import webdriver
except ImportError:
    from nose import SkipTest
    raise SkipTest

from osmpoint import database


def _start_server():
    from cherrypy.wsgiserver import CherryPyWSGIServer
    from wsgiref.simple_server import demo_app
    from threading import Thread
    import time

    global _httpd
    _httpd = CherryPyWSGIServer(('127.0.0.1', 57909), demo_app,
                                server_name='osmpoint-test-http')
    Thread(target=_httpd.start).start()

    for t in xrange(100):
        if _httpd.ready:
            break
        time.sleep(.01)
    else:
        raise ValueError("CherryPy server has not started")

def _stop_server():
    _httpd.stop()

def _set_app(app):
    _httpd.wsgi_app = app

def js(cmd):
    return browser.execute_script("return (" + cmd + ")")

def css(selector):
    return browser.find_element_by_css_selector(selector)


def setUpModule():
    global browser
    browser = webdriver.Chrome()
    _start_server()

def tearDownModule():
    browser.quit()
    _stop_server()


class BrowsingTest(unittest2.TestCase):

    def setUp(self):
        from page_tests import app_for_testing
        self.app, _cleanup = app_for_testing()
        self.addCleanup(_cleanup)
        _set_app(self.app)

        self.db = database.db
        self._ctx = self.app.test_request_context()
        self._ctx.push()
        self.addCleanup(self._ctx.pop)

    def test_about_page(self):
        browser.get('http://127.0.0.1:57909/about')
        self.assertIn("find the code", browser.page_source)

    def test_homepage_marker_balloon(self):
        point_id = database.add_point(44.4324, 26.1020, 'S.A.L.T.',
                                      None, 'pub', 'my-open-id')
        browser.get('http://127.0.0.1:57909/')
        js("$('img', M.collections['Locations'].layer.markers[0]"
           ".icon.imageDiv)[0]").click()
        self.assertIn("S.A.L.T. (pub)", js("$('.olPopupContent').text()"))

    def test_feedback(self):
        from mail_tests import MailTesting
        self.mails = MailTesting()
        self.mails.start()
        self.addCleanup(self.mails.stop)

        browser.get('http://127.0.0.1:57909/')
        browser.find_element_by_link_text('Feedback').click()
        js(u"$('form[name=feedback] textarea').val('fix your damn bugș ♣')")
        js("$('form[name=feedback]')[0]").submit()
        sleep(1)

        # TODO must be logged in

        msg = self.mails[0]
        self.assertEqual(msg.get_payload(decode=True).decode('utf-8'),
                         u"fix your damn bugș ♣")
