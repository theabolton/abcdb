from django.db import models


class Song(models.Model):
    digest = models.CharField(max_length=40, unique=True, db_index=True)

    def __str__(self):
        return 'Song ' + str(self.id) + ' (' + self.digest[:7] + ')'


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

    def __str__(self):
        return self.title


class Collection(models.Model):
    # CREATE TABLE collection_instance (collection_id INTEGER, instance_id INTEGER, X INTEGER);
    # !FIX! note the 'X' field! need to add 'through = ' to the ManyToManyField below!
    # https://docs.djangoproject.com/en/1.10/ref/models/fields/#manytomanyfield
    # CREATE UNIQUE INDEX collection_instance_index ON collection_instance (collection_id, instance_id);
    instance = models.ManyToManyField(Instance)
    URL = models.URLField(unique=True)  # 200 char limit

    def __str__(self):
        return self.URL
