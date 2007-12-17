from sets import Set

from django import newforms as forms
from django.newforms import widgets, ValidationError
#from django.newforms.forms import SortedDictFromList

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from models import Category


class PostForm(forms.Form):
    post = forms.CharField(
            label = '',
            widget=forms.Textarea(attrs={
                'rows':'5',
                'cols':'10',
            }),
        )
    private = forms.CharField(
            label="Recipients",
            max_length=150,
            widget=forms.TextInput(),
            required=False,
            )

    def clean_private(self):
        recipients = self.cleaned_data['private']
        if len(recipients.strip()) < 1:
            return []
        recipients = filter(lambda x: len(x.strip()) > 0, recipients.split(','))
        recipients = Set([x.strip() for x in recipients]) # string of usernames

        u = User.objects.filter(username__in=recipients).order_by('username')
        if len(u) != len(recipients):
            u_set = Set([str(x.username) for x in u])
            u_diff = recipients.difference(u_set)
            raise ValidationError("The following are not valid user(s): " + ' '.join(u_diff))
        return u



class ThreadForm(forms.Form):
    def __init__( self, *args, **kwargs ):
        super( ThreadForm, self ).__init__( *args, **kwargs )
        self.fields['category'] = forms.ChoiceField(
                choices = [(str(x.id), x.label) for x in Category.objects.all()] 
                )

    # this is here to set the order
    category = forms.CharField()

    subject = forms.CharField(max_length=80,
            widget=forms.TextInput(
                attrs={
                    'size': '80',
                })
            )
    post = forms.CharField(widget=forms.Textarea(
            attrs={
                'rows':'5',
                'cols': '80',
            })
        )

    def clean_category(self):
        id = int(self.cleaned_data['category'])
        return id


class LoginForm(forms.Form):
    username = forms.CharField(max_length=30)
    password = forms.CharField(widget=widgets.PasswordInput)

    def clean_password(self):
        scd = self.cleaned_data
        self.user = authenticate(username=scd['username'], password=scd['password'])

        if self.user is not None:
            if self.user.is_active:
                return self.cleaned_data['password']
            else:
                raise ValidationError('Your account has been disabled.')
        else:
            raise ValidationError('Your username or password were incorrect.')
# vim: ai ts=4 sts=4 et sw=4
