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

import json

from django.test import TestCase, tag

from .models import Song, Instance, Title, Collection, CollectionInstance


def _create_instance():
    song = Song(digest='1' * 40)
    song.save()
    first_title = Title(title='Cast a Bell')
    first_title.save()
    first_title.songs.add(song)
    instance = Instance(song=song, digest='2' * 40, first_title=first_title,
                        text='X:1\nT:Cast a Bell\nM:4/4\nL:1/4\nK:G\n'
                             'F/G/Afe/d/|fe/d/eE|F/G/Afe/d/|d/G/F/E/FD:|')
    instance.save()
    return instance


def _create_simple_data():
    """Creates a simple set of data suitable for testing several of the views:

                             Collection1
                            /
      Title1       Instance1 - Collection2
            \     /         \
    Title2 - Song1           first_title:Title1
            /     \
      Title3       Instance2 - first_title:Title2
                            \
                             Collection3

    Returns a dict with object names (as above) as keys, and objects as values."""
    import datetime

    data = {}
    song = Song(digest='1' * 40)
    song.save()
    data['Song1'] = song
    for i in range(1, 4):
        title = Title(title='Title{}'.format(i))
        title.save()
        title.songs.add(song)
        data[title.title] = title
        collection = Collection(source='Collection{}'.format(i),
                                date=datetime.datetime.now(datetime.timezone.utc),
                                new_songs=1 if i == 1 else 0,
                                existing_songs=0 if i == 1 else 1,
                                new_instances=1 if i != 2 else 0,
                                existing_instances=0 if i != 2 else 1)
        collection.save()
        data[collection.source] = collection
    instance1 = Instance(song=song, digest='2' * 40, first_title=data['Title1'],
                        text='T:Title1\nT:Title2\nM:4/4\nL:1/4\nK:G\n'
                             'F/G/Afe/d/|fe/d/eE|F/G/Afe/d/|d/G/F/E/FD:|')
    instance1.save()
    data['Instance1'] = instance1
    instance2 = Instance(song=song, digest='3' * 40, first_title=data['Title2'],
                        text='T:Title2\nT:Title3\nM:4/4\nL:1/4\nK:G\n'
                             'F/G/Afe/d/|fe/d/eE|F/G/Afe/d/|d/G/F/E/FD:|')
    instance2.save()
    data['Instance2'] = instance2
    def link_collection(coll, inst):
        CollectionInstance(collection=coll, instance=inst, X=1, line_number=1).save()
    link_collection(data['Collection1'], instance1)
    link_collection(data['Collection2'], instance1)
    link_collection(data['Collection3'], instance2)
    return data


# ========== Model Tests ==========

class SongModelTest(TestCase):
    def test_string_representation(self):
        song = Song(digest='0' * 40)
        song.save()
        self.assertEqual(str(song), 'Song ' + str(song.id))


class InstanceModelTest(TestCase):
    def test_string_representation(self):
        instance = _create_instance()
        self.assertEqual(str(instance), 'Instance ' + str(instance.id))


class TitleModelTest(TestCase):
    def test_string_representation(self):
        title = Title(title='Cast a Bell')
        self.assertEqual(str(title), title.title)


class CollectionModelTest(TestCase):
    def test_string_representation(self):
        collection = Collection(source='http://www.smbolton.com/abc.html')
        self.assertEqual(str(collection), collection.source)


class CollectionInstanceModelTest(TestCase):
    def test_string_representation(self):
        import datetime

        instance = _create_instance()
        collection = Collection(source='http://www.smbolton.com/abc.html',
                                date=datetime.datetime.now(datetime.timezone.utc))
        collection.save()
        collectioninstance = CollectionInstance(collection=collection, instance=instance)
        self.assertEqual(str(collectioninstance), 'CollectionInstance {}:{}'.format(
            collectioninstance.collection_id, collectioninstance.instance_id))


# ========== Project Tests ==========

class ProjectTests(TestCase):
    def test_homepage(self):
        """Test that a homepage exists."""
        response = self.client.get('/')
        #print(response.content)
        self.assertEqual(response.status_code, 200)


class AppsTests(TestCase):
    def test_apps(self):
        """Umm, make sure apps.py loads?"""
        import main.apps


# ========== View Tests ==========

