import ast
import numpy as np
from django.contrib import admin

class CookingTimeFilter(admin.SimpleListFilter):
    title = "Время готовки"
    parameter_name = "cooking_time_range"

    def lookups(self, request, model_admin):
        qs = model_admin.model.objects.values_list("cooking_time", flat=True)
        times = list(set(qs))
        if len(times) < 3:
            return []
        counts, bins = np.histogram(times, bins=3)
        fast_time, slow_time = int(bins[1]), int(bins[2])
        return [
            (str((0, fast_time)), f'быстрее {fast_time} мин ({counts[0]})'),
            (str((fast_time, slow_time)), f'{fast_time}–{slow_time} мин ({counts[1]})'),
            (str((slow_time, 10**10)), f'дольше {slow_time} мин ({counts[2]})'),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            try:
                range_tuple = ast.literal_eval(value)
                return queryset.filter(cooking_time__range=range_tuple)
            except (ValueError, SyntaxError):
                return queryset
        return queryset
