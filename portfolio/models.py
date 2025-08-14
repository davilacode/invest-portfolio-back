from django.db import models
from django.conf import settings

class Portfolio(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='portfolios')
    name = models.CharField(max_length=120)
    base_currency = models.CharField(max_length=10, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('owner', 'name')
        ordering = ['created_at']

    def __str__(self):
        return f"{self.name} ({self.owner.username})"

class Asset(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='assets')
    symbol = models.CharField(max_length=20)
    quantity = models.DecimalField(max_digits=20, decimal_places=4)
    average_price = models.DecimalField(max_digits=20, decimal_places=4)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('portfolio', 'symbol')
        ordering = ['symbol']

    def __str__(self):
        return f"{self.symbol} x {self.quantity}"
