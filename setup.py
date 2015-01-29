#!/usr/bin/env python
# -*- coding: utf-8 -*-
# setup.py
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Setup file for bitmask.
"""
from __future__ import print_function

import hashlib
import sys
import os
import re

if not sys.version_info[0] == 2:
    print("[ERROR] Sorry, Python 3 is not supported (yet). "
          "Try running with python2: python2 setup.py ...")
    exit()

try:
    from setuptools import setup, find_packages
except ImportError:
    from pkg import distribute_setup
    distribute_setup.use_setuptools()
    from setuptools import setup, find_packages

from pkg import utils

import versioneer
versioneer.versionfile_source = 'src/leap/bitmask/_version.py'
versioneer.versionfile_build = 'leap/bitmask/_version.py'
versioneer.tag_prefix = ''  # tags are like 1.2.0
versioneer.parentdir_prefix = 'leap.bitmask-'


# The following import avoids the premature unloading of the `util` submodule
# when running tests, which would cause an error when nose finishes tests and
# calls the exit function of the multiprocessing module.
from multiprocessing import util
assert(util)

setup_root = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(setup_root, "src"))

trove_classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: X11 Applications :: Qt",
    "Intended Audience :: End Users/Desktop",
    ("License :: OSI Approved :: GNU General "
     "Public License v3 or later (GPLv3+)"),
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2.6",
    "Programming Language :: Python :: 2.7",
    "Topic :: Security",
    'Topic :: Security :: Cryptography',
    "Topic :: Communications",
    'Topic :: Communications :: Email',
    'Topic :: Communications :: Email :: Post-Office :: IMAP',
    'Topic :: Internet',
    "Topic :: Utilities",
]

DOWNLOAD_BASE = ('https://github.com/leapcode/bitmask_client/'
                 'archive/%s.tar.gz')
_versions = versioneer.get_versions()
VERSION = _versions['version']
VERSION_FULL = _versions['full']
DOWNLOAD_URL = ""

# get the short version for the download url
_version_short = re.findall('\d+\.\d+\.\d+', VERSION)
if len(_version_short) > 0:
    VERSION_SHORT = _version_short[0]
    DOWNLOAD_URL = DOWNLOAD_BASE % VERSION_SHORT

cmdclass = versioneer.get_cmdclass()


from setuptools import Command


class freeze_debianver(Command):
    """
    Freezes the version in a debian branch.
    To be used after merging the development branch onto the debian one.
    """
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        proceed = str(raw_input(
            "This will overwrite the file _version.py. Continue? [y/N] "))
        if proceed != "y":
            print("He. You scared. Aborting.")
            return
        template = r"""
# This file was generated by the `freeze_debianver` command in setup.py
# Using 'versioneer.py' (0.7+) from
# revision-control system data, or from the parent directory name of an
# unpacked source archive. Distribution tarballs contain a pre-generated copy
# of this file.

version_version = '{version}'
version_full = '{version_full}'
"""
        templatefun = r"""

def get_versions(default={}, verbose=False):
        return {'version': version_version, 'full': version_full}
"""
        subst_template = template.format(
            version=VERSION_SHORT,
            version_full=VERSION_FULL) + templatefun
        with open(versioneer.versionfile_source, 'w') as f:
            f.write(subst_template)


cmdclass["freeze_debianver"] = freeze_debianver
parsed_reqs = utils.parse_requirements()

leap_launcher = 'bitmask=leap.bitmask.app:start_app'

from setuptools.command.develop import develop as _develop


def copy_reqs(path, withsrc=False):
    # add a copy of the processed requirements to the package
    _reqpath = ('leap', 'bitmask', 'util', 'reqs.txt')
    if withsrc:
        reqsfile = os.path.join(path, 'src', *_reqpath)
    else:
        reqsfile = os.path.join(path, *_reqpath)
    print("UPDATING %s" % reqsfile)
    if os.path.isfile(reqsfile):
        os.unlink(reqsfile)
    with open(reqsfile, "w") as f:
        f.write('\n'.join(parsed_reqs))


class cmd_develop(_develop):
    def run(self):
        # versioneer:
        versions = versioneer.get_versions(verbose=True)
        self._versioneer_generated_versions = versions
        # unless we update this, the command will keep using the old version
        self.distribution.metadata.version = versions["version"]

        _develop.run(self)
        copy_reqs(self.egg_path)

cmdclass["develop"] = cmd_develop


class cmd_binary_hash(Command):
    """
    Update the _binaries.py file with hashes for the different helpers.
    This is used from within the bundle.
    """

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self, *args):

        OPENVPN_BIN = os.environ.get('OPENVPN_BIN', None)
        BITMASK_ROOT = os.environ.get('BITMASK_ROOT', None)

        def exit():
            print("Please set environment variables "
                  "OPENVPN_BIN and BITMASK_ROOT pointing to the right path "
                  "to use this command")
            sys.exit(1)

        bin_paths = OPENVPN_BIN, BITMASK_ROOT
        if not all(bin_paths):
            exit()

        if not all(map(os.path.isfile, bin_paths)):
            exit()

        openvpn_bin_hash, bitmask_root_hash = map(
            lambda path: hashlib.sha256(open(path).read()).hexdigest(),
            bin_paths)

        template = r"""
