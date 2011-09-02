import unittest2
from selenium import webdriver


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

        from osmpoint import database
        self.db = database.db
        self._ctx = self.app.test_request_context()
        self._ctx.push()
        self.addCleanup(self._ctx.pop)

    def test_about_page(self):
        browser.get('http://127.0.0.1:57909/about')
        self.assertIn("find the code", browser.page_source)
