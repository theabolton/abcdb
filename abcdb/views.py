from django.views.generic.base import TemplateView


class RootView(TemplateView):
    template_name = 'index.html'