# Hashes for binaries used in Bitmask Bundle.
# This file has been automatically generated by `setup.py hash_binaries`
# DO NOT modify it manually.

OPENVPN_BIN = "{openvpn}"
BITMASK_ROOT = "{bitmask}"
"""
        subst_template = template.format(
            openvpn=openvpn_bin_hash,
            bitmask=bitmask_root_hash)

        bin_hash_path = os.path.join('src', 'leap', 'bitmask', '_binaries.py')
        with open(bin_hash_path, 'w') as f:
            f.write(subst_template)
        print("Binaries hash file %s has been updated!" % (bin_hash_path,))


cmdclass["hash_binaries"] = cmd_binary_hash


# next two classes need to augment the versioneer modified ones

versioneer_build = cmdclass['build']
versioneer_sdist = cmdclass['sdist']


class cmd_build(versioneer_build):
    def run(self):
        versioneer_build.run(self)
        copy_reqs(self.build_lib)


class cmd_sdist(versioneer_sdist):
    def run(self):
        return versioneer_sdist.run(self)

    def make_release_tree(self, base_dir, files):
        versioneer_sdist.make_release_tree(self, base_dir, files)
        copy_reqs(base_dir, withsrc=True)


cmdclass["build"] = cmd_build
cmdclass["sdist"] = cmd_sdist

import platform
_system = platform.system()
IS_LINUX = _system == "Linux"
IS_MAC = _system == "Darwin"

data_files = []
extra_options = {}

if IS_LINUX:
    data_files = [
        ("helpers/", ["pkg/linux/bitmask-root"]),
        ("helpers/policykit/",
            ["pkg/linux/polkit/se.leap.bitmask.policy"]),
        ('/usr/share/applications',
         ['debian/extras-bitmask.desktop']),
    ]

if IS_MAC:
    extra_options["app"] = ['src/leap/bitmask/app.py']
    OPTIONS = {
        'argv_emulation': True,
        'plist': 'pkg/osx/Info.plist',
        'iconfile': 'pkg/osx/bitmask.icns',
    }
    extra_options["options"] = {'py2app': OPTIONS}
    extra_options["setup_requires"] = ['py2app']

    class jsonschema_recipe(object):
        def check(self, dist, mf):
            m = mf.findNode('jsonschema')
            if m is None:
                return None

            # Don't put jsonschema in the site-packages.zip file
            return dict(
                packages=['jsonschema']
            )

    import py2app.recipes
    py2app.recipes.jsonschema = jsonschema_recipe()

setup(
    name="leap.bitmask",
    package_dir={"": "src"},
    version=VERSION,
    cmdclass=cmdclass,
    description=("The Internet Encryption Toolkit: "
                 "Encrypted Internet Proxy and Encrypted Mail."),
    long_description=open('README.rst').read() + '\n\n\n' +
    open('CHANGELOG.rst').read(),
    classifiers=trove_classifiers,
    install_requires=parsed_reqs,
    test_suite='nose.collector',
    tests_require=utils.parse_requirements(
        reqfiles=['pkg/requirements-testing.pip']),
    keywords=('Bitmask, LEAP, client, qt, encryption, '
              'proxy, openvpn, imap, smtp, gnupg'),
    author='The LEAP Encryption Access Project',
    author_email='info@leap.se',
    maintainer='Kali Kaneko',
    maintainer_email='kali@leap.se',
    url='https://bitmask.net',
    download_url=DOWNLOAD_URL,
    license='GPL-3+',
    packages=find_packages(
        'src',
        exclude=['ez_setup', 'setup', 'examples', 'tests']),
    namespace_packages=["leap"],
    package_data={'': ['util/*.txt']},
    include_package_data=True,
    data_files=data_files,
    zip_safe=False,
    platforms="all",
    entry_points={
        'console_scripts': [leap_launcher]
    },
    **extra_options
)
