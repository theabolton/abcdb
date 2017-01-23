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


# ========== ABC File Upload View and Parser Subclass ==========

class UploadParser(ABCParser):
    """Extends ABCParser to save tunes to the database, convert logging information to HTML, and
    gather statistics."""
    def __init__(self, username=None, filename=None):
        super().__init__()
        self.journal = ''
        self.counts = collections.Counter()
        self.tune_had_errors = False
        self.tune_had_warnings = False
        # create Collection
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        source = 'upload {} {} {}'.format(username or '-', timestamp.strftime('%Y/%m/%d %H:%M:%S'),
                                          filename or 'no filename')
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
                                 defaults={'flat_title': remove_diacritics(t).lower()})
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
            p.append_journal(status)
            p.parse(file.file)
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
        else:
            # form.errors is a dict containing error mesages, keys are field names, values are
            # lists of error message strings.
            message = ('<div data-alert class="alert-box warning radius">The file upload was '
                       'invalid. Contact the site administrator if this problem persists.</div>')
            return render(request, 'main/upload-post.html', { 'error': message })

    return render(request, 'main/upload.html', { 'form': form_class, })
