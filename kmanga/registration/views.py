from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseForbidden
from django.views.generic import CreateView
from django.views.generic import UpdateView
from django.views.generic import TemplateView

from .forms import UserCreateForm
from .models import UserProfile


class UserProfileOwnerMixin(object):
    def dispatch(self, request, *args, **kwargs):
        if self.get_object().user != self.request.user:
            return HttpResponseForbidden()
        return super(UserProfileOwnerMixin, self).dispatch(request, *args,
                                                           **kwargs)


class UserCreateView(CreateView):
    model = User
    form_class = UserCreateForm
    template_name = 'registration/user_create_form.html'
    success_url = reverse_lazy('user_creation_done')

    def form_valid(self, form):
        result = super(UserCreateView, self).form_valid(form)
        return result


class UserCreateDoneView(TemplateView):
    template_name = 'registration/user_create_done.html'


class UserProfileUpdateView(LoginRequiredMixin, UserProfileOwnerMixin,
                            UpdateView):
    model = UserProfile
    fields = ['language', 'email_kindle']
    success_url = reverse_lazy('subscription-list')
