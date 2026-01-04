from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User


ROLE_CHOICES = (
    ("OP1", "Opérateur 1"),
    ("CHEF", "Chef équipe"),
    ("DIRECTEUR", "Directeur"),
)

class OperateurAuthForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "Nom d'utilisateur"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Mot de passe"}))


class OperateurCreateForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)
    prenom = forms.CharField(max_length=100)
    nom = forms.CharField(max_length=100)
    telephone = forms.CharField(max_length=30, required=False)
    role = forms.ChoiceField(choices=ROLE_CHOICES)

    def clean_username(self):
        u = self.cleaned_data["username"]
        if User.objects.filter(username=u).exists():
            raise forms.ValidationError("Ce username existe déjà.")
        return u
