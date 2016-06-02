from django import forms
from django.conf import settings
from django.core.mail import send_mail

from .models import Issue
from .models import Result
from .models import Subscription


class ContactForm(forms.Form):
    email = forms.EmailField(required=True)
    message = forms.CharField(required=True)

    def send_email(self):
        send_mail(
            'Contact message from %s' % self.cleaned_data['email'],
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
