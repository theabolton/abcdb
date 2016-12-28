from django.test import TestCase

from .models import Song, Instance, Title, Collection


# ====== Model Tests ======

class SongModelTest(TestCase):
    def test_string_representation(self):
        song = Song(digest='0' * 40)
        song.save()
        self.assertEqual(str(song), 'Song ' + str(song.id) + ' (' + song.digest[:7] + ')')


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
        collection = Collection(URL='http://www.smbolton.com/abc.html')
        self.assertEqual(str(collection), collection.URL)


# ====== Project Tests ======

class ProjectTests(TestCase):
    def test_homepage(self):
        """Test that a homepage exists."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
