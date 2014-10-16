from django.contrib import admin

from main.models import Source, SourceLanguage, ConsolidateGenre, Genre


class SourceLanguageInline(admin.StackedInline):
    model = SourceLanguage


class GenreInline(admin.StackedInline):
    model = Genre


class SourceAdmin(admin.ModelAdmin):
    inlines = [SourceLanguageInline, GenreInline]


admin.site.register(Source, SourceAdmin)
# admin.site.register(ConsolidateGenre)
