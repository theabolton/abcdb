from django.contrib import admin

from .models import Song, Instance, Title, Collection


admin.site.register(Song)
admin.site.register(Instance)
admin.site.register(Title)
admin.site.register(Collection)
