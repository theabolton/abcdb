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
import hashlib
import operator
import re
import datetime

from django.db import transaction
from django.shortcuts import render
from django.utils.html import format_html
from django.views import generic

from main.forms import TitleSearchForm, UploadForm

from main.models import Collection, Instance, Song, Title
from main.abcparser import Tune, ABCParser


# ========== Utility Functions ==========

def _generate_instance_name(instance):
    """Return a string describing the instance, e.g. 'Instance 3 from new.abc of Song 2 (ab37d30)'"""
    iname = 'Instance {} of Song {}'.format(instance.id, instance.song.id)
    collection = Collection.objects.filter(instance=instance.id)
    if collection:
        iname += ' from ' + str(collection[0])[:50]
    return iname


# ========== User-oriented Model Views ==========

class CollectionView(generic.DetailView):
    model = Collection
    template_name = 'main/collection.html'


class InstanceView(generic.DetailView):
    model = Instance
    template_name = 'main/instance.html'

    def collections(self):
        """Collections in which this instance was found."""
        return Collection.objects.filter(instance__id=self.object.pk)

    def other_instances(self):
        """Other instances of this instance's song, as a list of dicts, available in the template
        as view.other_instances."""
        instances = Instance.objects.filter(song__exact=self.object.song_id)
        context = [{ 'pk': i.pk, 'instance': _generate_instance_name(i) }
                       for i in instances if i.pk != self.object.pk]
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
        songs = Song.objects.filter(title__id__exact=self.object.pk)
        instances = Instance.objects.filter(song__in=songs)
        context = [{ 'pk': i.pk, 'instance': _generate_instance_name(i) } for i in instances]
        return context


# ========== Title Search ==========

def title_search(request):
    form_class = TitleSearchForm

    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            title = request.POST.get('title')
            # -FIX- what should be done to sanitize title before using it in a query?
            query_set = Title.objects.filter(title__icontains=title).order_by('title')
            return render(request, 'main/title_search-post.html',
                          { 'results': query_set, 'key': title, 'count': len(query_set) })
        else:
            message = ('<div data-alert class="alert-box warning radius">There was a problem '
                       'getting the search string.</div>')
            return render(request, 'main/title_search-post.html', { 'error': message, 'form': form })

    return render(request, 'main/title_search.html', { 'form': form_class, })


# ========== ABC File Upload View and Parser Subclass ==========

class UploadParser(ABCParser):
    """Extends ABCParser to save tunes to the database, convert logging information to HTML, and
    gather statistics."""
    def __init__(self, filename=None):
        super().__init__()
        self.status = ''
        self.counts = collections.Counter()
        self.tune_had_warnings = False
        # create Collection
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        source = 'upload {} {}'.format(timestamp.strftime('%Y/%m/%d %H:%M:%S'),
                                       filename or 'no filename')
        self.collection_inst, new = Collection.objects.get_or_create(source=source, date=timestamp)
        self.collection_inst.save()
        if new:
            self.status += format_html("Adding new collection '{}'<br>\n", source)
        else:
            self.status += format_html("Found existing collection '{}'<br>\n", source)


    @transaction.atomic
    def process_tune(self, tune):
        # create the SHA1 digest of the canonical tune, and save it in a Song
        song_digest = hashlib.sha1()
        song_digest.update('\n'.join(map(operator.itemgetter('line'),
                                         tune.canonical)).encode('utf-8'))
        song_digest = song_digest.hexdigest()
        song_inst, new = Song.objects.get_or_create(digest=song_digest)
        song_inst.save()
        if new:
            self.status += format_html("Adding new song {}<br>\n", song_digest[:7])
            self.counts['new_song'] += 1
        else:
            self.status += format_html("Found existing song {}<br>\n", song_digest[:7])
            self.counts['existing_song'] += 1
        # save Titles
        for t in tune.T:
            title_inst, new = Title.objects.get_or_create(title=t)
            if new:
                self.status += format_html("Adding new title '{}'<br>\n", t)
                self.counts['new_title'] += 1
            else:
                self.status += format_html("Found existing title '{}'<br>\n", t)
                self.counts['existing_title'] += 1
            title_inst.songs.add(song_inst)
        # digest the full tune, and save the tune in an Instance
        full_tune = '\n'.join(tune.full_tune)
        tune_digest = hashlib.sha1()
        tune_digest.update(full_tune.encode('utf-8'))
        tune_digest = tune_digest.hexdigest()
        instance_inst, new = Instance.objects.get_or_create(song=song_inst, digest=tune_digest,
                                                            text=full_tune)
        if new:
            self.status += format_html("Adding new instance {}<br>\n", tune_digest[:7])
            self.counts['new_instance'] += 1
        else:
            self.status += format_html("Found existing instance {}<br>\n", tune_digest[:7])
            self.counts['existing_instance'] += 1
        # add instance to collection
        self.collection_inst.instance.add(instance_inst)
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


def upload(request):
    form_class = UploadForm

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            status = format_html("Processing uploaded file '{}', size {} bytes<br>\n", file.name,
                                 file.size)
            p = UploadParser(filename=file.name)
            p.status_append(status)
            p.parse(file.file)
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
                results.append(text.format(p.counts[key], 's' if p.counts[key] != 1 else ''))
            elapsed = datetime.datetime.now(datetime.timezone.utc) - p.collection_inst.date
            elapsed = elapsed.total_seconds()
            results.append('Processed {} lines in {:.2f} seconds'.format(p.line_number, elapsed))
            return render(request, 'main/upload-post.html', { 'results': results,
                                                              'status': p.get_status() })
        else:
            # File uploads are not validated, so this should never be reached. Handle it anyway.
            # form.errors is a dict containing error mesages, keys are field names, values are
            # lists of error message strings.
            status = ('<div data-alert class="alert-box warning radius">The file upload was '
                      'invalid. Contact the site administrator if this problem persists.</div>')
            return render(request, 'main/upload-post.html', { 'status': status })

    return render(request, 'main/upload.html', { 'form': form_class, })


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
        return Instance.objects.all().order_by('digest')


class SongsView(generic.ListView):
    template_name = 'main/temp_songs.html'
    context_object_name = 'song_list'

    def get_queryset(self):
        return Song.objects.all().order_by('digest')


class TitlesView(generic.ListView):
    template_name = 'main/temp_titles.html'
    context_object_name = 'title_list'

    def get_queryset(self):
        return Title.objects.all().order_by('title')
