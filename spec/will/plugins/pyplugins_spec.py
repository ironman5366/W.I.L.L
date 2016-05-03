import os
import will.plugins.pyplugins as pyplugins

from expects import *
from mock import patch, MagicMock
from will.config import FilePath


with describe("will.plugins.pyplugins.PluginFilePath"):
    with describe("get_lib_path method"):
        with it("should return the library path for inclusion in sys.path"):
            file_path = FilePath("some/file/path.py")
            module_path = pyplugins.PluginFilePath(file_path)

            expect(module_path.get_lib_path()).to(
                equal(str(FilePath("some/file")))
            )

    with describe("_file_path method"):
        with it("should return module name if file_path is a python file"):
            file_path = FilePath('some/python/file.py')
            module_path = pyplugins.PluginFilePath(file_path)

            expect(module_path._file_path()).to(
                equal("file")
            )

        with it("should raise IOError if file_path is not a python file"):
            file_path = FilePath('some/python/file.json')
            module_path = pyplugins.PluginFilePath(file_path)

            expect(lambda: module_path._file_path()).to(
                raise_error(IOError)
            )

    with describe("_dir_path method"):
        with it("should return module name if __init__.py exists in directory"):
            file_path = FilePath('some/module')
            init_file = FilePath('__init__.py')
            init_file.exists = MagicMock(return_value=True)
            file_path.join = MagicMock(return_value=init_file)
            module_path = pyplugins.PluginFilePath(file_path)

            expect(module_path._dir_path()).to(
                equal("module")
            )

        with it("should raise IOError if __init__.py does not exist in directory"):
            file_path = FilePath('some/module')
            init_file = FilePath('__init__.py')
            init_file.exists = MagicMock(return_value=False)
            file_path.join = MagicMock(return_value=init_file)
            module_path = pyplugins.PluginFilePath(file_path)

            expect(lambda: module_path._dir_path()).to(
                raise_error(IOError)
            )

    with describe("is_plugin method"):
        with it("should return true if file_path is a python plugin"):
            file_path_a = FilePath('some/module.py')
            file_path_b = FilePath('some/module')
            init_file = FilePath('__init__.py')
            init_file.exists = MagicMock(return_value=True)
            file_path_b.join = MagicMock(return_value=init_file)
            module_path_a = pyplugins.PluginFilePath(file_path_a)
            module_path_b = pyplugins.PluginFilePath(file_path_b)

            expect(module_path_a.is_plugin()).to(be_true)
            expect(module_path_b.is_plugin()).to(be_true)

        with it("should return false if file_path is not a python plugin"):
            file_path_a = FilePath('some/module.json')
            file_path_b = FilePath('some/module')
            init_file = FilePath('__init__.py')
            init_file.exists = MagicMock(return_value=False)
            file_path_b.join = MagicMock(return_value=init_file)
            module_path_a = pyplugins.PluginFilePath(file_path_a)
            module_path_b = pyplugins.PluginFilePath(file_path_b)

            expect(module_path_a.is_plugin()).to(be_false)
            expect(module_path_b.is_plugin()).to(be_false)

    with describe("get_module_name method"):
        with context("when path doesn't exist"):
            with it("should raise IOError"):
                file_path = FilePath("some/path.py")
                file_path.exists = MagicMock(return_value=False)
                module_path = pyplugins.PluginFilePath(file_path)

                expect(lambda: module_path.get_module_name()).to(
                    raise_error(IOError)
                )

        with context("when path exists"):
            with context("and module is a directory"):
                with it("should call ModulePath._dir_path and return basename"):
                    file_path = FilePath("some/path")
                    file_path.exists = MagicMock(return_value=True)
                    file_path.is_directory = MagicMock(return_value=True)
                    module_path = pyplugins.PluginFilePath(file_path)
                    module_path._dir_path = MagicMock(return_value="path")
                    module_path._file_path = MagicMock()

                    expect(module_path.get_module_name()).to(
                        equal("path")
                    )
                    expect(module_path._dir_path.called).to(be_true)
                    expect(module_path._file_path.called).to(be_false)

            with context("and module is a file"):
                with it("should call ModulePath._dir_path and return basename"):
                    file_path = FilePath("some/path.py")
                    file_path.exists = MagicMock(return_value=True)
                    file_path.is_directory = MagicMock(return_value=False)
                    module_path = pyplugins.PluginFilePath(file_path)
                    module_path._dir_path = MagicMock()
                    module_path._file_path = MagicMock(return_value="path")

                    expect(module_path.get_module_name()).to(
                        equal("path")
                    )
                    expect(module_path._dir_path.called).to(be_false)
                    expect(module_path._file_path.called).to(be_true)


