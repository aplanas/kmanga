from django.conf.urls import patterns, url

from main.views import HistoryList, HistoryDetail, HistoryCreate, HistoryUpdate, HistoryDelete

urlpatterns = patterns('',
    url(r'^history/$', HistoryList.as_view(), name='history-list'),
    url(r'^history/add/$', HistoryCreate.as_view(), name='history-create'),
    url(r'^history/(?P<pk>\d+)/$', HistoryUpdate.as_view(), name='history-update'),
    url(r'^history/(?P<pk>\d+)/view$', HistoryDetail.as_view(), name='history-detail'),
    url(r'^history/(?P<pk>\d+)/delete/$', HistoryDelete.as_view(), name='history-delete'),
)
