from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.views.generic import CreateView
from django.views.generic import UpdateView

from .forms import UserUpdateForm


# class UserCreateView(CreateView):
#     model = User
#     form_class = UserCreateForm
#     # success_url = reverse_lazy('user_done')

#     def form_valid(self, form):
#         result = super(UserCreateView, self).form_valid(form)
#         return result


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'registration/user_form.html'
    success_url = reverse_lazy('subscription-list')

    def get_object(self, queryset=None):
        return self.request.user
