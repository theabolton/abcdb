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

import collections
import datetime
import hashlib
import operator
import re
import unicodedata

from django.db import transaction
from django.db.models import Q
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.html import format_html
from django.views import generic

from main.forms import TitleSearchForm, UploadForm

from main.models import Collection, CollectionInstance, Instance, Song, Title
from main.abcparser import Tune, ABCParser


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
        ci = CollectionInstance.objects.filter(collection__id=self.object.pk)
        ci = ci.select_related('instance__first_title')
        ci = ci.defer('instance__text', 'instance__digest')
        paginator = Paginator(ci, 40, orphans=10)
        page = self.request.GET.get('page')
        try:
            pci = paginator.page(page)
        except PageNotAnInteger:
            pci = paginator.page(1)
        except EmptyPage:
            pci = paginator.page(paginator.num_pages)
        return pci


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
        instances = Instance.objects.filter(song=self.object.song_id)
        instances = instances.exclude(id=self.object.pk)
        instances = instances.defer('text', 'digest')
        context = [{ 'pk': i.pk, 'instance': _generate_instance_name(i) } for i in instances]
        return context

    def titles(self):
        """Titles given to this instance's song (all of which may not be present in this
        instance.)"""
        return Title.objects.filter(songs=self.object.song)


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
    paginate_by = 25
    paginate_orphans = 5

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


# ========== ABC File Upload View and Parser Subclass ==========

class UploadParser(ABCParser):
    """Extends ABCParser to save tunes to the database, convert logging information to HTML, and
    gather statistics."""
    def __init__(self, username=None, filename=None):
        super().__init__()
        self.status = ''
        self.counts = collections.Counter()
        self.tune_had_warnings = False
        # create Collection
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        source = 'upload {} {} {}'.format(username or '-', timestamp.strftime('%Y/%m/%d %H:%M:%S'),
                                          filename or 'no filename')
        self.collection_inst, new = Collection.objects.update_or_create(source=source,
                                        defaults={'date': timestamp})
        if new:
            self.status += format_html("Adding new collection '{}'<br>\n", source)
        else:
            self.status += format_html("Found existing collection '{}'<br>\n", source)


    @transaction.atomic
    def process_tune(self, tune):
        # create the SHA1 digest of the canonical tune, and save it in a Song
        song_digest = hashlib.sha1()
        song_digest.update('\n'.join(map(operator.itemgetter('line'),
                                         tune.canonical)).encode('utf-8') + b'\n')
        song_digest = song_digest.hexdigest()
        song_inst, new = Song.objects.get_or_create(digest=song_digest)
        if new:
            self.status += format_html("Adding new song {}<br>\n", song_digest[:7])
            self.counts['new_song'] += 1
        else:
            self.status += format_html("Found existing song {}<br>\n", song_digest[:7])
            self.counts['existing_song'] += 1
        # save Titles
        first_title_inst = None
        if not tune.T:
            tune.T = ('<untitled>', )
        for t in tune.T:
            title_inst, new = Title.objects.update_or_create(title=t,
                                 defaults={'flat_title': remove_diacritics(t).lower()})
            if new:
                self.status += format_html("Adding new title '{}'<br>\n", t)
                self.counts['new_title'] += 1
            else:
                self.status += format_html("Found existing title '{}'<br>\n", t)
                self.counts['existing_title'] += 1
            title_inst.songs.add(song_inst)
            if not first_title_inst:
                first_title_inst = title_inst
        # digest the full tune, and save the tune in an Instance
        tune.full_tune[0] = 'X:1'  # make X fields all 1 for deduplication
        full_tune = '\n'.join(tune.full_tune) + '\n'
        tune_digest = hashlib.sha1()
        tune_digest.update(full_tune.encode('utf-8'))
        tune_digest = tune_digest.hexdigest()
        instance_inst, new = Instance.objects.update_or_create(digest=tune_digest,
                                 defaults={'song': song_inst, 'text': full_tune,
                                           'first_title': first_title_inst})
        if new:
            self.status += format_html("Adding new instance {}<br>\n", tune_digest[:7])
            self.counts['new_instance'] += 1
        else:
            self.status += format_html("Found existing instance {}<br>\n", tune_digest[:7])
            self.counts['existing_instance'] += 1
        # add instance to collection
        collinst_inst = CollectionInstance.objects.create(instance=instance_inst,
                                                          collection=self.collection_inst,
                                                          X=tune.X, line_number=tune.line_number)
        collinst_inst.save()
        # note warning status
        if self.instance_had_warnings:
            self.counts['warning_instance'] +=1
        else:
            self.counts['good_instance'] +=1


    def log(self, severity, message, text):
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='backslashreplace')
        if severity == 'warn':
            self.status += format_html("Warning, line {}: {}: {}<br>\n", str(self.line_number),
                                       message, text)
            self.instance_had_warnings = True
        elif severity == 'info':
            if 'New tune' in message:
                x = re.sub('\D', '', message) # get tune number
                self.status += format_html("Found start of new tune #{} at line {}<br>\n",
                                        x, str(self.line_number))
                self.instance_had_warnings = False
        else:  # severity == 'ignore'
            #print(severity + ' | ' + str(self.line_number) + ' | ' + message + ' | ' + text)
            pass


    def status_append(self, text):
        self.status += text


    def get_status(self):
        return self.status


