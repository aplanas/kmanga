from django.conf.urls import patterns, url

from main.views import (HistoryListView,
                        HistoryDetailView,
                        HistoryCreateView,
                        HistoryUpdateView,
                        HistoryDeleteView)


urlpatterns = [
    url(r'^history/$', HistoryListView.as_view(), name='history-list'),
    url(r'^history/(?P<pk>\d+)$', HistoryDetailView.as_view(),
        name='history-read'),
    url(r'^history/new/$', HistoryCreateView.as_view(), name='history-create'),
    url(r'^history/edit/(?P<pk>\d+)$', HistoryUpdateView.as_view(),
        name='history-update'),
    url(r'^history/delete/(?P<pk>\d+)$', HistoryDeleteView.as_view(),
        name='history-delete'),
    ]

urlpatterns = patterns('', *urlpatterns)
