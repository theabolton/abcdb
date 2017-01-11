# ABCdb main/tests.py
#
# Copyright © 2017 Sean Bolton.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from django.test import TestCase

from .models import Song, Instance, Title, Collection


# ====== Model Tests ======

class SongModelTest(TestCase):
    def test_string_representation(self):
        song = Song(digest='0' * 40)
        song.save()
        self.assertEqual(str(song), 'Song ' + str(song.id))


class InstanceModelTest(TestCase):
    def test_string_representation(self):
        song = Song(digest='1' * 40)
        song.save()
        instance = Instance(song=song, digest='2' * 40,
                            text='M:4/4\nL:1/4\nK:G\nF/G/Afe/d/|fe/d/eE|F/G/Afe/d/|d/G/F/E/FD:|')
        instance.save()
        self.assertEqual(str(instance), 'Instance ' + str(instance.id) + ' (' + instance.digest[:7] + ')')


class TitleModelTest(TestCase):
    def test_string_representation(self):
        title = Title(title='Cast a Bell')
        self.assertEqual(str(title), title.title)


class CollectionModelTest(TestCase):
    def test_string_representation(self):
        collection = Collection(source='http://www.smbolton.com/abc.html')
        self.assertEqual(str(collection), collection.source)


# ====== Project Tests ======

class ProjectTests(TestCase):
    def test_homepage(self):
        """Test that a homepage exists."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
