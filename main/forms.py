# ABCdb main/forms.py
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

from django import forms


class TitleSearchForm(forms.Form):
    title = forms.CharField(label='String to search for in titles (case insensitive):',
                            widget=forms.TextInput(attrs={'autofocus': 'autofocus'}),
                            required=True)


class UploadForm(forms.Form):
    file = forms.FileField(label='File to Upload:')


class FetchForm(forms.Form):
    url = forms.URLField(label='URL to Fetch:', initial='http://localhost/abc/CR70.abc')


class ABCEntryForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea, label='ABC Notation to Submit:')
