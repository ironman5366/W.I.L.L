from expects import *
from mock import patch
import will.plugins.pyplugins as pyplugins

with describe("will.plugins.pyplugins.get_module"):
    with context("is called with a file path"):
        with context("of an existing file"):
            with context("that is a python plugin"):

                with it("should return with 'echo'"):
                    with patch('os.path.exists', return_value=True):
                        expect(pyplugins.get_module('plugins/echo.py')).to(equal("echo"))

            with context("that is not a python plugin"):

                with it("should raise IOError"):
                    with patch('os.path.exists', return_value=True), \
                         patch('os.path.isdir', return_value=False):
                        expect(lambda: pyplugins.get_module('plugins/not_a_py_module.json')).to(raise_error(IOError))

        with context("of a non existing file"):

                with it("should raise IOError"):
                    with patch('os.path.exists', return_value=False):
                        expect(lambda: pyplugins.get_module('plugins/does_not_exist.py')).to(raise_error(IOError))

    with context("is called with a directory path"):
        with context("of an existing directory"):
            with before.each:
                patch('os.path.isdir', lambda x: True).start()

            with context("with an __init__.py"):
                with it("should return 'my_module'"):
                    with patch('os.path.exists', return_value=True):
                        expect(pyplugins.get_module('plugins/my_module')).to(equal('my_module'))

            with context("witout an __init__.py"):
                with it("should raise IOError"):
                    with patch('os.path.exists', side_effect=[True, False]):
                        expect(lambda: pyplugins.get_module('plugins/my_module')).to(raise_error(IOError))

        with context("directory does not exist"):
            with it("should raise IOerror"):
                with patch('os.path.exists', return_value=False):
                    expect(lambda: pyplugins.get_module('plugins/does_not_exist')).to(raise_error(IOError))
