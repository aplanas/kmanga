from django.forms import ModelForm

from models import History


class HistoryForm(ModelForm):

    class Meta:
        model = History
#         fields = ['name', 'from_issue', 'to_issue', 'to_email']
