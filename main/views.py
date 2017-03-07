# ABCdb main/views.py
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

import unicodedata

from django.db import connection
from django.db.models import F, Q, Sum
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import generic

from main.forms import TitleSearchForm, UploadForm, FetchForm, ABCEntryForm
from main.models import Collection, CollectionInstance, Instance, Song, Title
from main.upload import handle_upload


# ========== Utility Functions ==========

def _generate_instance_name(instance):
    """Return a string describing the instance, e.g.
    'Instance 3 "Happy Tune" of Song 2 from upload smbolton 2017/01/16 08:50:09 JOS.abc'"""
    title = instance.first_title.title
    if len(title) > 50:
        title = title[:47] + '...'
    return 'Instance {} "{}" of Song {}'.format(instance.id, title, instance.song_id)


def remove_diacritics(s):
    """Remove (many) accents and diacritics from string ``s``, by converting to Unicode
    compatibility decomposed form, and stripping combining characters. This is clearly 'wrong' in
    many cases, but works well enough to provide useful search results. A better option would be
    to use the Python ``Unidecode`` module."""
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join([c for c in nfkd if not unicodedata.combining(c)])


# ========== User-oriented Model Views ==========

class CollectionView(generic.DetailView):
    model = Collection
    template_name = 'main/collection.html'

    def collectioninstances(self):
        """CollectionInstances found in this collection, available in the template as
        view.collectioninstances."""
        ci = (CollectionInstance.objects.filter(collection__id=self.object.pk)
                 .order_by('line_number')
                 .select_related('instance__first_title')
                 .defer('instance__text', 'instance__digest'))
        paginator = Paginator(ci, 40, orphans=10)
        page = self.request.GET.get('page')
        try:
            pci = paginator.page(page)
        except PageNotAnInteger:
            pci = paginator.page(1)
        except EmptyPage:
            pci = paginator.page(paginator.num_pages)
        return pci


class CollectionsView(generic.ListView):
    """Display a list of all collections."""
    template_name = 'main/collections.html'
    context_object_name = 'collection_list'
    paginate_by = 40
    paginate_orphans = 10

    def get_queryset(self):
        return Collection.objects.all().order_by('-date')


class InstanceView(generic.DetailView):
    model = Instance
    template_name = 'main/instance.html'

    def collectioninstances(self):
        """CollectionInstances in which this instance was found."""
        ci = CollectionInstance.objects.filter(instance__id=self.object.pk)
        ci = ci.select_related('collection')
        return ci

    def other_instances(self):
        """Other instances of this instance's song, as a list of dicts, available in the template
        as view.other_instances."""
        instances = (Instance.objects.filter(song=self.object.song_id)
                        .exclude(id=self.object.pk)
                        .select_related('first_title')
                        .defer('text', 'digest'))
        context = [{ 'pk': i.pk, 'instance': _generate_instance_name(i) } for i in instances]
        return context

    def titles(self):
        """Titles given to this instance's song (not all of which may be present in this
        instance.)"""
        return Title.objects.filter(songs=self.object.song)


class SongView(generic.DetailView):
    """A 'Song' is just a hash used to identify "musically identical" instances, but it is useful
    to list the instances and titles that link to it."""
    model = Song
    template_name = 'main/song.html'

    def collections(self):
        """Collections in which this song appeared."""
        return Collection.objects.filter(instances__song=self.object.id)

    def instances(self):
        """Instances of this song, as a list of dicts, available in the template as
        view.instances."""
        instances = (Instance.objects.filter(song=self.object.id)
                        .select_related('first_title')
                        .defer('text', 'digest'))
        context = [{ 'pk': i.pk, 'instance': _generate_instance_name(i) } for i in instances]
        return context

    def titles(self):
        """Titles given to any instance of this song."""
        return Title.objects.filter(songs=self.object.pk).order_by('title')


class TitleView(generic.DetailView):
    model = Title
    template_name = 'main/title.html'

    def song_instances(self):
        """Songs given this title, as a list of dicts, available in the template as
        view.song_instances."""
        songs = Song.objects.filter(title=self.object.pk)
        instances = Instance.objects.filter(song__in=songs).defer('text', 'digest')
        instances = instances.select_related('first_title')
        context = [{ 'pk': i.pk, 'instance': _generate_instance_name(i) } for i in instances]
        return context


class TitlesView(generic.ListView):
    """Display a (possibly paginated) list of all titles."""
    template_name = 'main/titles.html'
    context_object_name = 'title_list'
    paginate_by = 40
    paginate_orphans = 10

    def get_queryset(self):
        return Title.objects.all().order_by('title')


# ========== Title Search ==========

