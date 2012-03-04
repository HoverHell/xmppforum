from django import forms
from django.utils.translation import ugettext_lazy as _
from registration.forms import RegistrationFormUniqueEmail

attrs_dict = {'class': 'required'}


"""
This can also be used with django-registration < 0.8.  For example:

    import registration_optionalemail
    urlpatterns += patterns('', 
        (r'^accounts/register/$', 'registration.views.register',
          {'form_class': registration_optionalemail.forms.RegistrationFormEmailFree,
           'template_name': 'registration/register.html',
           },
          'registration_register'),
        (r'^accounts/', include('registration.urls')),   
    )
"""


class RegistrationFormEmailFree(RegistrationFormUniqueEmail):
    email = forms.EmailField(
      widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=75)),
      label=_(u'email address (optional)'),
      required=False)
    
    def clean_email(self):
        email = self.cleaned_data['email']
        ## The check has to be done here as well (since it doesn't need to
        ## be ckecked for bqing unique in that case).
        if not email:
            return email
        return super(RegistrationFormEmailFree, self).clean_email()

    ## XX: Only used with django-registration < 0.8
    def save(self, profile_callback=None):
        """ Override of save to allow registering of email-less users.  """
        from registration.models import RegistrationProfile
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

