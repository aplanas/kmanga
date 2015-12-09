from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import User


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


class UserUpdateForm(UserChangeForm):
    language = forms.CharField()
    email_kindle = forms.EmailField()

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password')

    def save(self, *args, **kwargs):
        userprofile = self.instance.userprofile
        userprofile.language = self.cleaned_data['language']
        userprofile.email_kindle = self.cleaned_data['email_kindle']
        userprofile.save()
        return super(UserUpdateForm, self).save(*args, **kwargs)
