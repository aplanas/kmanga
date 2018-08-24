# The views used below are normally mapped in django.contrib.admin.urls.py
# This URLs file is used to provide a reliable view deployment for test purposes.
# It is also provided as a convenience to those who want to deploy these URLs
# elsewhere.

from django.conf.urls import url
from django.contrib.auth import views

from .views import UserCreateView
from .views import UserDeleteView
from .views import UserUpdateView

urlpatterns = [
    # From django.contrib.auth.urls
    url(r'^login/$', views.LoginView.as_view(), name='login'),
    url(r'^logout/$', views.LogoutView.as_view(),
        {'template_name': 'registration/logged_out_.html'}, name='logout'),
    url(r'^password_change/$', views.PasswordChangeView.as_view(),
        {'template_name': 'registration/password_change_form_.html'},
        name='password_change'),
    url(r'^password_change/done/$', views.PasswordChangeDoneView.as_view(),
        {'template_name': 'registration/password_change_done_.html'},
        name='password_change_done'),
    url(r'^password_reset/$', views.PasswordResetView.as_view(),
        {'template_name': 'registration/password_reset_form_.html'},
        name='password_reset'),
    url(r'^password_reset/done/$', views.PasswordResetDoneView.as_view(),
        {'template_name': 'registration/password_reset_done_.html'},
        name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)'
        r'/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.PasswordResetConfirmView.as_view(),
        {'template_name': 'registration/password_reset_confirm_.html'},
        name='password_reset_confirm'),
    url(r'^reset/done/$', views.PasswordResetCompleteView.as_view(),
        {'template_name': 'registration/password_reset_complete_.html'},
        name='password_reset_complete'),

    # User / UserProfile
    url(r'^user/new/$', UserCreateView.as_view(),
        name='user-create'),
    url(r'^user/edit$', UserUpdateView.as_view(),
        name='user-update'),
    url(r'^suser/delete$', UserDeleteView.as_view(),
        name='user-delete'),
]
