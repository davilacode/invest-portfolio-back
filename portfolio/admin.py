from django.contrib import admin
from .models import Portfolio, Asset

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "base_currency", "created_at")
    search_fields = ("name", "owner__username")

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("id", "portfolio", "symbol", "quantity", "average_price")
    list_filter = ("portfolio",)
    search_fields = ("symbol",)
