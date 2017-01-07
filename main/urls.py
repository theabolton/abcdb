from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^collection/(?P<pk>[0-9]{1,9})/$', views.CollectionView.as_view()),
    url(r'^instance/(?P<pk>[0-9]{1,9})/$', views.InstanceView.as_view()),
    url(r'^search/$', views.title_search, name='title_search'),
    url(r'^title/(?P<pk>[0-9]{1,9})/$', views.TitleView.as_view()),
    url(r'^upload/$', views.upload, name='upload'),
    # temporary
    url(r'^temp_songs/$', views.SongsView.as_view()),
    url(r'^temp_instances/$', views.InstancesView.as_view()),
    url(r'^temp_titles/$', views.TitlesView.as_view()),
    url(r'^temp_collections/$', views.CollectionsView.as_view()),
]
