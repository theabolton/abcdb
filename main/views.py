from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views import generic

from main.forms import UploadForm


# ========== User-oriented Model Views ==========

class CollectionView(generic.DetailView):
    model = Collection
    template_name = 'main/collection.html'


class InstanceView(generic.DetailView):
    model = Instance
    template_name = 'main/instance.html'


# ========== ABC File Upload View ==========

def upload(request):
    form_class = UploadForm

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            print('Size of upload: ' + str(request.FILES['file'].size))
            # !FIX! this needs to be return HttpResponseRedirct('success_url...')
            return HttpResponseRedirect('/')
        else:
            print('form is not valid!')  # !FIX! why?
            # !FIX! use message passing here to add an 'invalid' message to the next page loaded?

    return render(request, 'main/upload.html', {
        'form': form_class,
    })


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
