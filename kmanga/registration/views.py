from django.contrib.auth.models import User
# from django.contrib.auth.tokens import default_token_generator
from django.core.urlresolvers import reverse_lazy
# from django.shortcuts import render
from django.views.generic import (CreateView,
                                  TemplateView,)
# from django.views.decorators.csrf import csrf_protect

from django.contrib.auth.views import logout as _logout
from django.contrib.auth.views import password_change as _password_change
from django.contrib.auth.views import password_change_done as _password_change_done
from django.contrib.auth.views import password_reset as _password_reset
from django.contrib.auth.views import password_reset_done as _password_reset_done
from django.contrib.auth.views import password_reset_confirm as _password_reset_confirm
from django.contrib.auth.views import password_reset_complete as _password_reset_complete

from .forms import UserCreateForm
from .models import UserProfile


def logout(request):
    return _logout(request,
                   template_name='registration/logged_out_.html')


def password_change(request):
    return _password_change(request,
                            template_name='registration/password_change_form_.html')


def password_change_done(request):
    return _password_change_done(request,
                                 template_name='registration/password_change_done_.html')


def password_reset(request):
    return _password_reset(request,
                           template_name='registration/password_reset_form_.html',
                           email_template_name='registration/password_reset_email_.html',
                           subject_template_name='registration/password_reset_subject_.txt')


def password_reset_done(request):
    return _password_reset_done(request,
                                template_name='registration/password_reset_done_.html')


def password_reset_confirm(request):
    return _password_reset_confirm(request,
                                   template_name='registration/password_reset_confirm_.html')


def password_reset_complete(request):
    return _password_reset_complete(request,
                                    template_name='registration/password_reset_complete_.html')


class UserCreateView(CreateView):
    model = User
    form_class = UserCreateForm
    template_name = 'registration/user_create_form.html'
    success_url = reverse_lazy('user_creation_done')

    def form_valid(self, form):
        result = super(UserCreateView, self).form_valid(form)
        return result

# (request, is_admin_site=False,
#                   template_name='registration/user_creation_form.html',
#                   email_template_name='registration/user_creation_email.html',
#                   subject_template_name='registration/user_creation_subject.txt',
#                   account_register_form=UserCreationForm,
#                   token_generator=default_token_generator,
#                   post_reset_redirect=None,
#                   from_email=None,
#                   current_app=None,
#                   extra_context=None):
#     if post_reset_redirect is None:
#         post_reset_redirect = reverse('password_reset_done')
#     else:
#         post_reset_redirect = resolve_url(post_reset_redirect)


class UserCreateDoneView(TemplateView):
    template_name = 'registration/user_create_done.html'


class UserProfileView(TemplateView):
    template_name = 'registration/user_profile.html'
