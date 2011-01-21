
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.forms import widgets, ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext

from snapboard.models import Category, UserSettings


class PostForm(forms.Form):
    post = forms.CharField(
            label='',
            widget=forms.Textarea(attrs={
                'rows': '8',
                'cols': '120',
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
        recipients = set([x.strip() for x in recipients])  # string of usernames

        u = User.objects.filter(username__in=recipients).order_by('username')
        if len(u) != len(recipients):
            u_set = set([str(x.username) for x in u])
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
                }))
    post = forms.CharField(widget=forms.Textarea(
            attrs={
                'rows': '8',
                'cols': '80',
            }),
            label=_('Message'))

#    def clean_category(self):
#        id = int(self.cleaned_data['category'])
#        return id


class UserSettingsForm(forms.ModelForm):

    def __init__(self, *pa, **ka):
        user = ka.pop('user')
        self.user = user
        super(UserSettingsForm, self).__init__(*pa, **ka)
        self.fields['frontpage_filters'].choices = [(cat.id, cat.label) for
          cat in Category.objects.all() if cat.can_read(user)]

    frontpage_filters = forms.MultipleChoiceField(
        label=_('Front page categories'),
        required=False)

    class Meta:
        model = UserSettings
        exclude = ('user', )

    def clean_frontpage_filters(self):
        frontpage_filters = [cat for cat in (Category.objects.get(pk=id) for id in
                self.cleaned_data['frontpage_filters']) if cat.can_read(self.user)]
        return frontpage_filters


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


# !? Maybe this should be somewhere else?
from registration.forms import RegistrationForm, attrs_dict
from registration.models import RegistrationProfile
class RegistrationFormEmailFree(RegistrationForm):
    #email.required = False
    #email.label=_(u'email address (not required)')

    email = forms.EmailField(
      widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=75)),
      label=_(u'email address (optional)'),
      required=False)

    def save(self, profile_callback=None):
        """
        Override of save to allow registering of email-less users.
        """
        if self.cleaned_data['email']:  # Email was supplied anyway
            new_user = RegistrationProfile.objects.create_inactive_user(
              username=self.cleaned_data['username'],
              password=self.cleaned_data['password1'],
              email=self.cleaned_data['email'],
              profile_callback=profile_callback)
        else: 
            #new_user = RegistrationProfile.objects.create_inactive_user(
            #  username=self.cleaned_data['username'],
            #  password=self.cleaned_data['password1'],
            #  email="", send_email=False,  # Emailless.
            #  profile_callback=profile_callback)
            #new_user.is_active = True  # No need to activate.
            #new_user.save()  # Save activation.
            #  - if we don't need regprofile, then... (btw, callback!)
            new_user = User.objects.create_user(
              self.cleaned_data['username'],
              "",  # Emailless.
              self.cleaned_data['password1'])
            new_user.is_active = True
            new_user.save()
        return new_user

# vim: ai ts=4 sts=4 et sw=4
