from rest_framework import serializers
from .models import Portfolio, Asset

class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ["id", "portfolio", "symbol", "quantity", "average_price", "added_at"]
        read_only_fields = ["id", "added_at"]

class PortfolioSerializer(serializers.ModelSerializer):
    assets = AssetSerializer(many=True, read_only=True)

    class Meta:
        model = Portfolio
        fields = ["id", "name", "base_currency", "created_at", "assets"]
        read_only_fields = ["id", "created_at"]
