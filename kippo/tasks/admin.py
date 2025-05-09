from accounts.admin import UserCreatedBaseModelAdmin
from commons.admin import OrganizationTaskQuerysetModelAdminMixin, PrettyJSONWidget
from django.contrib import admin
from django.db.models import JSONField, QuerySet
from django.http import request as DjangoRequest  # noqa: N812
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import KippoTask, KippoTaskStatus


@admin.register(KippoTask)
class KippoTaskAdmin(OrganizationTaskQuerysetModelAdminMixin, UserCreatedBaseModelAdmin):
    list_display = (
        "title",
        "category",
        "get_kippoproject_name",
        "get_kippomilestone_title",
        "get_assignee_display_name",
        "get_github_issue_html_url",
        "github_issue_api_url",
    )
    search_fields = ("title",)

    def get_kippoproject_name(self, obj: KippoTask | None = None) -> str:
        result = ""
        if obj and obj.project and obj.project.name:
            result = obj.project.name
        return result

    get_kippoproject_name.short_description = "KippoProject"

    def get_kippomilestone_title(self, obj: KippoTask | None = None):
        result = ""
        if obj and obj.milestone and obj.milestone.title:
            result = obj.milestone.title
        return result

    get_kippomilestone_title.short_description = "KippoMilestone"

    def get_assignee_display_name(self, obj: KippoTask | None = None) -> str:
        result = ""
        if obj and obj.assignee:
            result = obj.assignee.display_name
        return result

    get_assignee_display_name.short_description = "Assignee"

    def get_github_issue_html_url(self, obj: KippoTask | None = None) -> str:
        url = ""
        if obj and obj.github_issue_html_url:
            url = format_html('<a href="{url}">{url}</a>', url=obj.github_issue_html_url)
        return url

    get_github_issue_html_url.short_description = _("Github Issue URL")


@admin.register(KippoTaskStatus)
class KippoTaskStatusAdmin(UserCreatedBaseModelAdmin):
    list_display = (
        "display_name",
        "effort_date",
        "state",
        "get_assignee",
        "minimum_estimate_days",
        "estimate_days",
        "maximum_estimate_days",
    )
    search_fields = ("task__assignee__github_login", "task__github_issue_html_url", "task__title")
    formfield_overrides = {JSONField: {"widget": PrettyJSONWidget}}

    def get_assignee(self, obj: KippoTaskStatus | None = None) -> str:
        result = ""
        if obj and obj.task.assignee:
            result = obj.task.assignee.github_login
        return result

    get_assignee.short_description = "ASSIGNEE"

    def get_queryset(self, request: DjangoRequest) -> QuerySet:
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(task__project__organization__in=request.user.organizations).order_by("task__project__organization").distinct()
