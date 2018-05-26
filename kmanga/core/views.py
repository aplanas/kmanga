import bisect

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import InvalidPage, Paginator
from django.http import Http404
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.views.generic import UpdateView
from django.views.generic.edit import BaseFormView
from django.views.generic.list import MultipleObjectMixin

from .forms import ContactForm
from .forms import IssueActionForm
from .models import Issue
from .models import Manga
from .models import Result
from .models import Subscription


class SubscriptionOwnerMixin(object):
    def dispatch(self, request, *args, **kwargs):
        if self.get_object().user != self.request.user:
            return HttpResponseForbidden()
        return super(SubscriptionOwnerMixin, self).dispatch(request, *args,
                                                            **kwargs)


class ResultOwnerMixin(object):
    def dispatch(self, request, *args, **kwargs):
        if self.get_object().subscription.user != self.request.user:
            return HttpResponseForbidden()
        return super(ResultOwnerMixin, self).dispatch(request, *args, **kwargs)


class SafeDeleteView(DeleteView):
    """View that provide the ability to safe delete objects."""

    def delete(self, request, *args, **kwargs):
        """Replace delete method with a safe version."""
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.deleted = True
        self.object.save()
        return HttpResponseRedirect(success_url)


class SafeCreateView(CreateView):
    """View that provide the ability to recover deleted objects."""

    def post(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            success_url = self.get_success_url()
            self.object.deleted = False
            self.object.save()
            return HttpResponseRedirect(success_url)
        except:
            pass
        return super(CreateView, self).post(request, *args, **kwargs)


class AboutTemplateView(TemplateView):
    template_name = 'core/about.html'


class ContactFormView(FormView):
    template_name = 'core/contact.html'
    form_class = ContactForm
    success_url = reverse_lazy('thanks-view')

    def form_valid(self, form):
        form.send_email()
        return super(ContactFormView, self).form_valid(form)


class ThanksTemplateView(TemplateView):
    template_name = 'core/thanks.html'


class MangaListView(LoginRequiredMixin, ListView, MultipleObjectMixin):
    model = Manga
    paginate_by = 9

    def get_context_data(self, **kwargs):
        """Extend the context data with the search query value."""
        context = super(MangaListView, self).get_context_data(**kwargs)
        q = self.request.GET.get('q', None)
        if q and Manga.objects.is_valid(q):
            context['q'] = q
        return context

    def get_queryset(self):
        q = self.request.GET.get('q', None)
        if q and Manga.objects.is_valid(q):
            mangas = Manga.objects.search(q)
        else:
            mangas = Manga.objects.latests()
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


class SubscriptionListView(LoginRequiredMixin, ListView, MultipleObjectMixin):
    model = Subscription
    paginate_by = 9

    def get_queryset(self):
        user = self.request.user
        return Subscription.objects.latests(user=user)


class SubscriptionDetailView(LoginRequiredMixin, SubscriptionOwnerMixin,
                             DetailView):
    model = Subscription
    paginate_by = 25

    def get_context_data(self, **kwargs):
        """Extend the context data with the paginator."""
        context = super(SubscriptionDetailView, self).get_context_data(
            **kwargs)

        paginate_by = self.kwargs.get('by') or self.request.GET.get('by')
        try:
            paginate_by = int(paginate_by)
        except (ValueError, TypeError):
            paginate_by = self.paginate_by

        paginator = Paginator(
            self.object.issues(),
            paginate_by,
            orphans=0,
            allow_empty_first_page=True
        )

        page = self.kwargs.get('page') or self.request.GET.get('page')
        if not page:
            page = self.get_last_page()
        try:
            page_number = int(page)
        except ValueError:
            if page == 'last':
                page_number = paginator.num_pages
            else:
                msg = "Page is not 'last', nor can it be converted to an int."
                raise Http404(msg)

        try:
            page = paginator.page(page_number)
        except InvalidPage as e:
            raise Http404('Invalid page (%s): %s' % (page_number, str(e)))

        context.update({
            'paginator': paginator,
            'page_obj': page,
            'object_list': page.object_list
        })
        return context

    def get_last_page(self):
        """Get the page number of the last modified issue's result."""
        # We get the last page taking first the Issue that contains
        # the most updated result, and searching it in the ordered
        # list of issues.  For each Issue we get the same fields used
        # in Meta.ordering, so we are sure that bisect will work.
        fields = Issue._meta.ordering
        latest_issues = self.object.latest_issues
        latest_issue = latest_issues().values_list(*fields).first()
        if not latest_issue:
            return 1
        issues = self.object.issues().values_list(*fields)
        index = bisect.bisect_left(issues, latest_issue)
        return (index / self.paginate_by) + 1


class SubscriptionCreateView(LoginRequiredMixin, SafeCreateView):
    model = Subscription
    fields = ['manga', 'user', 'language']

    def get_object(self):
        """Return the deleted object using secondary keys."""
        # For this method is OK to fail, because the exception is
        # captured in the SafeCreateView side.  In this case this
        # means that the object is new and needs to be created.
        form = self.get_form()
        # Validate the form, so we have cleaned_data
        form.is_valid()
        return Subscription.all_objects.get(
            manga=form.cleaned_data['manga'],
            user=self.request.user,
            deleted=True
        )

    def get_success_url(self):
        return reverse_lazy('subscription-read',
                            args=[self.object.pk])


class SubscriptionUpdateView(LoginRequiredMixin, SubscriptionOwnerMixin,
                             UpdateView):
    model = Subscription
    fields = ['language', 'issues_per_day', 'paused']

    def get_success_url(self):
        return reverse_lazy('subscription-read',
                            args=[self.object.pk])


class SubscriptionDeleteView(LoginRequiredMixin, SubscriptionOwnerMixin,
                             SafeDeleteView):
    model = Subscription
    success_url = reverse_lazy('subscription-list')

    def delete(self, request, *args, **kwargs):
        # Remove pending Result that are in PROCESSING status
        self.object = self.get_object()
        self.object.result_set.filter(status=Result.PROCESSING).delete()
        return super(SubscriptionDeleteView, self).delete(request, *args,
                                                          **kwargs)


class ResultListView(LoginRequiredMixin, ListView):
    model = Result


class ResultDetailView(LoginRequiredMixin, ResultOwnerMixin, DetailView):
    model = Result


class ResultCreateView(LoginRequiredMixin, CreateView):
    model = Result
    fields = ['issue', 'subscription', 'status']

    def get_success_url(self):
        return reverse_lazy('subscription-read',
                            args=[self.object.subscription.pk])


class ResultUpdateView(LoginRequiredMixin, ResultOwnerMixin, UpdateView):
    model = Result
    fields = ['status']

    def get_success_url(self):
        return reverse_lazy('subscription-read',
                            args=[self.object.subscription.pk])


class ResultMultipleUpdateView(LoginRequiredMixin, BaseFormView):
    form_class = IssueActionForm

    def get(self, request, *args, **kwargs):
        """Redirect to `post` to avoid the render logic."""
        return self.post(request, *args, **kwargs)

    def get_initial(self):
        """Add the `user` into the initial values for the form."""
        initial = super(ResultMultipleUpdateView, self).get_initial()
        initial['user'] = self.request.user
        return initial

    def form_valid(self, form):
        # Check that the owner of the `subscription` is the current
        # user.  Usually this is not necessary, because of the
        # validation of the form.
        self.subscription = form.cleaned_data['subscription']
        if self.subscription.user != self.request.user:
            return HttpResponseForbidden()

        action = form.cleaned_data['action']
        if action in (Result.PENDING, Result.SENT):
            form.mark()
        elif action == IssueActionForm.SEND_NOW:
            form.send()

        return super(ResultMultipleUpdateView, self).form_valid(form)

    def form_invalid(self, form):
        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)

    def get_success_url(self):
        if hasattr(self, 'subscription'):
            return reverse_lazy('subscription-read',
                                args=[self.subscription.pk])
        else:
            return reverse_lazy('subscription-list')


class ResultDeleteView(LoginRequiredMixin, ResultOwnerMixin, DeleteView):
    model = Result
    success_url = reverse_lazy('result-list')


class LatestUpdates(ListView):
    """Show latest updates mangas (mangas with new issues)."""
    model = Manga
