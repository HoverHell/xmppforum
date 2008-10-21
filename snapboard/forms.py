from sets import Set

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.forms import widgets, ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext

from snapboard.models import Category, UserSettings

class PostForm(forms.Form):
    post = forms.CharField(
            label = '',
            widget=forms.Textarea(attrs={
                'rows':'8',
                'cols':'120',
            }),
        )
    private = forms.CharField(
            label=_("Recipients"),
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
            raise ValidationError(ungettext(
                    "The following is not a valid user:", "The following are not valid user(s): ",
                    len(u_diff)) + ' '.join(u_diff))
        return u



class ThreadForm(forms.Form):
#    def __init__( self, *args, **kwargs ):
#        super( ThreadForm, self ).__init__( *args, **kwargs )
#        self.fields['category'] = forms.ChoiceField(
#                label = _('Category'),
#                choices = [(str(x.id), x.label) for x in Category.objects.all()] 
#                )

#    # this is here to set the order
#    category = forms.CharField(label=_('Category'))

    subject = forms.CharField(max_length=80,
            label=_('Subject'),
            widget=forms.TextInput(
                attrs={
                    'size': '80',
                })
            )
    post = forms.CharField(widget=forms.Textarea(
            attrs={
                'rows':'8',
                'cols': '80',
            }),
            label=_('Message')
        )

#    def clean_category(self):
#        id = int(self.cleaned_data['category'])
#        return id

class UserSettingsForm(forms.ModelForm):

    def __init__(self, *pa, **ka):
        super(UserSettingsForm, self).__init__(*pa, **ka)
        user = ka['user']
        self.fields['frontpage_filters'].choices = [
            (cat.id, cat.name) for cat in Category.objects.all() if 
            cat.can_read(user)
        ]

    frontpage_filters = forms.MultipleChoiceField(label=_('Front page categories'))

    class Meta:
        model = UserSettings
        exclude = ('user',)

    def clean_frontpage_filters(self):
        cd = self.cleaned_data
        cd['frontpage_filters'] = [cat for cat in (Category.objects.get(pk=id) for id in
                cd['frontpage_filters'] if cat.can_read(user))]
        return cd

class LoginForm(forms.Form):
    username = forms.CharField(max_length=30, label=_("Username"))
    password = forms.CharField(widget=widgets.PasswordInput, label=_("Password"))

    def clean_password(self):
        scd = self.cleaned_data
        self.user = authenticate(username=scd['username'], password=scd['password'])

        if self.user is not None:
            if self.user.is_active:
                return self.cleaned_data['password']
            else:
                raise ValidationError(_('Your account has been disabled.'))
        else:
            raise ValidationError(_('Your username or password were incorrect.'))

class InviteForm(forms.Form):
    user = forms.CharField(max_length=30, label=_('Username'))

    def clean_user(self):
        user = self.cleaned_data['user']
        try:
            user = User.objects.get(username=user)
        except User.DoesNotExist:
            raise ValidationError(_('Unknown username'))
        return user

class AnwserInvitationForm(forms.Form):
    decision = forms.ChoiceField(label=_('Answer'), choices=((0, _('Decline')), (1, _('Accept'))))

# vim: ai ts=4 sts=4 et sw=4
