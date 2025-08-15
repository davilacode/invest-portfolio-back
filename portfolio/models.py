from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal

class Portfolio(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='portfolios',
    )
    name = models.CharField(max_length=120)
    base_currency = models.CharField(max_length=10, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(fields=['owner', 'name'], name='uniq_portfolio_owner_name'),
        ]
        indexes = [
            models.Index(fields=['owner', 'name'], name='idx_portfolio_owner_name'),
            models.Index(fields=['created_at'], name='idx_portfolio_created_at'),
        ]

    def __str__(self):
        return f"{self.name} ({self.owner.username})"

class Asset(models.Model):
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='assets',
    )
    symbol = models.CharField(max_length=20)
    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0000001'))],
        help_text='Cantidad debe ser > 0',
    )
    average_price = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0000001'))],
        help_text='Precio promedio debe ser > 0',
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['symbol']
        constraints = [
            models.UniqueConstraint(fields=['portfolio', 'symbol'], name='uniq_asset_portfolio_symbol'),
        ]
        indexes = [
            models.Index(fields=['portfolio', 'symbol'], name='idx_asset_portfolio_symbol'),
            models.Index(fields=['added_at'], name='idx_asset_added_at'),
        ]

    def save(self, *args, **kwargs):
        # Normaliza símbolo (mayúsculas y trim) antes de guardar.
        if self.symbol:
            self.symbol = self.symbol.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.symbol} x {self.quantity}"


class AssetTransaction(models.Model):
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='transactions',
    )
    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0000001'))],
        help_text='Cantidad comprada (> 0)',
    )
    price = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0000001'))],
        help_text='Precio por unidad (> 0)',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['asset', 'created_at'], name='idx_transaction_asset_created'),
        ]

    def __str__(self):
        return f"TX {self.asset.symbol} +{self.quantity} @ {self.price}"
