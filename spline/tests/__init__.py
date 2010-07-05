"""Pylons application test package

This package assumes the Pylons environment is already loaded, such as
when this script is imported from the `nosetests --with-pylons=test.ini`
command.

This module initializes the application via ``websetup`` (`paster
setup-app`) and provides the base testing objects.
"""

# Shiv to make Unicode test docstrings print correctly; forces stderr to be
# utf8 (or whatever LANG says)
import locale, unittest
enc = locale.getpreferredencoding()
def new_writeln(self, arg=None):
    if arg:
        if isinstance(arg, unicode):
            self.write(arg.encode(enc))
        else:
            self.write(arg)
    self.write('\n')
unittest._WritelnDecorator.writeln = new_writeln

from unittest import TestCase

from paste.deploy import loadapp
from paste.fixture import TestApp
from paste.script.appinstall import SetupCommand
from pylons import config, url
from routes.util import URLGenerator

import pylons.test

__all__ = ['environ', 'url', 'TestController']

# Invoke websetup with the current config file
SetupCommand('setup-app').run([config['__file__']])

environ = {}

class TestController(TestCase):

    def __init__(self, *args, **kwargs):
        if pylons.test.pylonsapp:
            wsgiapp = pylons.test.pylonsapp
        else:
            wsgiapp = loadapp('config:%s' % config['__file__'])
        self.app = TestApp(wsgiapp)
        url._push_object(URLGenerator(config['routes.map'], environ))
        TestCase.__init__(self, *args, **kwargs)
