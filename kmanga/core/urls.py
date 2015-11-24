from django.conf.urls import include, url

from .views import MangaListView
from .views import MangaDetailView
# from .views import MangaCreateView
# from .views import MangaUpdateView
# from .views import MangaDeleteView
# from .views import ResultListView
# from .views import ResultDetailView
# from .views import ResultCreateView
from .views import ResultUpdateView
# from .views import ResultDeleteView
from .views import SubscriptionListView
from .views import SubscriptionDetailView
from .views import SubscriptionCreateView
from .views import SubscriptionUpdateView
from .views import SubscriptionDeleteView


urlpatterns = [
    # Manga
    url(r'^manga/$', MangaListView.as_view(),
        name='manga-list'),
    url(r'^manga/(?P<pk>\d+)$', MangaDetailView.as_view(),
        name='manga-read'),
    # url(r'^manga/new/$', MangaCreateView.as_view(),
    #     name='manga-create'),
    # url(r'^manga/(?P<pk>\d+)/edit$', MangaUpdateView.as_view(),
    #     name='manga-update'),
    # url(r'^manga/(?P<pk>\d+)/delete$', MangaDeleteView.as_view(),
    #     name='manga-delete'),

    # Subscription
    url(r'^subscription/$', SubscriptionListView.as_view(),
        name='subscription-list'),
    url(r'^subscription/(?P<pk>\d+)$', SubscriptionDetailView.as_view(),
        name='subscription-read'),
    url(r'^subscription/new/$', SubscriptionCreateView.as_view(),
        name='subscription-create'),
    url(r'^subscription/(?P<pk>\d+)/edit$', SubscriptionUpdateView.as_view(),
        name='subscription-update'),
    url(r'^subscription/(?P<pk>\d+)/delete$', SubscriptionDeleteView.as_view(),
        name='subscription-delete'),

    # Result
    # url(r'^result/$', ResultListView.as_view(), name='result-list'),
    # url(r'^result/(?P<pk>\d+)$', ResultDetailView.as_view(),
    #     name='result-read'),
    # url(r'^result/new/$', ResultCreateView.as_view(), name='result-create'),
    url(r'^result/(?P<pk>\d+)/edit$', ResultUpdateView.as_view(),
        name='result-update'),
    # url(r'^result/(?P<pk>\d+)/delete$', ResultDeleteView.as_view(),
    #     name='result-delete'),
]
