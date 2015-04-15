from django.conf.urls import include, url
from django.contrib import admin

from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView

urlpatterns = [
    # Examples:
    # url(r'^$', 'kmanga.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),

    # Site URLs
    url(r'^$', RedirectView.as_view(url=reverse_lazy('subscription-list')),
        name='home'),
    url(r'^kmanga/', include('core.urls')),
    url(r'^accounts/', include('registration.urls')),

    # Application URLs
    url(r'^django-rq/', include('django_rq.urls')),
]


# Remove this in deployment
# https://docs.djangoproject.com/en/1.8/howto/static-files/
from django.conf import settings
from django.conf.urls.static import static
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
