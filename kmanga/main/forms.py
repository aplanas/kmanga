from django import forms

from main.models import History


class HistoryForm(forms.ModelForm):

    class Meta:
        model = History
#         fields = ['name', 'from_issue', 'to_issue', 'to_email']
