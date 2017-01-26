# ABCdb main/upload.py
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
import io
import operator
import re
import urllib.parse

from django.db import transaction
from django.shortcuts import render
from django.utils.html import format_html

from main.abcparser import ABCParser
from main.forms import UploadForm, FetchForm, ABCEntryForm
from main.models import Collection, CollectionInstance, Instance, Song, Title
import main.views


# ========== ABCParser Subclass ==========

class UploadParser(ABCParser):
    """Extends ABCParser to save tunes to the database, convert logging information to HTML, and
    gather statistics."""
    def __init__(self, username=None, filename=None, method=None):
        super().__init__()
        self.journal = ''
        self.counts = collections.Counter()
        self.tune_had_errors = False
        self.tune_had_warnings = False
        # create Collection
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        if filename:
            filename = ' ' + filename
        else:
            filename = ''
        source = '{} {} {}{}'.format(method or 'unknown', username or '-',
                                     timestamp.strftime('%Y/%m/%d %H:%M:%S'), filename)
        self.collection_inst, new = Collection.objects.update_or_create(source=source,
                                        defaults={'date': timestamp})
        if new:
            self.journal += format_html("Adding new collection '{}'<br>\n", source)
        else:
            self.journal += format_html("Found existing collection '{}'<br>\n", source)


    def parse(self, filehandle):
        """Parse ABC upload, then save statistics to the collection."""
        super().parse(filehandle)
        self.collection_inst.new_songs = self.counts['new_songs']
        self.collection_inst.existing_songs = self.counts['existing_songs']
        self.collection_inst.new_instances = self.counts['new_instances']
        self.collection_inst.existing_instances = self.counts['existing_instances']
        self.collection_inst.error_instances = self.counts['error_instances']
        self.collection_inst.warning_instances = self.counts['warning_instances']
        self.collection_inst.new_titles = self.counts['new_titles']
        self.collection_inst.existing_titles = self.counts['existing_titles']
        self.collection_inst.save()


    def start_tune(self):
        self.tune_had_errors = False
        self.tune_had_warnings = False


    @transaction.atomic
    def process_tune(self, tune):
        # create the SHA1 digest of the canonical tune, and save it in a Song
        song_digest = hashlib.sha1()
        song_digest.update('\n'.join(map(operator.itemgetter('line'),
                                         tune.canonical)).encode('utf-8') + b'\n')
        song_digest = song_digest.hexdigest()
        song_inst, new = Song.objects.get_or_create(digest=song_digest)
        if new:
            self.journal += format_html("Adding new song {}<br>\n", song_digest[:7])
            self.counts['new_songs'] += 1
        else:
            self.journal += format_html("Found existing song {}<br>\n", song_digest[:7])
            self.counts['existing_songs'] += 1
        # save Titles
        first_title_inst = None
        if not tune.T:
            tune.T = ('<untitled>', )
        for t in tune.T:
            title_inst, new = Title.objects.update_or_create(title=t,
                                 defaults={'flat_title': main.views.remove_diacritics(t).lower()})
            if new:
                self.journal += format_html("Adding new title '{}'<br>\n", t)
                self.counts['new_titles'] += 1
            else:
                self.journal += format_html("Found existing title '{}'<br>\n", t)
                self.counts['existing_titles'] += 1
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
            self.journal += format_html("Adding new instance {}<br>\n", tune_digest[:7])
            self.counts['new_instances'] += 1
        else:
            self.journal += format_html("Found existing instance {}<br>\n", tune_digest[:7])
            self.counts['existing_instances'] += 1
        # add instance to collection
        collinst_inst = CollectionInstance.objects.create(instance=instance_inst,
                                                          collection=self.collection_inst,
                                                          X=tune.X, line_number=tune.line_number)
        collinst_inst.save()
        # note warning status
        if self.tune_had_errors:
            self.counts['error_instances'] +=1
        elif self.tune_had_warnings:
            self.counts['warning_instances'] +=1
        else:
            self.counts['good_instances'] +=1


    def log(self, severity, message, text):
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='backslashreplace')
        if severity == 'error':
            self.journal += format_html("Error, line {}: {}: {}<br>\n", str(self.line_number),
                                       message, text)
            self.tune_had_errors = True
        elif severity == 'warn':
            self.journal += format_html("Warning, line {}: {}: {}<br>\n", str(self.line_number),
                                       message, text)
            self.tune_had_warnings = True
        elif severity == 'info':
            if 'New tune' in message:
                x = re.sub('\D', '', message) # get tune number
                self.journal += format_html("Found start of new tune #{} at line {}<br>\n",
                                        x, str(self.line_number))
        else:  # severity == 'ignore'
            #print(severity + ' | ' + str(self.line_number) + ' | ' + message + ' | ' + text)
            pass


    def append_journal(self, text):
        self.journal += text


    def get_journal(self):
        return self.journal


