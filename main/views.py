import re

from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.html import format_html
from django.views import generic

from main.forms import UploadForm

from main.models import Collection, Instance, Song, Title
from main.abcparser import Tune, ABCParser
import hashlib, operator


# ========== User-oriented Model Views ==========

class CollectionView(generic.DetailView):
    model = Collection
    template_name = 'main/collection.html'


class InstanceView(generic.DetailView):
    model = Instance
    template_name = 'main/instance.html'


# ========== ABC File Upload View and Parser Subclass ==========

class UploadParser(ABCParser):
    def __init__(self, collection=None):
        super().__init__()
        self.collection = collection
        self.status = ''


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
        else:
            self.status += format_html("Found existing song {}<br>\n", song_digest[:7])
        # save Titles
        for t in tune.T:
            title_inst, new = Title.objects.get_or_create(title=t)
            if new:
                self.status += format_html("Adding new title '{}'<br>\n", t)
            else:
                self.status += format_html("Found existing title '{}'<br>\n", t)
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
        else:
            self.status += format_html("Found existing instance {}<br>\n", tune_digest[:7])
        # save Collection information
        collection_inst, new = Collection.objects.get_or_create(URL=self.collection)
        collection_inst.save()
        collection_inst.instance.add(instance_inst)
        if new:
            self.status += format_html("Adding new collection '{}'<br>\n", self.collection)
        else:
            self.status += format_html("Found existing collection '{}'<br>\n", self.collection)


    def log(self, severity, message, text):
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='backslashreplace')
        if severity == 'warn':
            self.status += format_html("Warning, line {}: {}: {}<br>\n", str(self.line_number),
                                       message, text)
        elif severity == 'info':
            if 'New tune' in message:
                x = re.sub('\D', '', message) # get tune number
                self.status += format_html("Found start of new tune #{} at line {}<br>\n",
                                        x, str(self.line_number))
        else:  # severity == 'ignore'
            print(severity + ' | ' + str(self.line_number) + ' | ' + message + ' | ' + text)


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
            p = UploadParser(collection=file.name)
            p.status_append(status)
            p.parse(file.file)
            return render(request, 'main/upload-post.html', { 'status': p.get_status() })
        else:
            # Django 1.10 does not validate file uploads. Handle this anyway.
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
        return Collection.objects.all().order_by('URL')


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
