import unittest
import itertools
from unittest.mock import Mock, patch
from datetime import datetime

from freezegun import freeze_time

import minilodon.util as util

class UtilTest(unittest.TestCase):
    @freeze_time('01-01-01')
    def test_open(self):
        with patch('builtins.open') as _open, \
             patch('os.path.exists') as _exists:
            _exists.return_value = True
            logfile = util.open_log_file('#test')
            _exists.assert_called_with('#test')
            _open.assert_called_with('#test/01-01-01-#test.log', 'at', 1)
            self.assertEqual(logfile.day, 1)

    def test_wrap_short(self):
        result = list(util.wrap_msg('Hello World!'))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], 'Hello World!')

    def test_wrap_long(self):
        teststr = ' '.join(itertools.repeat("Hello World!", 21))
        result = list(util.wrap_msg(teststr))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1], 'World! Hello World!')