# ========== ABC Upload POST View ==========

def upload_failed(request, reason, severity=''):
    message = format_html('<div data-alert class="alert-box {} radius">{}</div>',
                          severity, reason)
    return render(request, 'main/upload-post.html', { 'error': message })


def handle_upload(request):
    """Handle an upload POST request."""

    # ---- file upload ----
    if request.FILES and 'file' in request.FILES:
        form = UploadForm(request.POST, request.FILES)
        if not form.is_valid():
            # form.errors is a dict containing error mesages, keys are field names, values are
            # lists of error message strings.
            return upload_failed(request, 'The file upload was invalid. Contact the site '
                                 'administrator if this problem persists', severity='warning')
        file = request.FILES['file']
        status = format_html("Processing uploaded file '{}', size {} bytes<br>\n", file.name,
                             file.size)
        method = 'upload'
        filename = file.name

    # ---- URL fetch ----
    elif 'url' in request.POST:
        if not request.user.is_active or not request.user.is_staff:
            return upload_failed(request, 'Sorry, but until the URL fetch is implemented in a '
                                 'background process, it is only available to administrators.',
                                 severity='info')
        form = FetchForm(request.POST)
        if not form.is_valid():
            return upload_failed(request, 'No URL fetch attempted. Please enter a valid URL.')
        url = form.cleaned_data['url']
        file = io.BytesIO()
        file_length = 0
        TOO_LONG = 512 * 1024
        import requests  # -FIX- this will move when ready for production
        try:
            r = requests.get(url, timeout=5, stream=True)
            for chunk in r.iter_content(4096):
                file_length += file.write(chunk)
                if file_length > TOO_LONG:
                    return upload_failed(request, 'The fetched file is too long. Please download '
                                         'it yourself, break it into smaller pieces, and upload '
                                         'them.', severity='info')
            r.raise_for_status()  # convert any non-200 status response to an exception, could
                                  # handle 404 more gracefully
        except requests.exceptions.RequestException as e:
            message = "URL fetch failed with '{}'".format(str(e))  # -FIX- reveals too much?
            return upload_failed(request, message, severity='warning')
        file.seek(0)
        status = format_html("Processing file fetched from '{}', size {} bytes<br>\n", url,
                             file_length)
        method = 'fetch'
        filename = url

    # ---- ABC manual entry ----
    elif 'text' in request.POST:
        form = ABCEntryForm(request.POST)
        if not form.is_valid():
            return upload_failed(request, 'The submitted form was invalid.', severity='warning')
        # Get the 'text' field as bytes. We can't use ``form.cleaned_data['text']`` because that
        # would already be decoded to a Unicode str. It would be nice if urllib had a
        # parse.parse_qsl_to_bytes.
        text = None
        fields = re.split(b'[&;]', request.body)
        for field in fields:
            if field.startswith(b'text='):
                text = urllib.parse.unquote_to_bytes(field[5:].replace(b'+', b' '))
                break
        if not text:
            return upload_failed(request, 'The submitted form was invalid (2).', severity='warning')
        file = io.BytesIO(text)
        # We could look in request.content_params for a hint as to the encoding, but apparently
        # browsers are a bit rubbish at setting this correctly?
        status = format_html("Processing ABC notation, size {} bytes<br>\n", len(text))
        method = 'entry'
        # Use the first title in the submission as the 'filename'
        match = re.search(b'T:\\s*([ -~\\w\\d]+)', text)
        if match:
            filename = match.group(1).decode('utf-8', errors='ignore')
        else:
            filename = None

    else:
        return upload_failed(request, 'Bad form, dude.', severity='warning')

    # create parser instance and parse file
    p = UploadParser(username=request.user.username, filename=filename, method=method)
    p.append_journal(status)
    p.parse(file)
    # build a list of natural-language descriptions of the results
    results = []
    for key, text in (
            ('new_songs', '{} new song{}'),
            ('existing_songs', '{} existing song{}'),
            ('new_instances', '{} new song instance{}'),
            ('existing_instances', '{} existing song instance{}'),
            ('error_instances', '{} instance{} with errors'),
            ('warning_instances', '{} instance{} with warnings'),
            ('good_instances', '{} instance{} with no errors or warnings'),
            ('new_titles', '{} new title{}'),
            ('existing_titles', '{} existing title{}')):
        result = text.format(p.counts[key], 's' if p.counts[key] != 1 else '')
        if ('warning' in key or 'error' in key) and p.counts[key] > 0:
            result = '<div style="color:red">' + result + '</div>'
        results.append(result)
    elapsed = datetime.datetime.now(datetime.timezone.utc) - p.collection_inst.date
    elapsed = elapsed.total_seconds()
    results.append('Processed {} lines in {:.2f} seconds'.format(p.line_number, elapsed))
    return render(request, 'main/upload-post.html', { 'results': results,
                                                      'status': p.get_journal() })
