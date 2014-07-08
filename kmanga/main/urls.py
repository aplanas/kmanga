from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from main.views import (HistoryListView,
                        HistoryDetailView,
                        HistoryCreateView,
                        HistoryUpdateView,
                        HistoryDeleteView)


urlpatterns = [
    url(r'^history/$', login_required(HistoryListView.as_view()),
        name='history-list'),
    url(r'^history/add/$', login_required(HistoryCreateView.as_view()),
        name='history-create'),
    url(r'^history/(?P<pk>\d+)/$', login_required(HistoryUpdateView.as_view()),
        name='history-update'),
    url(r'^history/(?P<pk>\d+)/view$', login_required(HistoryDetailView.as_view()),
        name='history-detail'),
    url(r'^history/(?P<pk>\d+)/delete/$',
        login_required(HistoryDeleteView.as_view()), name='history-delete'),
    ]

urlpatterns = patterns('', *urlpatterns)
