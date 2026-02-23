from __future__ import annotations

from django.conf import settings
from django.contrib.auth.views import LoginView


class StaffLoginView(LoginView):
    """Custom login view that prevents superusers from logging in through regular login."""

    def form_valid(self, form):
        user = form.get_user()
        if user.is_superuser:
            form.add_error(None, "Admins must login through the Admin Login session.")
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["admin_error"] = any(
            "Admins must login" in str(error) for error in context.get("form", {}).errors.get("__all__", [])
        )

        enable_demo = bool(getattr(settings, "ENABLE_DEMO_CREDENTIALS", False))
        demo_credentials = getattr(settings, "DEMO_CREDENTIALS", {}) if enable_demo else {}

        def _is_complete(entry):
            return bool(entry.get("username")) and bool(entry.get("password"))

        demo_complete = (
            isinstance(demo_credentials, dict)
            and _is_complete(demo_credentials.get("admin", {}))
            and _is_complete(demo_credentials.get("faculty", {}))
            and _is_complete(demo_credentials.get("stall_owner", {}))
        )

        context["show_demo_credentials"] = bool(enable_demo and demo_complete)
        context["demo_credentials"] = demo_credentials if context["show_demo_credentials"] else {}
        return context


class AdminLoginView(LoginView): 
    """Custom admin login that only allows superusers."""

    template_name = 'admin/login.html'

    def form_valid(self, form):
        user = form.get_user()
        if not user.is_superuser:
            form.add_error(None, "Only superusers can access the admin site. Please use the regular login page.")
            return self.form_invalid(form)
        return super().form_valid(form)
