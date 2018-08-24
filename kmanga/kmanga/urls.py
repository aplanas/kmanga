"""kmanga URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from django.urls import include, reverse_lazy
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Site URLs
    path('', RedirectView.as_view(url=reverse_lazy('subscription-list')),
         name='home'),
    path('about/', RedirectView.as_view(url=reverse_lazy('about-view')),
         name='about'),
    path('contact/', RedirectView.as_view(url=reverse_lazy('contact-form')),
         name='contact'),
    path('kmanga/', include('core.urls')),
    path('accounts/', include('registration.urls')),

    # Application URLs
    path('django-rq/', include('django_rq.urls')),
]

# Remove this in deployment
# https://docs.djangoproject.com/en/2.1/howto/static-files/
from django.conf import settings
from django.conf.urls.static import static
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ModuleNotFoundError:
        pass
