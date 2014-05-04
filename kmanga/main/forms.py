from django.forms import ModelForm

from models import History


class HistoryForm(ModelForm):

    class Meta:
        model = History
