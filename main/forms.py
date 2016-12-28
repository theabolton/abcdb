from django import forms


class UploadForm(forms.Form):
    file = forms.FileField()  # 'max_length' kwarg is the length of the filename, not of the file.

    # add a custom field label
    # def __init__(self, *args, **kwargs):
    #     super(UploadForm, self).__init__(*args, **kwargs)
    #     self.fields['field_name'].label = "custom label"
