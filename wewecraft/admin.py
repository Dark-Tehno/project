from django.contrib import admin

from .models import LinkCode, MinecraftProfile, News, Rule


@admin.register(MinecraftProfile)
class MinecraftProfileAdmin(admin.ModelAdmin):
    list_display = ("username", "uuid", "user", "linked_at")
    search_fields = ("username", "uuid", "user__username")


@admin.register(LinkCode)
class LinkCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "user", "created_at", "expires_at", "used")
    list_filter = ("used",)
    search_fields = ("code", "user__username")


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ("number", "title", "punishment")
    list_editable = ("punishment",)


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "published", "created_at")
    list_filter = ("published",)
    search_fields = ("title", "text")
