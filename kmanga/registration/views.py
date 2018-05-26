from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import UpdateView

from .forms import UserCreateForm
from .forms import UserUpdateForm
from .models import UserProfile


class UserCreateView(CreateView):
    model = User
    form_class = UserCreateForm
    template_name = 'registration/user_create_form.html'
    success_url = reverse_lazy('subscription-list')

    def get_context_data(self, **kwargs):
        context = super(UserCreateView, self).get_context_data(**kwargs)
        context['language_choices'] = UserProfile.LANGUAGE_CHOICES
        return context

    def form_valid(self, form):
        response = super(UserCreateView, self).form_valid(form)
        username = form.cleaned_data['username']
        password = form.cleaned_data['password1']
        user = authenticate(username=username, password=password)
        login(self.request, user)
        return response


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'registration/user_update_form.html'
    success_url = reverse_lazy('subscription-list')

    def get_object(self, queryset=None):
        return self.request.user


class UserDeleteView(LoginRequiredMixin, DeleteView):
    model = User
    template_name = 'registration/user_confirm_delete.html'
    success_url = reverse_lazy('home')

    def get_object(self, queryset=None):
        return self.request.user
