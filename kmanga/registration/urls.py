# The views used below are normally mapped in django.contrib.admin.urls.py
# This URLs file is used to provide a reliable view deployment for test purposes.
# It is also provided as a convenience to those who want to deploy these URLs
# elsewhere.

from django.conf.urls import url
from django.contrib.auth import views

from .views import UserCreateView
from .views import UserCreateDoneView
from .views import UserProfileView

urlpatterns = [
    # From django.contrib.auth.urls
    url(r'^login/$', views.login, name='login'),
    url(r'^logout/$', views.logout,
        {'template_name': 'registration/logged_out_.html'}, name='logout'),
    # url(r'^password_change/$', views.password_change,
    #     {'template_name': 'registration/password_change_form_.html'}, name='password_change'),
    # url(r'^password_change/done/$', views.password_change_done,
    #     {'template_name': 'registration/password_change_done_.html'}, name='password_change_done'),
    # url(r'^password_reset/$', views.password_reset,
    #     {'template_name': 'registration/password_reset_form_.html'}, name='password_reset'),
    # url(r'^password_reset/done/$', views.password_reset_done,
    #     {'template_name': 'registration/password_reset_done_.html'}, name='password_reset_done'),
    # url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
    #     views.password_reset_confirm, {'template_name': 'registration/password_reset_confirm_.html'},
    #     name='password_reset_confirm'),
    # url(r'^reset/done/$', views.password_reset_complete,
    #     {'template_name': 'registration/password_reset_complete_.html'}, name='password_reset_complete'),

    # url(r'^confim/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
    #     'accounts.views.confirm', name='confirm'),
    # url(r'^confirm/done/$', 'django.contrib.auth.views.confirm_done', name='confirm_done'),

    url(r'^profile/$', UserProfileView.as_view(), name='profile'),
]