class UtilityFunctionTests(TestCase):
    def test__generate_instance_name(self):
        from main.views import _generate_instance_name

        instance = _create_instance()
        self.assertEqual(_generate_instance_name(instance),
                         'Instance {} "{}" of Song {}'.format(
                             instance.id, instance.first_title.title, instance.song.id))
        Title.objects.update(title='Long Title ' * 5)
        instance = Instance.objects.all()[0]  # refresh cache
        self.assertEqual(
            _generate_instance_name(instance),
            'Instance {} "Long Title Long Title Long Title Long Title Lon..." of Song {}'.format(
                instance.id, instance.song.id))

    def test_remove_diacritics(self):
        import unicodedata
        from main.views import remove_diacritics

        self.assertEqual(remove_diacritics(''), '')
        self.assertEqual(remove_diacritics('abcdefg'), 'abcdefg')
        self.assertEqual(remove_diacritics('äbçdèfĝhīj́'), 'abcdefghij')


class ajax_graph_viewTests(TestCase):
    def decode_json(self, response):
        try:
            return json.loads(response.content.decode('utf-8'))
        except json.JSONDecodeError:
            self.fail('response was not valid JSON')

    def test_ajax_graph_view(self):
        # create simple test graph:
        data = _create_simple_data()
        # add a few additional nodes (existing nodes are parenthesized):
        #         (Song1)             (Collection1)
        #        /                   /
        #  Title4 - Song2 - Instance3 - first_title:Title4
        song = Song(digest='2' * 40)
        song.save()
        data['Song2'] = song
        title = Title(title='Title4')
        title.save()
        title.songs.add(song)
        title.songs.add(data['Song1'])
        data[title.title] = title
        instance = Instance(song=song, digest='4' * 40, first_title=data['Title4'],
                        text='T:Title1\nT:Title2\nM:4/4\nL:1/4\nK:G\n'
                             'A/B/cfe/d/|fe/d/eE|F/G/Afe/d/|d/G/F/E/FD:|')
        instance.save()
        data['Instance3'] = instance
        CollectionInstance(collection=data['Collection1'], instance=instance, X=2,
                           line_number=30).save()
        # An HTML request to the Ajax URL should return a redirect to the base graph URL.
        response = self.client.get('/ajax/graph/s1/')
        self.assertRedirects(response, '/graph/s1/')
        # An Ajax request with an invalid node id should return a JSON error object.
        response = self.client.get('/ajax/graph/s999999999/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEquals(response._headers['content-type'][1], 'application/json')
        response_json = self.decode_json(response)
        self.assertTrue(response_json['error'])
        self.assertIn('not found', response_json['description'])
        # An Ajax request with valid node id should return the graph for that node.
        response = self.client.get('/ajax/graph/s{}/'.format(data['Song1'].id),
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEquals(response._headers['content-type'][1], 'application/json')
        response_json = self.decode_json(response)
        # a quick check for a specific set of keys:
        #   self.assertCountEqual(response_json, { 'nodes': True, 'links': True })
        self.assertIsNotNone(response_json.get('nodes'), "JSON does not contain 'nodes' object")
        self.assertIsNotNone(response_json.get('links'), "JSON does not contain 'links' object")
        # check that the graph is correct
        response_json['nodes'].sort(key=lambda n: n['id'] + '|' + n.get('title', ''))
        self.assertListEqual(response_json['nodes'],
                             [{'id': 'i1', 'title': 'Title1'},
                              {'id': 'i2', 'title': 'Title2'},
                              {'id': 'i3', 'title': 'Title4'},
                              {'id': 's1'},
                              {'id': 's2'},
                              {'id': 't1', 'title': 'Title1'},
                              {'id': 't2', 'title': 'Title2'},
                              {'id': 't3', 'title': 'Title3'},
                              {'id': 't4', 'title': 'Title4'}])
        response_json['links'].sort(key=lambda n: n['source'] + '|' + n['target'])
        self.assertListEqual(response_json['links'],
                             [{'source': 's1', 'target': 'i1'},
                              {'source': 's1', 'target': 'i2'},
                              {'source': 's2', 'target': 'i3'},
                              {'source': 't1', 'target': 's1'},
                              {'source': 't2', 'target': 's1'},
                              {'source': 't3', 'target': 's1'},
                              {'source': 't4', 'target': 's1'},
                              {'source': 't4', 'target': 's2'}])


class CollectionViewTest(TestCase):
    def test_CollectionView(self):
        import datetime

        collection = Collection(source='Collection 1',
                                date=datetime.datetime.now(datetime.timezone.utc))
        collection.save()
        instance = _create_instance()
        collectioninstance = CollectionInstance(collection=collection, instance=instance,
                                                X=1, line_number=1)
        collectioninstance.save()
        response = self.client.get('/collection/{}/'.format(collection.id))
        self.assertContains(response, 'Collection source: Collection 1')
        self.assertContains(response, '0 new songs')
        self.assertContains(response, 'There is one song')
        self.assertContains(response, 'Cast a Bell')


class CollectionsViewTests(TestCase):
    def test_CollectionsView(self):
        import datetime

        date = datetime.datetime.now(datetime.timezone.utc)
        Collection.objects.bulk_create([
            Collection(source='Collection 1', date=date),
            Collection(source='Collection 2', date=date),
        ])
        response = self.client.get('/collections/')
        self.assertContains(response, 'There are two collections')
        self.assertContains(response, 'Collection 1')
        self.assertContains(response, 'Collection 2')


class graph_viewTests(TestCase):
    def test_graph_view(self):
        # create simple test graph:
        data = _create_simple_data()
        # A request with an invalid node id should return a simple message and a link to the
        # search page.
        response = self.client.get('/graph/t999999999/')
        self.assertContains(response, 'not found.')
        self.assertContains(response, '<a href="/search/">')
        # A request with a valid node id should serve the HTML for the client-side tune graph
        # explorer.
        response = self.client.get('/graph/s{}/'.format(data['Song1'].id))
        self.assertContains(response, '<div id="graph">')
        self.assertContains(response, '<script src="/static/graph.js"')


class InstanceViewTests(TestCase):
    def test_InstanceView(self):
        data = _create_simple_data()
        response = self.client.get('/instance/{}/'.format(data['Instance1'].id))
        # check song titles (with the closing '>' from titles link, so we don't match the other
        # occurances)
        self.assertContains(response, '>Title1')
        self.assertContains(response, '>Title2')
        # check for other instances
        self.assertContains(response, 'Instance {} &quot;'.format(data['Instance2'].id))
        # check for ABC text within javascript
        self.assertContains(response, 'M:4/4\\u000AL:1/4\\u000A')
        # check for ABC text within page
        self.assertContains(response, 'M:4/4\nL:1/4\n')
        # check for download link
        self.assertContains(response, '<form role="form" action="/download/{}/" method="post">'
                                          .format(data['Instance1'].id))
        # check for collections
        self.assertContains(response, 'Collection1')
        self.assertContains(response, 'Collection2')


class SongViewTests(TestCase):
    def test_SongView(self):
        data = _create_simple_data()
        response = self.client.get('/song/{}/'.format(data['Song1'].id))
        self.assertContains(response, 'Title1')
        self.assertContains(response, 'Title2')
        self.assertContains(response, 'Title3')
        self.assertContains(response, 'Instance 1 &quot;')
        self.assertContains(response, 'Instance 2 &quot;')
        self.assertContains(response, 'Collection1')
        self.assertContains(response, 'Collection2')


class TitleViewTests(TestCase):
    def test_TitleView(self):
        data = _create_simple_data()
        response = self.client.get('/title/{}/'.format(data['Title2'].id))
        self.assertContains(response, 'Title: Title2')
        self.assertContains(response, '1 song has this title.')
        self.assertContains(response, 'Song {}'.format(data['Song1'].id))


class TitlesViewTests(TestCase):
    def test_TitlesView(self):
        Title.objects.bulk_create([
            Title(title='Title 1'),
            Title(title='Title 2'),
        ])
        response = self.client.get('/titles/')
        self.assertContains(response, 'There are two titles')
        self.assertContains(response, 'Title 1')
        self.assertContains(response, 'Title 2')


class title_searchTests(TestCase):
    def test_title_search(self):
        Title.objects.bulk_create([
            Title(title='Alawondahula'),
            Title(title='Ecky Ecky Ecky Patang'),
        ])
        response = self.client.get('/search/')
        self.assertContains(response, 'String to search for in titles')
        response = self.client.get('/search/', { 'title': 'xxx' })
        self.assertContains(response, "No titles matching 'xxx' were found.")
        response = self.client.get('/search/', { 'title': 'won' })
        self.assertContains(response, "1 title matching 'won'")
        self.assertContains(response, 'Alawondahula')
        response = self.client.get('/search/?title=')
        self.assertContains(response, 'There was a problem getting the search string.')


class statsTests(TestCase):
    def test_stats(self):
        data = _create_simple_data()
        response = self.client.get('/stats/')
        # 'The database currently contains:'
        self.assertContains(response, '1 song')
        self.assertContains(response, '2 song instances')
        self.assertContains(response, '3 titles')
        self.assertContains(response, '3 collections')
        # miscellaneous statistics
        self.assertContains(response, 'Instances vs. songs deduplication amount: 50.00%')
        self.assertContains(response, 'least one new instance, is 2.')
        self.assertContains(response, 'vs. database instances deduplication amount: 0.00%')
        # instances-per-song histo (in a comment created for this test)
        self.assertContains(response, 'inst_per_song_histo 2:1| ')
        # collections-per-instance histo
        self.assertContains(response, 'coll_per_inst_histo 2:1|1:1| ')


class downloadTests(TestCase):
    def test_download(self):
        instance = _create_instance()
        response = self.client.get('/download/{}/'.format(instance.id))
        self.assertEquals(response.content, instance.text.encode('utf-8'))


# ========== Upload Tests ==========

@tag('upload')
class uploadTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User, Permission

        # create users
        User.objects.create_superuser('admin', 'none@example.com', password='a1b2c3d4')
        user = User.objects.create_user('testuser', password='password')
        user.first_name='Test'
        user.last_name='User'
        user.save()
        perm = Permission.objects.get(name='Can upload files')
        user.user_permissions.add(perm)

    def test_form(self):
        """Check that the upload form renders properly on GET."""
        from django.contrib.auth.models import User

        # should receive redirect if not logged in
        response = self.client.get('/upload/')
        self.assertRedirects(response, '/login/?next=/upload/')
        # if logged in as normal user, URL fetch should not be available
        self.client.force_login(User.objects.get(username='testuser'))
        response = self.client.get('/upload/')
        self.assertContains(response, 'You may upload an ABC file')
        self.assertContains(response, 'File to Upload:')
        self.assertContains(response, 'ABC Notation to Submit:')
        self.assertNotContains(response, 'URL to Fetch:')
        self.client.logout()
        # if logged in as staff, URL fetch should be available
        self.client.force_login(User.objects.get(username='admin'))
        response = self.client.get('/upload/')
        self.assertContains(response, 'URL to Fetch:')

    def test_malformed_upload_requests(self):
        """Exercise the upload request validation code."""
        from django.contrib.auth.models import User

        self.client.force_login(User.objects.get(username='testuser'))
        # unexpected method PUT
        response = self.client.put('/upload/')
        # -FIX- Huh, just falls through to GET response

    def test_upload_manual_entry_valid(self):
        """Test upload of ABC from manual entry textarea."""
        from urllib.parse import urlencode
        from django.contrib.auth.models import User

        self.client.force_login(User.objects.get(username='testuser'))
        response = self.client.post('/upload/',
                                    urlencode({'text': 'X:1\nT:Title\nK:G\nabcdbef\n\n'}),
                                    content_type='application/x-www-form-urlencoded')
        self.assertContains(response, 'processing complete.')
        self.assertContains(response, '1 new song')
        self.assertContains(response, "Adding new collection 'entry testuser")
        # check that tune with no title is handled properly
        response = self.client.post('/upload/',
                                    urlencode({'text': 'X:2\nK:G\nabcdbef\n\n'}),
                                    content_type='application/x-www-form-urlencoded')
        self.assertContains(response, "Adding new title '&lt;untitled&gt;'")
        self.assertRegex(response.content, b"Adding new collection 'entry testuser.*:\d\d'")
        # ...and a tune with more than one title
        response = self.client.post('/upload/',
                                    urlencode({'text': 'X:3\nT:Title1\nT:Title2\nK:G\nabc\n\n'}),
                                    content_type='application/x-www-form-urlencoded')
        self.assertContains(response, "Adding new title 'Title2'")

    def test_upload_manual_entry_invalid(self):
        """Exercise the manual ABC entry validation code."""
        from urllib.parse import urlencode
        from django.contrib.auth.models import User

        self.client.force_login(User.objects.get(username='testuser'))
        response = self.client.post('/upload/', 'text',
                                    content_type='application/x-www-form-urlencoded')
        self.assertContains(response, 'The submitted form was invalid')
        # can't get 100% coverage of invalid forms because of redundant checks

    def test_upload_file_valid(self):
        """Test upload of an ABC file."""
        from django.contrib.auth.models import User
        from django.utils.six import StringIO

        self.client.force_login(User.objects.get(username='testuser'))
        file = StringIO('X:2\nT:Fragment\nK:Bb\nbdfdbdfd|b8||\n\n')
        response = self.client.post('/upload/', { 'file': file })
        self.assertContains(response, 'processing complete.')
        self.assertContains(response, '1 new song')
        self.assertContains(response, "Adding new collection 'upload testuser")
        # upload it again to exercise 'existing' branches
        file.seek(0)
        response = self.client.post('/upload/', { 'file': file })
        self.assertContains(response, 'processing complete.')
        self.assertContains(response, '1 existing song')
        self.assertContains(response, "Adding new collection 'upload testuser")

    def test_upload_file_invalid(self):
        """Exercise the file upload validation code."""
        from django.contrib.auth.models import User
        from django.utils.six import StringIO

        # invalid file upload
        self.client.force_login(User.objects.get(username='testuser'))
        response = self.client.post('/upload/', { 'file': 'foo' })
        self.assertContains(response, 'Bad form')
        # empty file
        file = StringIO('')
        response = self.client.post('/upload/', { 'file': file })
        self.assertContains(response, 'The file upload was invalid')

    @tag('fetch')
    def test_upload_url_fetch_valid(self):
        """Test fetching ABC from a URL."""
        from urllib.parse import urlencode
        from django.contrib.auth.models import User

        # test URL fetch from non-staff user
        self.client.force_login(User.objects.get(username='testuser'))
        TEST_URL = 'https://github.com/smbolton/abcdb/raw/master/docs/Cast_A_Bell.abc'
        response = self.client.post(
                       '/upload/',
                       urlencode({'url': TEST_URL}),
                       content_type='application/x-www-form-urlencoded')
        self.assertContains(response, 'only available to administrators')
        self.client.logout()
        # test URL fetch from staff user
        self.client.force_login(User.objects.get(username='admin'))
        response = self.client.post(
                       '/upload/',
                       urlencode({'url': TEST_URL}),
                       content_type='application/x-www-form-urlencoded')
        self.assertContains(response, 'processing complete.')
        self.assertContains(response, '1 new song')
        self.assertContains(response, "Adding new collection 'fetch admin")

    @tag('fetch')
    def test_upload_url_fetch_invalid(self):
        """Exercise the URL fetch validation code."""
        from urllib.parse import urlencode
        from django.contrib.auth.models import User

        # fetch of invalid URL
        self.client.force_login(User.objects.get(username='admin'))
        response = self.client.post(
                       '/upload/',
                       urlencode({'url': 'foo'}),
                       content_type='application/x-www-form-urlencoded')
        self.assertContains(response, 'Please enter a valid URL.')
        # fetch of nonexistent URL
        response = self.client.post(
                       '/upload/',
                       urlencode({'url': 'http://smbolton.com/nonexistent'}),
                       content_type='application/x-www-form-urlencoded')
        self.assertContains(response, 'URL fetch failed')
        self.assertContains(response, '404 Client Error: Not Found')
        # fetch of too-large file
        TOO_BIG_FILE = 'http://smbolton.com/whysynth/whysynth-20120903.tar.bz2'
        response = self.client.post(
                       '/upload/',
                       urlencode({'url': TOO_BIG_FILE}),
                       content_type='application/x-www-form-urlencoded')
        self.assertContains(response, 'The fetched file is too long.')

    def test_upload_parse_errors_and_warnings(self):
        """Test that parse errors and warnings are reported correctly."""
        from urllib.parse import urlencode
        from django.contrib.auth.models import User

        self.client.force_login(User.objects.get(username='testuser'))
        BAD_TUNES = ('X:1\nT:Tune with error\nK:F\nab+cd+\n\n'
                     'X:2\nT:Tune with warning (no newlines at end)\nK:G\nabcdefg')
        response = self.client.post('/upload/',
                                    urlencode({'text': BAD_TUNES}),
                                    content_type='application/x-www-form-urlencoded')
        self.assertContains(response, 'processing complete.')
        self.assertContains(response, '2 new songs')
        self.assertContains(response, '1 instance with errors')
        self.assertContains(response, '1 instance with warnings')
        self.assertContains(response, "Adding new collection 'entry testuser")


# ========== ABC Parser Tests ==========

@tag('parser')
class TuneTests(TestCase):
    """Tests for the Tune class."""

    def test_string_representation(self):
        """Manually stuff a ``Tune``, then make sure ``__str__`` works. (``__str__`` probably
        ought to be ``__repr__`` instead.)"""
        from main.abcparser import Tune
        tune = Tune()
        tune.full_tune = ['T:Title1', 'T:Title2', 'K:G', 'abcd', '']
        tune.X = 22
        tune.line_number = 33
        tune.T = ['Title1', 'Title2']
        tune.canonical = [{'sort': '3K000000', 'line': 'K:G'},
                          {'sort': '5_000001', 'line': 'abcd'},
                          {'sort': '5_000002', 'line': ''}]
        self.assertEqual(str(tune),
                         'X: 22\nT: Title1\nT: Title2\nF| T:Title1\nF| T:Title2\n'
                         'F| K:G\nF| abcd\nF| \nD| 3K000000 K:G\nD| 5_000001 abcd\nD| 5_000002 \n')

    def test_Tune_API(self):
        """Test the Tune class methods."""
        from main.abcparser import Tune
        tune = Tune()
        tune.X = 44
        tune.line_number = 55
        for iscanon, line in [(False, 'T:Title1'), (False, 'T:Title2'), (True, 'M:4/4'),
                              (True, 'K:G'), (True, 'abcd'), (True, '')]:
            if line.startswith('T:'):
                tune.T.append(line[2:])
            tune.full_tune_append(line)
            if iscanon:
                if line[1:2] == ':':
                    field = line[:1]
                else:
                    field = 'body'
                tune.canonical_append(field, line)
        self.assertEqual(str(tune),
                         'X: 44\nT: Title1\nT: Title2\nF| T:Title1\nF| T:Title2\nF| M:4/4\n'
                         'F| K:G\nF| abcd\nF| \nD| 2M000000 M:4/4\nD| 3K000001 K:G\n'
                         'D| 5_000002 abcd\nD| 5_000003 \n')


@tag('parser')
class ParserUtilityTests(TestCase):
    def test_decode_abc_text_string(self):
        from main.abcparser import decode_abc_text_string
        self.assertEqual(decode_abc_text_string(''), '')
        self.assertEqual(decode_abc_text_string('&Ouml;'), 'Ö')
        self.assertEqual(decode_abc_text_string('\\u0041'), 'A')
        self.assertEqual(decode_abc_text_string('\\U00000041'), 'A')
        self.assertEqual(decode_abc_text_string('\\u00A0'), ' ')         # nbsp -> space
        self.assertEqual(decode_abc_text_string('\\u000A'), '\\u000A')   # don't sub controls
        self.assertEqual(decode_abc_text_string('\\"A'), 'Ä')
        self.assertEqual(decode_abc_text_string('\\\\u0041'), '\\u0041') # double backslash

    def test_split_off_comment(self):
        from main.abcparser import split_off_comment
        self.assertEqual(split_off_comment(b''), (b'', None))
        self.assertEqual(split_off_comment(b'Aa bb cc dd.'), (b'Aa bb cc dd.', None))
        self.assertEqual(split_off_comment(b'Aa bb % cc dd.'), (b'Aa bb', b'% cc dd.'))
        self.assertEqual(split_off_comment(b'Aa bb \\% cc dd.'), (b'Aa bb \\% cc dd.', None))
        self.assertEqual(split_off_comment(b'Aa bb \\\\% cc dd.'), (b'Aa bb \\\\', b'% cc dd.'))
        self.assertEqual(split_off_comment(b'a\\xb'), (b'a\\xb', None))
        self.assertEqual(split_off_comment(b'a\\065b'), (b'a\\065b', None))
        self.assertEqual(split_off_comment(b'a\\\\065b'), (b'a\\\\065b', None))


@tag('parser')
class ABCParserTests(TestCase):
    """Tests for ABCParser."""
    from main.abcparser import ABCParser

    class TestParser(ABCParser):
        """A minimal ABCParser subclass."""
        lastlog = None
        def log(self, severity, message, text):
            self.lastlog = message
        def process_tune(self, tune):
            pass

    def test_handle_encoding(self):
        p = self.TestParser()
        self.assertEqual(p.encoding, 'default')
        # values permitted by ABC 2.2 standard
        p.handle_encoding(b'%%abc-charset iso-8859-1')
        self.assertEqual(p.encoding, 'iso-8859-1')
        p.handle_encoding(b'I:abc-charset iso-8859-9')
        self.assertEqual(p.encoding, 'iso-8859-9')
        p.handle_encoding(b'%%abc-charset iso-8859-10')
        self.assertEqual(p.encoding, 'iso-8859-10')
        p.handle_encoding(b'I:abc-charset us-ascii')
        self.assertEqual(p.encoding, 'us-ascii')
        p.handle_encoding(b'%%abc-charset utf-8')
        self.assertEqual(p.encoding, 'utf-8')
        p.handle_encoding(b'%%encoding 1')
        self.assertEqual(p.encoding, 'iso-8859-1')
        p.handle_encoding(b'I:encoding 9')
        self.assertEqual(p.encoding, 'iso-8859-9')
        # values that Python accepts, so we do also
        p.handle_encoding(b'%%abc-charset latin-1')
        self.assertEqual(p.encoding, 'latin-1')
        p.handle_encoding(b'I:abc-charset ASCII')
        self.assertEqual(p.encoding, 'ASCII')
        p.handle_encoding(b'%%abc-charset cp1252')
        self.assertEqual(p.encoding, 'cp1252')
        # invalid encoding
        p.encoding = 'default'
        p.lastlog = None
        p.handle_encoding(b'I:abc-charset mojibake')
        self.assertEqual(p.encoding, 'default')
        self.assertIn('Unrecognized character encoding', p.lastlog)
        p.lastlog = None
        p.handle_encoding(b'I:garbage braille')
        self.assertEqual(p.encoding, 'default')
        self.assertIn('Unrecognized character encoding', p.lastlog)
        p.lastlog = None
        p.handle_encoding(b'%%abc-charset *#(!"[')
        self.assertEqual(p.encoding, 'default')
        self.assertIn('Unrecognized character encoding', p.lastlog)
        p.lastlog = None
        p.handle_encoding(b'I:encoding 639')
        self.assertEqual(p.encoding, 'default')
        self.assertIn('Unrecognized character encoding', p.lastlog)
        p.lastlog = None
        p.handle_encoding(b'I:encoding xyz')
        self.assertEqual(p.encoding, 'default')
        self.assertIn('Unrecognized character encoding', p.lastlog)

    def test_decode_from_raw(self):
        p = self.TestParser()
        # 'default' encoding is try UTF-8, else try CP1252, else UTF-8 with backslash escapes
        self.assertEqual(p.encoding, 'default')
        self.assertEqual(p.decode_from_raw(b''), '')
        self.assertEqual(p.decode_from_raw(b'a\xc3\xb1b'), 'añb') # valid UTF-8
        self.assertEqual(p.decode_from_raw(b'a\xc3b'), 'aÃb')     # invalid UTF-8 but valid CP1252
        self.assertEqual(p.decode_from_raw(b'a\x81b'), 'a\\x81b') # invalud UTF-8 and CP1252
        # specific encodings
        p.encoding = 'utf-8'
        self.assertEqual(p.decode_from_raw(b'a\xc3\xb1b'), 'añb') # valid UTF-8
        self.assertEqual(p.decode_from_raw(b'a\xc3b'), 'a\\xc3b') # invalid UTF-8
        p.encoding = 'cp1252'
        self.assertEqual(p.decode_from_raw(b'a\xc3b'), 'aÃb')     # valid CP1252
        self.assertEqual(p.decode_from_raw(b'a\x81b'), 'a\\x81b') # invalid CP1252
        self.assertEqual(p.decode_from_raw(b'a\xa0b'), 'a b')     # nbsp -> space
        p.encoding = 'iso-8859-5'
        self.assertEqual(p.decode_from_raw(b'a\xb4b'), 'aДb')     # valid CP1252
        # python doesn't think any ISO-8859-5 is invalid
        self.assertEqual(p.decode_from_raw(b'a\x81b'), 'a\\u0081b') # C1 controls should be escaped
        p.encoding = 'us-ascii'
        self.assertEqual(p.decode_from_raw(b'a\nb\x7fc'), 'a\\u000ab\\u007fc') # as should C0
