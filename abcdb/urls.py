"""abcdb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin

from abcdb import views as proj_views
from main  import views as main_views


urlpatterns = [
    # project URLs
    url(r'^$', proj_views.RootView.as_view(), name='root'),
    url(r'^admin/', admin.site.urls),
    # app URLs
    url(r'^collection/(?P<pk>[0-9]{1,9})/$', main_views.CollectionView.as_view()),
    url(r'^instance/(?P<pk>[0-9]{1,9})/$', main_views.InstanceView.as_view()),
    url(r'^upload/$', main_views.upload, name='upload'),
    # temporary
    url(r'^temp_songs/$', main_views.SongsView.as_view()),
    url(r'^temp_instances/$', main_views.InstancesView.as_view()),
    url(r'^temp_titles/$', main_views.TitlesView.as_view()),
    url(r'^temp_collections/$', main_views.CollectionsView.as_view()),
]