@permission_required('main.can_upload', login_url="/login/")
def upload(request):
    form_class = UploadForm

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            status = format_html("Processing uploaded file '{}', size {} bytes<br>\n", file.name,
                                 file.size)
            # create parser instance and parse file
            p = UploadParser(username=request.user.username, filename=file.name)
            p.status_append(status)
            p.parse(file.file)
            # build a list of natural-language descriptions of the results
            results = []
            for key, text in (
                    ('new_song', '{} new song{}'),
                    ('existing_song', '{} existing song{}'),
                    ('new_instance', '{} new song instance{}'),
                    ('existing_instance', '{} existing song instance{}'),
                    ('warning_instance', '{} instance{} with warnings'),
                    ('good_instance', '{} instance{} with no warnings'),
                    ('new_title', '{} new title{}'),
                    ('existing_title', '{} existing title{}')):
                result = text.format(p.counts[key], 's' if p.counts[key] != 1 else '')
                if 'warning' in key and p.counts[key] > 0:
                    result = '<div style="color:red">' + result + '</div>'
                results.append(result)
            elapsed = datetime.datetime.now(datetime.timezone.utc) - p.collection_inst.date
            elapsed = elapsed.total_seconds()
            results.append('Processed {} lines in {:.2f} seconds'.format(p.line_number, elapsed))
            return render(request, 'main/upload-post.html', { 'results': results,
                                                              'status': p.get_status() })
        else:
            # form.errors is a dict containing error mesages, keys are field names, values are
            # lists of error message strings.
            status = ('<div data-alert class="alert-box warning radius">The file upload was '
                      'invalid. Contact the site administrator if this problem persists.</div>')
            return render(request, 'main/upload-post.html', { 'status': status })

    return render(request, 'main/upload.html', { 'form': form_class, })


# ========== ABC File Download View ==========

def download(request, pk=None):
    """Allow downloading the raw ABC of a song instance."""
    instance = get_object_or_404(Instance, pk=pk)
    response = HttpResponse(instance.text, content_type='text/vnd.abc')
    response['Content-Disposition'] = 'attachment; filename="song_instance_%s.abc"' % pk
    return response


# ========== Temporary Views for Development ==========

class CollectionsView(generic.ListView):
    template_name = 'main/temp_collections.html'
    context_object_name = 'collection_list'

    def get_queryset(self):
        return Collection.objects.all().order_by('-date')


class InstancesView(generic.ListView):
    template_name = 'main/temp_instances.html'
    context_object_name = 'instance_list'

    def get_queryset(self):
        return Instance.objects.all().order_by('digest').defer('text', 'digest')


class SongsView(generic.ListView):
    template_name = 'main/temp_songs.html'
    context_object_name = 'song_list'

    def get_queryset(self):
        return Song.objects.all().order_by('digest')
