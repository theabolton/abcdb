# ABCdb main/models.py
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

from django.db import models


class Song(models.Model):
    digest = models.CharField(max_length=40, unique=True, db_index=True)

    def __str__(self):
        return 'Song ' + str(self.id)

    class Meta:
        # Per-Model permissions don't make sense for an action as complex as 'upload', but it is
        # convenient and works well to put a single permission here.
        permissions = ( ('can_upload', 'Can upload files'), )


class Instance(models.Model):
    # CREATE TABLE song_instance (song_id INTEGER, instance_id INTEGER);
    # CREATE UNIQUE INDEX song_instance_index ON song_instance (song_id, instance_id);
    song = models.ForeignKey(Song, on_delete=models.PROTECT)
    digest = models.CharField(max_length=40, unique=True, db_index=True)
    text = models.TextField()

    def __str__(self):
        return 'Instance ' + str(self.id) + ' (' + self.digest[:7] + ')'


class Title(models.Model):
    # CREATE TABLE title_song (title_id INTEGER, song_id INTEGER);
    # CREATE UNIQUE INDEX title_song_index ON title_song (title_id, song_id);
    songs = models.ManyToManyField(Song)
    title = models.CharField(max_length=80, unique=True, db_index=True)
    # flat_title is a lowercased, diacritic-stripped copy of title
    flat_title = models.CharField(max_length=80, db_index=True)

    def __str__(self):
        return self.title


class Collection(models.Model):
    # CREATE TABLE collection_instance (collection_id INTEGER, instance_id INTEGER, X INTEGER);
    # CREATE UNIQUE INDEX collection_instance_index ON collection_instance (collection_id, instance_id);
    instances = models.ManyToManyField(Instance, through='CollectionInstance')
    source = models.CharField(max_length=200, unique=True, db_index=True)
    date = models.DateTimeField()

    def __str__(self):
        return self.source


class CollectionInstance(models.Model):
    """This holds the many-to-many relationship between Collection and Instance, and also holds for
    each the reference number (X: field) of the tune and the line number in the file at which it
    occured."""
    collection = models.ForeignKey(Collection, on_delete=models.PROTECT)
    instance = models.ForeignKey(Instance, on_delete=models.PROTECT)
    X = models.PositiveIntegerField()
    line_number = models.PositiveIntegerField()
    first_title = models.ForeignKey(Title, on_delete=models.PROTECT)
