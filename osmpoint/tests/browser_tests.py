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


def setUpModule():
    global browser
    browser = webdriver.Chrome()
    _start_server()

def tearDownModule():
    browser.quit()
    _stop_server()


def test_wsgiref():
    browser.get('http://127.0.0.1:57909/')
    assert browser.execute_script('return 13') == 13