def title_search(request):
    form_class = TitleSearchForm

    if 'title' in request.GET:
        form = form_class(request.GET)
        if form.is_valid():
            title = request.GET.get('title')
            # Search for the given title fragment, matching either the fragment as-is, or a
            # version of it with (many) accents and diacritics stripped.
            flat_title = remove_diacritics(title).lower()
            query_set = Title.objects.filter(Q(title__icontains=title) |
                                             Q(flat_title__contains=flat_title))
            query_set = query_set.order_by('flat_title')
            paginator = Paginator(query_set, 40, orphans=10)
            page = request.GET.get('page')
            try:
                pqs = paginator.page(page)
            except PageNotAnInteger:
                pqs = paginator.page(1)
            except EmptyPage:
                pqs = paginator.page(paginator.num_pages)
            return render(request, 'main/title_search.html', { 'results': pqs, 'key': title })
        else:
            message = ('<div data-alert class="alert-box warning radius">There was a problem '
                       'getting the search string.</div>')
            return render(request, 'main/title_search.html', { 'error': message, 'form': form })

    return render(request, 'main/title_search.html', { 'form': form_class, })


# ========== ABC Upload View ==========

@permission_required('main.can_upload', login_url="/login/")
def upload(request):
    if request.method == 'POST':
        return handle_upload(request)

    context = { 'form': UploadForm, 'entry_form': ABCEntryForm }
    if request.user.is_active and request.user.is_staff:
        # for now, URL fetch is only available to administrators
        context.update(fetch_form=FetchForm)
    return render(request, 'main/upload.html', context)


# ========== Database Statistics View ==========

def stats(request):
    """Show various statistics about the database."""
    songs = Song.objects.count()
    instances = Instance.objects.count()
    titles = Title.objects.count()
    collections = Collection.objects.count()

    # compare number of instances to number of songs
    if instances > 0:
        inst_to_song_dedup = '{:.2f}'.format((instances - songs) / instances * 100.0)
    else:
        inst_to_song_dedup = 'n/a'

    # Compare number of instances in collections to number of instances in database (collections
    # which contributed no new instances are omitted; usually these are subsequent uploads of the
    # same file.)
    collection_instances = (
        Collection.objects.filter(new_instances__gt=0)
            .aggregate(total=Sum(F('existing_instances')+F('new_instances')))['total'])
    if collection_instances and collection_instances > 0:
        coll_to_inst_dedup = '{:.2f}'.format((collection_instances - instances) /
                                             collection_instances * 100.0)
    else:
        coll_to_inst_dedup = 'n/a'

    # generate a histogram of number-of-instances per song
    with connection.cursor() as cursor:
        cursor.execute('SELECT instance_count, COUNT(instance_count) FROM ( '
                           'SELECT COUNT(*) AS instance_count '
                           'FROM main_song LEFT OUTER JOIN main_instance '
                           'ON main_song.id = main_instance.song_id '
                           'GROUP BY main_song.id ) AS counts '
                       'GROUP BY instance_count ORDER BY instance_count DESC')
        inst_per_song_histo = cursor.fetchall()

    # generate a histogram of number-of-collections per instance
    with connection.cursor() as cursor:
        cursor.execute('SELECT collection_count, COUNT(collection_count) FROM ( '
                           'SELECT COUNT(*) AS collection_count '
                           'FROM main_collectioninstance '
                           'GROUP BY main_collectioninstance.instance_id ) AS counts '
                       'GROUP BY collection_count ORDER BY collection_count DESC')
        coll_per_inst_histo = cursor.fetchall()

    # The ``context = locals()`` trick, but explicit
    context = locals()
    context = { key: context[key] for key in
                ('coll_per_inst_histo', 'coll_to_inst_dedup', 'collection_instances',
                 'collections', 'inst_to_song_dedup', 'inst_per_song_histo', 'instances',
                 'songs', 'titles') }
    return render(request, 'main/stats.html', context)


# ========== ABC File Download View ==========

def download(request, pk=None):
    """Allow downloading the raw ABC of a song instance."""
    instance = get_object_or_404(Instance, pk=pk)
    response = HttpResponse(instance.text, content_type='text/vnd.abc')
    response['Content-Disposition'] = 'attachment; filename="song_instance_%s.abc"' % pk
    return response


# ========== Temporary Views for Development ==========

class InstancesView(generic.ListView):
    template_name = 'main/temp_instances.html'
    context_object_name = 'instance_list'

    def get_queryset(self):
        return Instance.objects.all().order_by('digest').defer('text', 'digest')


class SongsView(generic.ListView):
    template_name = 'main/temp_songs.html'
    context_object_name = 'song_list'
    paginate_by = 40
    paginate_orphans = 10

    def get_queryset(self):
        return Song.objects.all().order_by('id')
