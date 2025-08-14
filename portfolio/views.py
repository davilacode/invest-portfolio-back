from rest_framework import viewsets, permissions
from .models import Portfolio, Asset
from .serializers import PortfolioSerializer, AssetSerializer

class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Portfolio):
            return obj.owner == request.user
        if isinstance(obj, Asset):
            return obj.portfolio.owner == request.user
        return False

class PortfolioViewSet(viewsets.ModelViewSet):
    serializer_class = PortfolioSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        return Portfolio.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class AssetViewSet(viewsets.ModelViewSet):
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        return Asset.objects.filter(portfolio__owner=self.request.user)
