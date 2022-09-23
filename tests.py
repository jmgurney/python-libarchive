#!/usr/bin/env python
# coding=utf-8
#
# Copyright (c) 2011, SmartFile <btimby@smartfile.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the organization nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os, unittest, tempfile, random, string, sys
import hashlib
import io
import pathlib
import shutil
import zipfile

from libarchive import Archive, is_archive_name, is_archive
from libarchive.zip import is_zipfile, ZipFile, ZipEntry

FILENAMES = [
    'test1.txt',
    'foo',
    # TODO: test non-ASCII chars.
    #'álért.txt',
]

class MakeTempMixIn:
    def setUp(self):
        self.TMPDIR = tempfile.mkdtemp(suffix='.python-libarchive')
        self.ZIPFILE = 'test.zip'
        self.ZIPPATH = os.path.join(self.TMPDIR, self.ZIPFILE)

    def tearDown(self):
        shutil.rmtree(self.TMPDIR)

        self.TMPDIR = None
        self.ZIPFILE = None
        self.ZIPPATH = None

    def make_temp_files(self):
        if not os.path.exists(self.ZIPPATH):
            for name in FILENAMES:
                with open(os.path.join(self.TMPDIR, name), 'w') as f:
                    f.write(''.join(random.sample(string.ascii_letters, 10)))


    def make_temp_archive(self):
        self.make_temp_files()
        with zipfile.ZipFile(self.ZIPPATH, mode="w") as z:
            for name in FILENAMES:
                z.write(os.path.join(self.TMPDIR, name), arcname=name)


