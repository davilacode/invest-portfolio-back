from rest_framework import serializers
from .models import Portfolio, Asset, AssetTransaction

class AssetTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetTransaction
        fields = ["id", "quantity", "price", "created_at"]
        read_only_fields = ["id", "created_at"]


class AssetSerializer(serializers.ModelSerializer):
    transactions = AssetTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Asset
        fields = ["id", "portfolio", "symbol", "quantity", "average_price", "added_at", "transactions"]
        read_only_fields = ["id", "added_at", "transactions"]

    def validate_portfolio(self, value: Portfolio):
        request = self.context.get('request')
        if request and value.owner != request.user:
            raise serializers.ValidationError("You do not own the specified portfolio.")
        return value

    def validate_symbol(self, value: str):
        # Normaliza temprano para coherencia en búsquedas (lookups).
        return value.strip().upper()

    def update(self, instance: Asset, validated_data):
        # Bloquea intento de mover a otro portfolio por seguridad.
        if 'portfolio' in validated_data and validated_data['portfolio'] != instance.portfolio:
            raise serializers.ValidationError({"portfolio": "Cannot change portfolio of an existing asset."})
        # Normaliza símbolo si se intenta cambiar.
        if 'symbol' in validated_data:
            new_symbol = validated_data['symbol'].strip().upper()
            if new_symbol != instance.symbol:
                # Evita colisión con otro asset del mismo portfolio.
                if Asset.objects.filter(portfolio=instance.portfolio, symbol=new_symbol).exclude(pk=instance.pk).exists():
                    raise serializers.ValidationError({"symbol": "Another asset with this symbol already exists in the portfolio."})
                instance.symbol = new_symbol
        # Por diseño la cantidad y average_price no deben editarse directamente (se hace vía transacciones).
        blocked = []
        for field in ('quantity', 'average_price'):
            if field in validated_data:
                blocked.append(field)
        if blocked:
            raise serializers.ValidationError({f: "Field cannot be directly updated; add a new transaction instead." for f in blocked})
        return super().update(instance, validated_data)

class PortfolioSerializer(serializers.ModelSerializer):
    assets = AssetSerializer(many=True, read_only=True)

    class Meta:
        model = Portfolio
        fields = ["id", "name", "base_currency", "created_at", "assets"]
        read_only_fields = ["id", "created_at"]
