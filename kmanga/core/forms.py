from django import forms
from django.conf import settings
from django.core.mail import send_mail

from .models import Issue
from .models import Result
from .models import Subscription
from scrapyctl.utils import send


class ContactForm(forms.Form):
    email = forms.EmailField(required=True)
    user = forms.CharField(required=True)
    message = forms.CharField(required=True)

    def send_email(self):
        subject = 'Contact message from %s (%s)' % (
            self.cleaned_data['email'], self.cleaned_data['user'])
        send_mail(
            subject,
            self.cleaned_data['message'],
            settings.KMANGA_EMAIL,
            [settings.CONTACT_EMAIL],
        )


class IssueActionForm(forms.Form):
    SEND_NOW = 'SN'
    ACTION_CHOICES = Result.STATUS_CHOICES + (
        (SEND_NOW, 'Send now'),
    )

    subscription = forms.ModelChoiceField(queryset=None)
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        required=False)
    issues = forms.ModelMultipleChoiceField(queryset=None)

    def __init__(self, *args, **kwargs):
        super(IssueActionForm, self).__init__(*args, **kwargs)
        if 'user' in kwargs['initial']:
            user = kwargs['initial'].pop('user')
            subscription = Subscription.objects.filter(user=user)
            issues = Issue.objects.filter(manga__subscription__in=subscription)
        else:
            subscription = Subscription.objects.all()
            issues = Issue.objects.all()
        self.fields['subscription'].queryset = subscription
        self.fields['issues'].queryset = issues

    def mark(self):
        """Mark issues with a specific status."""
        subscription = self.cleaned_data['subscription']
        action = self.cleaned_data['action']
        for issue in self.cleaned_data['issues']:
            result = issue.create_result_if_needed(
                user=subscription.user,
                status=action,
                set_send_date=False
            )
            if result.status != action:
                result.set_status(status=action)

    def send(self):
        """Send issues to the user."""
        # Basic algorithm is similar to the one for `sendsub`
        #
        #   * Get the number of issues processed during the last 24hs
        #     for an user, and calculate the remaining number of
        #     issues to send to this user.
        #
        #   * Get the list Issues to send in order.
        #
        #   * From the list, send the Issues that are allowed.
        #
        user = self.cleaned_data['subscription'].user
        remains = user.userprofile.remains()
        issues = self.cleaned_data['issues']
        send(issues[:remains], user)
