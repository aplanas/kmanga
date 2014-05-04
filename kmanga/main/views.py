from django.core.urlresolvers import reverse_lazy
# from django.shortcuts import render
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from main.models import History


class HistoryList(ListView):
    model = History


class HistoryDetail(DetailView):
    model = History


class HistoryCreate(CreateView):
    model = History


class HistoryUpdate(UpdateView):
    model = History


class HistoryDelete(DeleteView):
    model = History
    success_url = reverse_lazy('history-list')
