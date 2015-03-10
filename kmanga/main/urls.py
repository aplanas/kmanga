from django.conf.urls import patterns, url

from .views import HistoryListView
from .views import HistoryDetailView
from .views import HistoryCreateView
from .views import HistoryUpdateView
from .views import HistoryDeleteView
from .views import SubscriptionListView
from .views import SubscriptionDetailView
from .views import SubscriptionCreateView
from .views import SubscriptionUpdateView
from .views import SubscriptionDeleteView


urlpatterns = [
    # Subscription
    url(r'^subscription/$', SubscriptionListView.as_view(),
        name='subscription-list'),
    url(r'^subscription/(?P<pk>\d+)$', SubscriptionDetailView.as_view(),
        name='subscription-read'),
    url(r'^subscription/(?P<pk>\d+)$', HistoryDetailView.as_view(),
        name='subscription-read'),
    url(r'^subscription/new/$', SubscriptionCreateView.as_view(),
        name='subscription-create'),
    url(r'^subscription/edit/(?P<pk>\d+)$', SubscriptionUpdateView.as_view(),
        name='subscription-update'),
    url(r'^subscription/delete/(?P<pk>\d+)$', SubscriptionDeleteView.as_view(),
        name='subscription-delete'),

    # History
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
