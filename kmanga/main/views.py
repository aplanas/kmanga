from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse_lazy
# from django.shortcuts import render
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

# import django_rq

from .models import History
from .models import Manga


class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
        return login_required(view)


class HistoryListView(LoginRequiredMixin, ListView):
    model = History


class HistoryDetailView(LoginRequiredMixin, DetailView):
    model = History


class HistoryCreateView(LoginRequiredMixin, CreateView):
    model = History
    # form_class = HistoryForm

    # def form_valid(self, form):
    #     result = super(HistoryCreateView, self).form_valid(form)
    #     for issue in range(form.instance.from_issue, form.instance.to_issue+1):
    #         line = form.instance.historyline_set.create(issue=issue)
    #         django_rq.get_queue('default').enqueue(line.send_mobi)
    #     return result


class HistoryUpdateView(LoginRequiredMixin, UpdateView):
    model = History


class HistoryDeleteView(LoginRequiredMixin, DeleteView):
    model = History
    success_url = reverse_lazy('history-list')


class LatestUpdates(ListView):
    """Show latest updates mangas (mangas with new issues)."""
    model = Manga
