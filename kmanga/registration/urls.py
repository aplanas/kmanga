# The views used below are normally mapped in django.contrib.admin.urls.py
# This URLs file is used to provide a reliable view deployment for test purposes.
# It is also provided as a convenience to those who want to deploy these URLs
# elsewhere.

from django.conf.urls import include, url

from .views import logout
from .views import password_change
from .views import password_change_done
from .views import password_reset
from .views import password_reset_done
from .views import password_reset_confirm
from .views import password_reset_complete
from .views import UserCreateView
from .views import UserCreateDoneView
from .views import UserProfileView

urlpatterns = [
    url(r'^login/$', 'django.contrib.auth.views.login', name='login'),
    url(r'^logout/$', logout, name='logout'),
    url(r'^password_change/$', password_change, name='password_change'),
    url(r'^password_change/done/$', password_change_done, name='password_change_done'),
    url(r'^password_reset/$', password_reset, name='password_reset'),
    url(r'^password_reset/done/$', password_reset_done, name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        password_reset_confirm, name='password_reset_confirm'),
    url(r'^reset/done/$', password_reset_complete, name='password_reset_complete'),

    url(r'^register/$', UserCreateView.as_view(), name='register'),
    url(r'^register/done/$', UserCreateDoneView.as_view(), name='register_done'),
    # url(r'^confim/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
    #     'accounts.views.confirm', name='confirm'),
    # url(r'^confirm/done/$', 'django.contrib.auth.views.confirm_done', name='confirm_done'),

    url(r'^profile/$', UserProfileView.as_view(), name='profile'),
]