class TestIsArchiveName(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(is_archive_name('foo'), None)
        self.assertEqual(is_archive_name('foo.txt'), None)
        self.assertEqual(is_archive_name('foo.txt.gz'), None)
        self.assertEqual(is_archive_name('foo.tar.gz'), 'tar')
        self.assertEqual(is_archive_name('foo.tar.bz2'), 'tar')
        self.assertEqual(is_archive_name('foo.zip'), 'zip')
        self.assertEqual(is_archive_name('foo.rar'), 'rar')
        self.assertEqual(is_archive_name('foo.iso'), 'iso')
        self.assertEqual(is_archive_name('foo.rpm'), 'cpio')


class TestIsArchiveZip(unittest.TestCase, MakeTempMixIn):
    def setUp(self):
        MakeTempMixIn.setUp(self)
        self.make_temp_archive()

    def tearDown(self):
        MakeTempMixIn.tearDown(self)

    def test_zip(self):
        self.assertEqual(is_archive(self.ZIPPATH), True)
        self.assertEqual(is_archive(self.ZIPPATH, formats=('zip',)), True)
        self.assertEqual(is_archive(self.ZIPPATH, formats=('tar',)), False)


class TestIsArchiveTar(unittest.TestCase):
    def test_tar(self):
        pass


# TODO: incorporate tests from:
# http://hg.python.org/cpython/file/a6e1d926cd98/Lib/test/test_zipfile.py
class TestZipRead(unittest.TestCase, MakeTempMixIn):
    def setUp(self):
        MakeTempMixIn.setUp(self)
        self.make_temp_archive()
        self.f = open(self.ZIPPATH, mode='r')

    def tearDown(self):
        self.f.close()
        MakeTempMixIn.tearDown(self)

    def test_iszipfile(self):
        self.assertEqual(is_zipfile('/dev/null'), False)
        self.assertEqual(is_zipfile(self.ZIPPATH), True)

    def test_iterate(self):
        z = ZipFile(self.f, 'r')
        count = 0
        for e in z:
            count += 1
        self.assertEqual(count, len(FILENAMES), 'Did not enumerate correct number of items in archive.')

    def test_deferred_close_by_archive(self):
        """Test archive deferred close without a stream."""
        z = ZipFile(self.f, 'r')
        self.assertIsNotNone(z._a)
        self.assertIsNone(z._stream)
        z.close()
        self.assertIsNone(z._a)

    def test_deferred_close_by_stream(self):
        """Ensure archive closes self if stream is closed first."""
        z = ZipFile(self.f, 'r')
        stream = z.readstream(FILENAMES[0])
        stream.close()
        # Make sure archive stays open after stream is closed.
        self.assertIsNotNone(z._a)
        self.assertIsNone(z._stream)
        z.close()
        self.assertIsNone(z._a)
        self.assertTrue(stream.closed)

    def test_close_stream_first(self):
        """Ensure that archive stays open after being closed if a stream is
        open. Further, ensure closing the stream closes the archive."""
        z = ZipFile(self.f, 'r')
        stream = z.readstream(FILENAMES[0])
        z.close()
        try:
            stream.read()
        except:
            self.fail("Reading stream from closed archive failed!")
        stream.close()
        # Now the archive should close.
        self.assertIsNone(z._a)
        self.assertTrue(stream.closed)
        self.assertIsNone(z._stream)

    def test_filenames(self):
        z = ZipFile(self.f, 'r')
        names = []
        for e in z:
            names.append(e.filename)
        self.assertEqual(names, FILENAMES, 'File names differ in archive.')

    # ~ def test_non_ascii(self):
    # ~ pass

    def test_extract_str(self):
        pass


class TestZipWrite(unittest.TestCase, MakeTempMixIn):
    def setUp(self):
        MakeTempMixIn.setUp(self)
        self.make_temp_files()
        self.f = open(self.ZIPPATH, mode='w')

    def tearDown(self):
        self.f.close()
        MakeTempMixIn.tearDown(self)

    def test_writepath(self):
        z = ZipFile(self.f, 'w')
        for fname in FILENAMES:
            with open(os.path.join(self.TMPDIR, fname), 'r') as f:
                z.writepath(f)
        z.close()


    def test_writepath_directory(self):
        """Test writing a directory."""
        z = ZipFile(self.f, 'w')
        z.writepath(None, pathname='/testdir', folder=True)
        z.writepath(None, pathname='/testdir/testinside', folder=True)
        z.close()
        self.f.close()

        f = open(self.ZIPPATH, mode='r')
        z = ZipFile(f, 'r')

        entries = z.infolist()

        assert len(entries) == 2
        assert entries[0].isdir()
        z.close()
        f.close()

    def test_writestream(self):
        z = ZipFile(self.f, 'w')
        for fname in FILENAMES:
            full_path = os.path.join(self.TMPDIR, fname)
            i = open(full_path)
            o = z.writestream(fname)
            while True:
                data = i.read(1)
                if not data:
                    break
                o.write(data)
            o.close()
            i.close()
        z.close()

    def test_writestream_unbuffered(self):
        z = ZipFile(self.f, 'w')
        for fname in FILENAMES:
            full_path = os.path.join(self.TMPDIR, fname)
            i = open(full_path)
            o = z.writestream(fname, os.path.getsize(full_path))
            while True:
                data = i.read(1)
                if not data:
                    break
                o.write(data)
            o.close()
            i.close()
        z.close()

    def test_deferred_close_by_archive(self):
        """Test archive deferred close without a stream."""
        z = ZipFile(self.f, 'w')
        o = z.writestream(FILENAMES[0])
        z.close()
        self.assertIsNotNone(z._a)
        self.assertIsNotNone(z._stream)
        o.write('testdata')
        o.close()
        self.assertIsNone(z._a)
        self.assertIsNone(z._stream)
        z.close()


import base64

# ZIP_CONTENT is base64 encoded password protected zip file with password: 'pwd' and following contents:
# unzip -l /tmp/zzz.zip 
#Archive:  /tmp/zzz.zip
#  Length      Date    Time    Name
#---------  ---------- -----   ----
#        9  08-09-2022 19:29   test.txt
#---------                     -------
#        9                     1 file

ZIP_CONTENT='UEsDBAoACQAAAKubCVVjZ7b1FQAAAAkAAAAIABwAdGVzdC50eHRVVAkAA5K18mKStfJid' + \
        'XgLAAEEAAAAAAQAAAAA5ryoP1rrRK5apjO41YMAPjpkWdU3UEsHCGNntvUVAAAACQAAAF' + \
        'BLAQIeAwoACQAAAKubCVVjZ7b1FQAAAAkAAAAIABgAAAAAAAEAAACkgQAAAAB0ZXN0LnR' + \
        '4dFVUBQADkrXyYnV4CwABBAAAAAAEAAAAAFBLBQYAAAAAAQABAE4AAABnAAAAAAA='

ITEM_CONTENT='test.txt\n'
ITEM_NAME='test.txt'

ZIP1_PWD='pwd'
ZIP2_PWD='12345'

class TestProtectedReading(unittest.TestCase, MakeTempMixIn):
    def create_file_from_content(self):
        with open(self.ZIPPATH, mode='wb') as f:
            f.write(base64.b64decode(ZIP_CONTENT))

    def setUp(self):
        MakeTempMixIn.setUp(self)
        self.create_file_from_content()

    def tearDown(self):
        MakeTempMixIn.tearDown(self)

    def test_read_with_password(self):
        z = ZipFile(self.ZIPPATH, 'r', password=ZIP1_PWD)
        self.assertEqual(z.read(ITEM_NAME), bytes(ITEM_CONTENT, 'utf-8'))
        z.close()

    def test_read_without_password(self):
        z = ZipFile(self.ZIPPATH, 'r')
        self.assertRaises(RuntimeError, z.read, ITEM_NAME)
        z.close()

    def test_read_with_wrong_password(self):
        z = ZipFile(self.ZIPPATH, 'r', password='wrong')
        self.assertRaises(RuntimeError, z.read, ITEM_NAME)
        z.close()

class TestProtectedWriting(unittest.TestCase, MakeTempMixIn):
    def create_protected_zip(self):
        z = ZipFile(self.ZIPPATH, mode='w', password=ZIP2_PWD)
        z.writestr(ITEM_NAME, ITEM_CONTENT)
        z.close()

    def setUp(self):
        MakeTempMixIn.setUp(self)
        self.create_protected_zip()

    def tearDown(self):
        MakeTempMixIn.tearDown(self)

    def test_read_with_password(self):
        z = ZipFile(self.ZIPPATH, 'r', password=ZIP2_PWD)
        self.assertEqual(z.read(ITEM_NAME), bytes(ITEM_CONTENT, 'utf-8'))
        z.close()

    def test_read_without_password(self):
        z = ZipFile(self.ZIPPATH, 'r')
        self.assertRaises(RuntimeError, z.read, ITEM_NAME)
        z.close()

    def test_read_with_wrong_password(self):
        z = ZipFile(self.ZIPPATH, 'r', password='wrong')
        self.assertRaises(RuntimeError, z.read, ITEM_NAME)
        z.close()

    def test_read_with_password_list(self):
        z = ZipFile(self.ZIPPATH, 'r', password=[ZIP1_PWD, ZIP2_PWD])
        self.assertEqual(z.read(ITEM_NAME), bytes(ITEM_CONTENT, 'utf-8'))
        z.close()


class TestHighLevelAPI(unittest.TestCase, MakeTempMixIn):
    def setUp(self):
        MakeTempMixIn.setUp(self)
        self.make_temp_archive()

    def tearDown(self):
        MakeTempMixIn.tearDown(self)

    def _test_listing_content(self, f):
        """Test helper capturing file paths while iterating the archive."""
        found = []
        with Archive(f) as a:
            for entry in a:
                found.append(entry.pathname)

        self.assertEqual(set(found), set(FILENAMES))

    def test_open_by_name(self):
        """Test an archive opened directly by name."""
        self._test_listing_content(self.ZIPPATH)

    def test_open_by_named_fobj(self):
        """Test an archive using a file-like object opened by name."""
        with open(self.ZIPPATH, 'rb') as f:
            self._test_listing_content(f)

    def test_open_by_unnamed_fobj(self):
        """Test an archive using file-like object opened by fileno()."""
        with open(self.ZIPPATH, 'rb') as zf:
            with io.FileIO(zf.fileno(), mode='r', closefd=False) as f:
                self._test_listing_content(f)

_defaulthash = 'sha512'

def _readfp(fp):
    while True:
        r = fp.read(64*1024)
        # libarchive returns None on EOF
        if r == b'' or r is None:
            return

        yield r

def _hashfp(fp):
    hash = getattr(hashlib, _defaulthash)()
    for r in _readfp(fp):
        hash.update(r)

    return '%s:%s' % (_defaulthash, hash.hexdigest())


class TestArchive(unittest.TestCase):
    def setUp(self):
        self.fixtures = pathlib.Path(__file__).parent / 'fixtures'

    def test_closed(self):
        fname = self.fixtures / 'testfile.tar.gz'

        with Archive(fname) as arch:
            origfp = arch.f

            hashes = []

            for i in arch:
                if not i.isfile():
                    continue

                with arch.readstream(i.size) as fp:
                    hashes.append(_hashfp(fp))

                self.assertTrue(fp.closed)
                self.assertIsNone(arch._stream)

            self.assertEqual(hashes, [ 'sha512:90f8342520f0ac57fb5a779f5d331c2fa87aa40f8799940257f9ba619940951e67143a8d746535ed0284924b2b7bc1478f095198800ba96d01847d7b56ca465c', 'sha512:7d5768d47b6bc27dc4fa7e9732cfa2de506ca262a2749cb108923e5dddffde842bbfee6cb8d692fb43aca0f12946c521cce2633887914ca1f96898478d10ad3f' ])

        self.assertTrue(arch.f.closed)


if __name__ == '__main__':
    unittest.main()
