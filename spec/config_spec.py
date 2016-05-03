import os
from expects import *
from mock import patch
from will.config import FilePath


with describe("will.config.FilePath"):
    with describe("exists method"):
        with it("returns true if file path exists"):
            with patch('os.path.exists', return_value=True):
                my_path = FilePath("my/file/path.py")
                expect(my_path.exists()).to(be_true)

        with it("returns false if file path does not exist"):
            with patch('os.path.exists', return_value=False):
                my_path = FilePath("my/file/path.py")
                expect(my_path.exists()).to(be_false)

    with describe("__str__ method"):
        with it("should return the file_path string"):
            path_str = os.path.normpath("my/file/path.py")
            my_path = FilePath(path_str)
            expect(str(my_path)).to(equal(path_str))

    with describe("base_name method"):
        with it("should return the base filename"):
            my_path = FilePath("my/file/path.py")
            expect(my_path.base_name()).to(equal("path.py"))

    with describe("is_directory method"):
        with it("should return true if file path is a directory"):
            with patch('os.path.isdir', return_value=True):
                my_path = FilePath("my/file/path")
                expect(my_path.is_directory()).to(be_true)

        with it("should return false if file path is not a directory"):
            with patch('os.path.isdir', return_value=False):
                my_path = FilePath("my/file/path.py")
                expect(my_path.is_directory()).to(be_false)

    with describe("abs_path method"):
        with it("should return the absolute path to the file/directory"):
            # Unfortunately this is a hard test to write as the result is
            # going to be OS specific.  If anyone has a better way to do
            # this, I'd love to learn about it.  -Brent Taylor
            path_str = "my/file/path.py"
            my_path = FilePath("my/file/path.py")
            expect(str(my_path.abs_path())).to(equal(os.path.abspath(path_str)))

    with describe("join method"):
        with it("should join two paths and return the result as a new FilePath"):
            path_a = FilePath("my/file/path")
            path_b = FilePath("file.py")
            expect(str(path_a.join(path_b))).to(
                equal(os.path.normpath("my/file/path/file.py"))
            )