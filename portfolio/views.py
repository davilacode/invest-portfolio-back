from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Portfolio, Asset, AssetTransaction
from .serializers import PortfolioSerializer, AssetSerializer, AssetTransactionSerializer
from django.db import transaction
import yfinance as yf

class IsOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        # Requiere autenticación para cualquier acción.
        return bool(request.user and request.user.is_authenticated)

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
        # Prefetch de assets relacionados para evitar consultas N+1 al listar/recuperar portfolios.
        return Portfolio.objects.filter(owner=self.request.user).prefetch_related('assets')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"], url_path="assets")
    def add_asset(self, request, pk=None):
        """POST /portfolios/<id>/assets/

        Crea un nuevo asset dentro del portfolio especificado. Ignora cualquier valor de 'portfolio' enviado
        en el payload y fuerza la asociación al portfolio de la URL.
        """
        portfolio = self.get_object()  # Dispara comprobación de permisos de objeto.
        serializer = AssetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        symbol = serializer.validated_data['symbol']
        qty_new = serializer.validated_data['quantity']
        price_new = serializer.validated_data['average_price']
        with transaction.atomic():
            # Bloquea la fila del asset existente (si existe) para evitar condiciones de carrera.
            asset = (
                Asset.objects.select_for_update()
                .filter(portfolio=portfolio, symbol=symbol)
                .first()
            )
            if asset is None:
                asset = Asset.objects.create(
                    portfolio=portfolio,
                    symbol=symbol,
                    quantity=qty_new,
                    average_price=price_new,
                )
            else:
                total_cost = asset.quantity * asset.average_price + qty_new * price_new
                new_total_qty = asset.quantity + qty_new
                asset.quantity = new_total_qty
                asset.average_price = total_cost / new_total_qty
                asset.save(update_fields=['quantity', 'average_price'])
            AssetTransaction.objects.create(asset=asset, quantity=qty_new, price=price_new)
        out = AssetSerializer(asset, context={'request': request})
        return Response(out.data, status=status.HTTP_201_CREATED)

class AssetViewSet(viewsets.ModelViewSet):
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        return Asset.objects.filter(portfolio__owner=self.request.user).select_related('portfolio').prefetch_related('transactions')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        portfolio = serializer.validated_data['portfolio']
        if portfolio.owner != request.user:
            return Response({'detail': 'Cannot add asset to a portfolio you do not own.'}, status=status.HTTP_403_FORBIDDEN)
        symbol = serializer.validated_data['symbol']
        qty_new = serializer.validated_data['quantity']
        price_new = serializer.validated_data['average_price']
        with transaction.atomic():
            asset = (
                Asset.objects.select_for_update()
                .filter(portfolio=portfolio, symbol=symbol)
                .first()
            )
            if asset is None:
                asset = Asset.objects.create(
                    portfolio=portfolio,
                    symbol=symbol,
                    quantity=qty_new,
                    average_price=price_new,
                )
            else:
                total_cost = asset.quantity * asset.average_price + qty_new * price_new
                new_total_qty = asset.quantity + qty_new
                asset.quantity = new_total_qty
                asset.average_price = total_cost / new_total_qty
                asset.save(update_fields=['quantity', 'average_price'])
            AssetTransaction.objects.create(asset=asset, quantity=qty_new, price=price_new)
        output = self.get_serializer(asset)
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

    def update(self, request, *args, **kwargs):
        # Delegamos en el serializer pero garantizamos que no cambie quantity/average_price por bypass.
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        # Copiamos datos para inspección.
        data = request.data
        forbidden = [f for f in ('quantity', 'average_price') if f in data]
        if forbidden:
            return Response({f: 'Field cannot be directly updated; add a new transaction instead.' for f in forbidden}, status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, partial=partial, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class MarketQuoteView(APIView):
    """GET /api/market/quote/?symbol=TSLA&period=5d

    Returns: {symbol, name, price, period}
    period is optional (default '1d'); we don't currently return history to keep it light.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        symbol = request.query_params.get('symbol')
        if not symbol:
            return Response({'error': 'Missing required query parameter: symbol'}, status=status.HTTP_400_BAD_REQUEST)
        period = request.query_params.get('period', '1d')

        try:
            ticker = yf.Ticker(symbol)
            info = getattr(ticker, 'info', {}) or {}
            name = info.get('shortName') or info.get('longName') or symbol
            price = info.get('regularMarketPrice')
            hist = getattr(ticker.history(period=period), 'Close', None)
            if price is None:
                # Fallback a fast_info si está disponible.
                fast_info = getattr(ticker, 'fast_info', None)
                if fast_info:
                    price = getattr(fast_info, 'lastPrice', None) or getattr(fast_info, 'last_price', None)
            if price is None:
                return Response({'error': 'Price not available for symbol', 'symbol': symbol}, status=status.HTTP_404_NOT_FOUND)
            return Response({
                'symbol': symbol.upper(),
                'name': name,
                'price': price,
                'period': period,
                'history': hist
            })
        except Exception as e:
            return Response({'error': 'Unable to fetch data', 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
