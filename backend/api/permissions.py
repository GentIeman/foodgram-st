from typing import Any
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.request import Request

class IsAuthorOrReadOnly(BasePermission):
    """Проверяет, является ли пользователь автором рецепта."""
    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        return request.method in SAFE_METHODS or obj.author == request.user
