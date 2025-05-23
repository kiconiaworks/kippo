import datetime
from collections import Counter, defaultdict

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.http import (
    HttpResponseBadRequest,
    request as DjangoRequest,  # noqa: N812
)
from django.shortcuts import render
from django.utils import timezone
from projects.functions import get_user_session_organization

from .models import KippoOrganization, OrganizationMembership


def _get_organization_monthly_available_workdays(organization: KippoOrganization) -> tuple[list[OrganizationMembership], dict[str, Counter]]:
    # get organization memberships
    organization_memberships = list(
        OrganizationMembership.objects.filter(organization=organization, user__github_login__isnull=False, is_developer=True)
        .exclude(user__github_login__startswith=settings.UNASSIGNED_USER_GITHUB_LOGIN_PREFIX)
        .order_by("user__github_login")
    )
    member_personal_holiday_dates = {m.user.github_login: tuple(m.user.personal_holiday_dates()) for m in organization_memberships}
    member_public_holiday_dates = {m.user.github_login: tuple(m.user.public_holiday_dates()) for m in organization_memberships}

    current_datetime = timezone.now()
    start_datetime = datetime.datetime(current_datetime.year, current_datetime.month, 1, tzinfo=datetime.UTC)

    # get the last full month 2 years from now
    end_datetime = start_datetime + relativedelta(months=1, years=2)
    end_datetime = end_datetime.replace(day=1)

    current_date = start_datetime.date()
    end_date = end_datetime.date()

    monthly_available_workdays = defaultdict(Counter)
    while current_date < end_date:
        month_key = current_date.strftime("%Y-%m")
        for membership in organization_memberships:
            if (
                current_date not in member_personal_holiday_dates[membership.user.github_login]
                and current_date not in member_public_holiday_dates[membership.user.github_login]
            ) and current_date.weekday() in membership.committed_weekdays:
                monthly_available_workdays[month_key][membership.user] += 1
        current_date += datetime.timedelta(days=1)
    return organization_memberships, monthly_available_workdays


def view_organization_members(request: DjangoRequest):
    try:
        selected_organization, user_organizations = get_user_session_organization(request)
    except ValueError as e:
        return HttpResponseBadRequest(str(e.args))

    organization_memberships, monthly_available_workdays = _get_organization_monthly_available_workdays(selected_organization)

    # prepare monthly output for template
    monthly_member_data = []
    for month in sorted(monthly_available_workdays.keys()):
        data = (
            month,
            sum(monthly_available_workdays[month].values()),
            [monthly_available_workdays[month][m.user] for m in organization_memberships],  # get data in organization_membership order
        )
        monthly_member_data.append(data)

    context = {
        "selected_organization": selected_organization,
        "organizations": user_organizations,
        "organization_memberships": organization_memberships,
        "monthly_available_workdays": monthly_member_data,
        "messages": messages.get_messages(request),
    }

    return render(request, "accounts/view_organization_members.html", context)
