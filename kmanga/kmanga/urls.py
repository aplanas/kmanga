"""kmanga URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Import the include() function: from django.conf.urls import url, include
    3. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import url, include
from django.contrib import admin

from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView

from django_rq import urls as django_rq_urls

from core import urls as core_urls
from registration import urls as registration_urls

urlpatterns = [
    url(r'^admin/', admin.site.urls),

    # Site URLs
    url(r'^$', RedirectView.as_view(url=reverse_lazy('subscription-list')),
        name='home'),
    url(r'^about/', RedirectView.as_view(url=reverse_lazy('about-view')),
        name='about'),
    url(r'^contact/', RedirectView.as_view(url=reverse_lazy('contact-form')),
        name='contact'),
    url(r'^kmanga/', include(core_urls)),
    url(r'^accounts/', include(registration_urls)),

    # Application URLs
    url(r'^django-rq/', include(django_rq_urls)),
]

# Remove this in deployment
# https://docs.djangoproject.com/en/1.9/howto/static-files/
from django.conf import settings
from django.conf.urls.static import static
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
