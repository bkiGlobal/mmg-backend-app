from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, SAFE_METHODS


MANAGEMENT_ROLES = {'admin', 'ceo', 'cto', 'it'}
PROJECT_WRITE_ROLES = MANAGEMENT_ROLES | {
    'pm',
    'sm',
    'spv',
    'project_admin',
    'architect',
    'qs',
}
FINANCE_WRITE_ROLES = MANAGEMENT_ROLES | {
    'cfo',
    'finance_admin',
    'qs',
}
INVENTORY_WRITE_ROLES = MANAGEMENT_ROLES | {
    'logistic',
    'pm',
    'sm',
    'project_admin',
}
PEOPLE_WRITE_ROLES = MANAGEMENT_ROLES | {'project_admin'}
APPROVAL_ROLES = MANAGEMENT_ROLES | {'cfo', 'pm', 'sm', 'qs'}


def user_role(user):
    if not user or not user.is_authenticated:
        return ''
    profile = getattr(user, 'profile', None)
    return getattr(profile, 'role', '')


def has_any_role(user, roles):
    return bool(user and user.is_authenticated) and (
        user.is_superuser or user_role(user) in set(roles)
    )


def accessible_project_ids(user, global_roles=None):
    """None berarti akses ke seluruh proyek."""
    if has_any_role(user, MANAGEMENT_ROLES | set(global_roles or ())):
        return None
    profile = getattr(user, 'profile', None)
    if profile is None:
        return []

    from project.models import Project

    return Project.objects.filter(
        Q(client=profile)
        | Q(
            team__members__user=profile,
            team__members__is_active=True,
            team__members__is_deleted=False,
        )
    ).values_list('pk', flat=True).distinct()


class RoleBasedPermission(BasePermission):
    """Permission deklaratif berdasarkan atribut read_roles/write_roles view."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True

        roles = (
            getattr(view, 'read_roles', None)
            if request.method in SAFE_METHODS
            else getattr(view, 'write_roles', None)
        )
        if roles is None:
            return True
        return user_role(request.user) in set(roles)


class ProjectScopedQuerysetMixin:
    """Batasi queryset ke proyek milik client/anggota team."""

    project_lookup = 'project_id'
    global_project_roles = ()

    def _project_id_from_serializer(self, serializer):
        if self.project_lookup == 'pk':
            return None

        parts = [
            part[:-3] if part.endswith('_id') else part
            for part in self.project_lookup.split('__')
        ]
        current = serializer.validated_data.get(parts[0])
        if current is None and serializer.instance is not None:
            current = getattr(serializer.instance, parts[0], None)
        for part in parts[1:]:
            if current is None:
                return None
            current = getattr(current, part, None)
        return getattr(current, 'pk', current)

    def _assert_project_write_access(self, serializer):
        project_id = self._project_id_from_serializer(serializer)
        if project_id is None:
            return
        project_ids = accessible_project_ids(
            self.request.user,
            global_roles=self.global_project_roles,
        )
        if (
            project_ids is not None
            and project_id not in set(project_ids)
        ):
            raise PermissionDenied(
                'Anda tidak dapat menulis data pada proyek ini.'
            )

    def perform_create(self, serializer):
        self._assert_project_write_access(serializer)
        return super().perform_create(serializer)

    def perform_update(self, serializer):
        self._assert_project_write_access(serializer)
        return super().perform_update(serializer)

    def get_queryset(self):
        queryset = super().get_queryset()
        project_ids = accessible_project_ids(
            self.request.user,
            global_roles=self.global_project_roles,
        )
        if project_ids is not None:
            queryset = queryset.filter(
                **{f'{self.project_lookup}__in': project_ids}
            ).distinct()
        if not queryset.ordered:
            queryset = queryset.order_by('pk')
        return queryset
