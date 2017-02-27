from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import User
from django.db.models import Q

from .models import UserProfile


class UserCreateForm(UserCreationForm):
    language = forms.CharField()
    email_kindle = forms.EmailField()

    class Meta:
        model = User
        fields = ('username', 'email')

    def save(self, *args, **kwargs):
        instance = super(UserCreateForm, self).save(*args, **kwargs)
        userprofile = instance.userprofile
        userprofile.language = self.cleaned_data['language']
        userprofile.email_kindle = self.cleaned_data['email_kindle']
        userprofile.save()
        return instance

    def clean_email(self):
        email = self.cleaned_data['email']
        if not email:
            raise forms.ValidationError(
                'Required. The email is needed to recover the password',
                code='email_missing',
            )
        return email

    def clean_email_kindle(self):
        email_kindle = self.cleaned_data['email_kindle']
        if UserProfile.objects.filter(email_kindle=email_kindle).exists():
            raise forms.ValidationError(
                'This kindle email is already registered.',
                code='email_kindle_registered',
            )
        return email_kindle


class UserUpdateForm(UserChangeForm):
    language = forms.CharField()
    time_zone = forms.IntegerField()
    send_at = forms.IntegerField()
    email_kindle = forms.EmailField()

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password')

    def save(self, *args, **kwargs):
        userprofile = self.instance.userprofile
        userprofile.language = self.cleaned_data['language']
        userprofile.time_zone = self.cleaned_data['time_zone']
        userprofile.send_at = self.cleaned_data['send_at']
        userprofile.email_kindle = self.cleaned_data['email_kindle']
        userprofile.save()
        return super(UserUpdateForm, self).save(*args, **kwargs)

    def clean_email_kindle(self):
        email_kindle = self.cleaned_data['email_kindle']
        userprofile = self.instance.userprofile
        if UserProfile.objects.filter(
                Q(email_kindle=email_kindle) & ~Q(pk=userprofile)).exists():
            raise forms.ValidationError(
                'This kindle email is already registered.',
                code='email_kindle_registered',
            )
        return email_kindle
