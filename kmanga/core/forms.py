from django import forms
from django.conf import settings
from django.core.mail import send_mail


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
