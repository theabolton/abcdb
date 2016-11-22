from django.http import HttpResponseRedirect
from django.shortcuts import render

from main.forms import UploadForm


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
