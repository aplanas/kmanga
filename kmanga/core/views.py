from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse_lazy
# from django.shortcuts import render
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic.edit import CreateView
from django.views.generic.edit import DeleteView
from django.views.generic.edit import UpdateView
from django.views.generic.list import MultipleObjectMixin

# import django_rq

from .models import History
from .models import Issue
from .models import Manga
from .models import Subscription


class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
        return login_required(view)


class MangaListView(LoginRequiredMixin, ListView, MultipleObjectMixin):
    model = Manga
    paginate_by = 10
    template_name = 'core/manga_list.html'

    def get_context_data(self, **kwargs):
        """Extend the context data with the search query value."""
        context = super(MangaListView, self).get_context_data(**kwargs)
        q = self.request.GET.get('q', None)
        if q:
            context['q'] = q
        return context

    def get_queryset(self):
        q = self.request.GET.get('q', None)
        mangas = Manga.objects.latests()
        if q:
            mangas = list(mangas.search(q))
        return mangas


class MangaDetailView(LoginRequiredMixin, DetailView):
    model = Manga


class MangaCreateView(LoginRequiredMixin, CreateView):
    model = Manga


class MangaUpdateView(LoginRequiredMixin, UpdateView):
    model = Manga


class MangaDeleteView(LoginRequiredMixin, DeleteView):
    model = Manga
    success_url = reverse_lazy('manga-list')


class IssueListView(LoginRequiredMixin, ListView):
    model = Issue


class IssueDetailView(LoginRequiredMixin, DetailView):
    model = Issue


class IssueCreateView(LoginRequiredMixin, CreateView):
    model = Issue


class IssueUpdateView(LoginRequiredMixin, UpdateView):
    model = Issue


class IssueDeleteView(LoginRequiredMixin, DeleteView):
    model = Issue
    success_url = reverse_lazy('issue-list')


class SubscriptionListView(LoginRequiredMixin, ListView):
    model = Subscription

    def get_queryset(self):
        user = self.request.user
        return user.subscription_set.latests()


class SubscriptionDetailView(LoginRequiredMixin, DetailView):
    model = Subscription


class SubscriptionCreateView(LoginRequiredMixin, CreateView):
    model = Subscription


class SubscriptionUpdateView(LoginRequiredMixin, UpdateView):
    model = Subscription


class SubscriptionDeleteView(LoginRequiredMixin, DeleteView):
    model = Subscription
    success_url = reverse_lazy('subscription-list')


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
