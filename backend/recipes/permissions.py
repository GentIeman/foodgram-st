from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Кастомное разрешение для управления рецептами.
    Разрешает чтение всем, но редактирование только автору.
    """

    def has_permission(self, request, view):
        return (
            request.method in permissions.SAFE_METHODS
            or request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if not request.user.is_authenticated:
            return False

        return obj.author == request.user
