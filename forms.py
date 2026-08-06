from __future__ import annotations

import secrets
import string

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.mail import send_mail
from django.conf import settings

from .models import Department, Evaluation, EvaluationAnswer, Questionnaire, UserProfile

User = get_user_model()

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "Username",
                "autocomplete": "username",
                "autofocus": True,
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "Password",
                "autocomplete": "current-password",
                "id": "id_password",
            }
        )
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Invalid credentials.",
    }

_PASSWORD_ALPHABET = string.ascii_letters + string.digits


def generate_temporary_password(length: int = 10) -> str:
    return "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))


class BaseStyledForm:
    base_class = "form-control"

    def _style_widgets(self):
        for field in self.fields.values():
            widget = field.widget
            css = widget.attrs.get("class", "")
            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                continue
            if "form-select" in css or "form-check-input" in css:
                continue
            widget.attrs["class"] = (css + " " + self.base_class).strip()


class UserCreateForm(BaseStyledForm, forms.ModelForm):
    full_name = forms.CharField(max_length=150, required=False)
    role = forms.ChoiceField(choices=UserProfile._meta.get_field("role").choices)
    gender = forms.ChoiceField(
        choices=[("", "-----")] + list(UserProfile._meta.get_field("gender").choices),
        required=False,
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        label="Grade Level",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Auto-generated if blank"}),
        required=False,
    )

    class Meta:
        model = User
        fields = ("username", "email")
        widgets = {
            "username": forms.TextInput(attrs={"placeholder": "Username"}),
            "email": forms.EmailInput(attrs={"placeholder": "name@school.edu"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_widgets()
        for name in ("role", "gender", "department"):
            self.fields[name].widget.attrs["class"] = "form-select"

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get("username")
        email = cleaned.get("email")
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already taken.")
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already in use.")
        return cleaned

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password") or generate_temporary_password()
        user.set_password(password)
        if commit:
            user.save()
            UserProfile.objects.create(
                user=user,
                full_name=self.cleaned_data.get("full_name", ""),
                role=self.cleaned_data.get("role", "staff"),
                gender=self.cleaned_data.get("gender", ""),
                department=self.cleaned_data.get("department"),
                temp_password=password,
            )
        return user


class UserEditForm(BaseStyledForm, forms.ModelForm):
    full_name = forms.CharField(max_length=150, required=False)
    role = forms.ChoiceField(choices=UserProfile._meta.get_field("role").choices)
    gender = forms.ChoiceField(
        choices=[("", "-----")] + list(UserProfile._meta.get_field("gender").choices),
        required=False,
    )
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=False, label="Grade Level")
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"placeholder": "Leave blank to keep current"}),
    )
    current_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"placeholder": "Required to change password"}),
    )

    class Meta:
        model = User
        fields = ("email",)

    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop("profile", None)
        super().__init__(*args, **kwargs)
        if self.profile:
            self.fields["full_name"].initial = self.profile.full_name
            self.fields["role"].initial = self.profile.role
            self.fields["gender"].initial = self.profile.gender
            self.fields["department"].initial = self.profile.department
        self._style_widgets()
        for name in ("role", "gender", "department"):
            self.fields[name].widget.attrs["class"] = "form-select"

    def clean(self):
        cleaned = super().clean()
        new_password = cleaned.get("new_password")
        current_password = cleaned.get("current_password")
        if new_password:
            if not current_password or not self.instance.check_password(current_password):
                raise forms.ValidationError(
                    "Current password is required to set a new password."
                )
        return cleaned

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get("new_password")
        if new_password:
            user.set_password(new_password)
            if self.profile:
                self.profile.temp_password = new_password
        if commit:
            user.save()
            profile = self.profile or getattr(user, "profile", None)
            if profile:
                profile.full_name = self.cleaned_data.get("full_name", profile.full_name)
                profile.role = self.cleaned_data.get("role", profile.role)
                profile.gender = self.cleaned_data.get("gender", profile.gender)
                profile.department = self.cleaned_data.get("department", profile.department)
                profile.save()
        return user


class FacultyPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = (field.widget.attrs.get("class", "") + " form-control").strip()

class DepartmentForm(BaseStyledForm, forms.ModelForm):
    class Meta:
        model = Department
        fields = ("department_name",)
        widgets = {"department_name": forms.TextInput(attrs={"placeholder": "Grade level name"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_widgets()


class QuestionnaireForm(BaseStyledForm, forms.ModelForm):
    class Meta:
        model = Questionnaire
        fields = ("question",)
        widgets = {"question": forms.TextInput(attrs={"placeholder": "Type the question"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_widgets()

class RateForm(forms.ModelForm):
    faculty = forms.ModelChoiceField(
        queryset=User.objects.none(),
        empty_label="Select grade level first",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_faculty"}),
        to_field_name="id",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Department
        self.fields["department"].queryset = Department.objects.all()
        self.fields["department"].label = "Grade Level"
        self.fields["course_section"].label = "Grade & Section"
        self.fields["faculty"].label_from_instance = lambda obj: \
            getattr(obj, 'profile', None) and obj.profile.display_name() or obj.username
        dept = self.data.get("department") or self.initial.get("department")
        if dept:
            self.fields["faculty"].queryset = User.objects.filter(
                profile__role="staff", profile__department_id=dept
            ).select_related("profile")

    class Meta:
        model = Evaluation
        fields = ("email", "full_name", "department", "course_section", "faculty", "comments")
        widgets = {
            "email": forms.EmailInput(attrs={
                "class": "form-control form-control-lg",
                "placeholder": "you@school.edu",
            }),
            "full_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Optional",
            }),
            "course_section": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. G7-Diamond",
            }),
            "department": forms.Select(attrs={"class": "form-select", "id": "id_department"}),
            "comments": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Optional — share additional thoughts or suggestions…",
            }),
        }

    def clean(self):
        cleaned = super().clean()
        dept = cleaned.get("department")
        faculty = cleaned.get("faculty")
        if dept and faculty:
            profile = getattr(faculty, "profile", None)
            if profile and profile.department_id and profile.department_id != dept.id:
                raise forms.ValidationError(
                    "Selected faculty does not belong to the chosen department."
                )
        return cleaned

def mail_credentials(user: User, password: str) -> bool:
    from logging import getLogger
    from .models import RecentActivity

    log = getLogger(__name__)
    if not user.email:
        log.warning("mail_credentials skipped: user '%s' has no email", user.username)
        return False

    subject = f"Welcome to {getattr(settings, 'SITE_NAME', 'FacuTrack')}"
    body = (
        f"Hello {user.get_full_name() or user.username},\n\n"
        f"Your {getattr(settings, 'SITE_NAME', 'FacuTrack')} account has been "
        f"created. You can sign in using the credentials below:\n\n"
        f"  Username: {user.username}\n"
        f"  Temporary password: {password}\n\n"
        f"Sign in at: {getattr(settings, 'SITE_URL', '/')}\n\n"
        "For your security, please change your password after the first "
        "sign-in.\n\n"
        f"— The {getattr(settings, 'SITE_NAME', 'FacuTrack')} Team"
    )
    try:
        sent = send_mail(
            subject=subject,
            message=body,
            from_email=None,            
            recipient_list=[user.email],
            fail_silently=False,
        )
        if getattr(settings, "EMAIL_LOG_SUCCESS", False):
            log.info("Credentials emailed to %s", user.email)
            RecentActivity.objects.create(
                activity=f"Credentials emailed to {user.username}.",
            )
        return bool(sent)
    except Exception as exc:  
        log.exception("mail_credentials failed for %s: %s", user.username, exc)
        try:
            RecentActivity.objects.create(
                activity=f"Failed to email credentials to {user.username}: {exc}".splitlines()[0][:255],
            )
        except Exception:
            pass
        return False
