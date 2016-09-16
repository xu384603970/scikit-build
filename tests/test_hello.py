#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""test_hello
----------------------------------

Tries to build and test the `hello` sample project.
"""

import glob
import os
import pytest
import tarfile

from skbuild.constants import SKBUILD_DIR
from skbuild.exceptions import SKBuildError
from skbuild.platform_specifics import get_platform
from skbuild.utils import push_dir

from zipfile import ZipFile

from . import project_setup_py_test
from . import (_copy_dir, _tmpdir, SAMPLES_DIR)


def test_hello_builds():
    with push_dir():

        @project_setup_py_test("hello", ["build"])
        def run():
            pass

        # Check that a project can be build twice in a row
        # See issue scikit-build#120
        tmp_dir = run()[0]

        @project_setup_py_test("hello", ["build"], tmp_dir=tmp_dir)
        def another_run():
            pass

        another_run()


@pytest.mark.parametrize("generator_args",
                         [
                             ["-G", "invalid"],
                             ["--", "-G", "invalid"],
                             ["-G", get_platform().default_generators[0]],
                             ["--", "-G", get_platform().default_generators[0]],
                         ])
def test_hello_builds_with_generator(generator_args):
    with push_dir():

        build_args = ["build"]
        build_args.extend(generator_args)

        @project_setup_py_test("hello", build_args)
        def run():
            pass

        failed = False
        message = ""
        try:
            run()
        except SystemExit as e:
            failed = isinstance(e.code, SKBuildError)
            message = str(e)

        if 'invalid' in generator_args:
            assert failed
            assert "Could not get working generator for your system." \
                   "  Aborting build." in message
        else:
            assert not failed


# @project_setup_py_test("hello", ["test"])
# def test_hello_works():
#     pass


@project_setup_py_test("hello", ["sdist"])
def test_hello_sdist():
    sdists_tar = glob.glob('dist/*.tar.gz')
    sdists_zip = glob.glob('dist/*.zip')
    assert sdists_tar or sdists_zip

    expected_content = [
        'hello-1.2.3/CMakeLists.txt',
        'hello-1.2.3/bonjour/__init__.py',
        'hello-1.2.3/hello/_hello.cxx',
        'hello-1.2.3/hello/CMakeLists.txt',
        'hello-1.2.3/hello/__init__.py',
        'hello-1.2.3/hello/__main__.py',
        'hello-1.2.3/setup.py',
        'hello-1.2.3/PKG-INFO'
    ]

    member_list = None
    if sdists_tar:
        expected_content.extend([
            'hello-1.2.3',
            'hello-1.2.3/bonjour',
            'hello-1.2.3/hello'
        ])
        member_list = tarfile.open('dist/hello-1.2.3.tar.gz').getnames()

    elif sdists_zip:
        member_list = ZipFile('dist/hello-1.2.3.zip').namelist()

    assert expected_content and member_list
    assert sorted(expected_content) == sorted(member_list)


@project_setup_py_test("hello", ["bdist_wheel"])
def test_hello_wheel():
    whls = glob.glob('dist/*.whl')
    assert len(whls) == 1
    assert not whls[0].endswith('-none-any.whl')


@pytest.mark.parametrize("dry_run", ['with-dry-run', 'without-dry-run'])
def test_hello_clean(dry_run, capfd):
    with push_dir():

        dry_run = dry_run == 'with-dry-run'

        @project_setup_py_test("hello", ["build"])
        def run_build():
            pass

        tmp_dir = run_build()[0]

        assert tmp_dir.join(SKBUILD_DIR).exists()

        # XXX Since using capfd.disabled() context manager prevents
        # the output from being captured atfer it exits, we display
        # a separator allowing to differentiate the build and clean output.
        print("<<-->>")

        clean_args = ["clean"]
        if dry_run:
            clean_args.append("--dry-run")

        @project_setup_py_test("hello", clean_args, tmp_dir=tmp_dir)
        def run_clean():
            pass

        run_clean()

        if not dry_run:
            assert not tmp_dir.join(SKBUILD_DIR).exists()
        else:
            assert tmp_dir.join(SKBUILD_DIR).exists()

        build_out, clean_out = capfd.readouterr()[0].split('<<-->>')
        assert 'Build files have been written to' in build_out
        assert 'Build files have been written to' not in clean_out


def test_hello_cleans(capfd):
    with push_dir():

        tmp_dir = _tmpdir("test_hello_cleans")

        _copy_dir(tmp_dir, os.path.join(SAMPLES_DIR, "hello"))

        @project_setup_py_test("hello", ["build"], tmp_dir=tmp_dir)
        def run_build():
            pass

        @project_setup_py_test("hello", ["clean"], tmp_dir=tmp_dir)
        def run_clean():
            pass

        # Check that a project can be cleaned twice in a row
        run_build()
        print("<<-->>")
        run_clean()
        print("<<-->>")
        run_clean()

    _, clean1_out, clean2_out = \
        capfd.readouterr()[0].split('<<-->>')

    clean1_out = clean1_out.strip()
    clean2_out = clean2_out.strip()

    assert "running clean" == clean1_out.splitlines()[0]
    assert "removing '_skbuild{}cmake-install'".format(os.path.sep) \
           == clean1_out.splitlines()[1]
    assert "removing '_skbuild{}cmake-build'".format(os.path.sep) \
           == clean1_out.splitlines()[2]
    assert "removing '_skbuild'" == clean1_out.splitlines()[3]

    assert "running clean" == clean2_out
