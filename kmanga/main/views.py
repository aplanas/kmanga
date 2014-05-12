from django.core.urlresolvers import reverse_lazy
# from django.shortcuts import render
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

import django_rq

from main.forms import HistoryForm
from main.models import History


class HistoryList(ListView):
    model = History


class HistoryDetail(DetailView):
    model = History


class HistoryCreate(CreateView):
    model = History
    form_class = HistoryForm

    def form_valid(self, form):
        django_rq.get_queue('default').enqueue(form.instance.send_mobi)
        return super(HistoryCreate, self).form_valid(form)


class HistoryUpdate(UpdateView):
    model = History


class HistoryDelete(DeleteView):
    model = History
    success_url = reverse_lazy('history-list')
