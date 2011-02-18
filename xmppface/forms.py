""" xmppface sample forms.  """

from django import forms
from .models import UserSettings

class UserSettingsForm(forms.ModelForm):

    def __init__(self, *pa, **ka):
        user = ka.pop('user')
        self.user = user
        super(UserSettingsForm, self).__init__(*pa, **ka)

    class Meta:
        model = UserSettings
        exclude = ('user', )
