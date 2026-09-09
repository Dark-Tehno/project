from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from .models import DarkAccount


class StyledFormMixin:
    """Добавляет единый CSS-класс ко всем полям формы для тёмной темы."""

    def _style(self):
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = widget.attrs.get("class", "")
                widget.attrs["class"] = (css + " checkbox").strip()
                continue
            css = widget.attrs.get("class", "")
            widget.attrs["class"] = (css + " input").strip()
            widget.attrs.setdefault("autocomplete", "off")


class RegisterForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(required=True, label="Почта")

    class Meta(UserCreationForm.Meta):
        model = DarkAccount
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = None
        self.fields["password1"].help_text = None
        self._style()

    def clean_email(self):
        email = self.cleaned_data["email"]
        if DarkAccount.objects.filter(email=email).exists():
            raise ValidationError("Пользователь с такой почтой уже зарегистрирован.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class LoginForm(StyledFormMixin, forms.Form):
    username = forms.CharField(label="Имя пользователя")
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class ProfileEditForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = DarkAccount
        fields = [
            "avatar",
            "avatar_access",
            "first_name",
            "last_name",
            "email",
            "info",
            "date_of_birth",
            "language",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "info": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "avatar": "Аватар",
            "avatar_access": "Доступ к аватару",
            "first_name": "Имя",
            "last_name": "Фамилия",
            "email": "Почта",
            "info": "О себе",
            "date_of_birth": "Дата рождения",
            "language": "Язык интерфейса",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
        # у файлового поля своя стилизация в шаблоне
        self.fields["avatar"].widget.attrs.pop("class", None)

    def clean_email(self):
        email = self.cleaned_data["email"]
        qs = DarkAccount.objects.filter(email=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Эта почта уже используется другим аккаунтом.")
        return email


class CodeConfirmForm(StyledFormMixin, forms.Form):
    code = forms.CharField(label="Код подтверждения", max_length=10)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class PasswordResetRequestForm(StyledFormMixin, forms.Form):
    email = forms.EmailField(label="Почта, указанная при регистрации")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class PasswordResetConfirmForm(StyledFormMixin, forms.Form):
    email = forms.EmailField(label="Почта")
    code = forms.CharField(label="Код из письма", max_length=10)
    new_password1 = forms.CharField(label="Новый пароль", widget=forms.PasswordInput)
    new_password2 = forms.CharField(label="Повторите новый пароль", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("new_password1")
        p2 = cleaned.get("new_password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Пароли не совпадают.")
        return cleaned
