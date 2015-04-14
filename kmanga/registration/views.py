from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.views.generic import CreateView
from django.views.generic import TemplateView

from .forms import UserCreateForm
from .models import UserProfile


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
