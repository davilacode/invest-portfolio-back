
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Portfolio, Asset, AssetTransaction
from .serializers import PortfolioSerializer, AssetSerializer, AssetTransactionSerializer
from django.db import transaction
import yfinance as yf
from .helpers import asset_weighted_performance

class IsOwner(permissions.BasePermission):
    def has_permission(self, request, view):
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
        return Portfolio.objects.filter(owner=self.request.user).prefetch_related('assets')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        """GET /api/portfolios/<id>/
        Devuelve los datos originales del portfolio más:
          - performance del portfolio (coste total, valor actual, ganancia/pérdida, %)
          - performance por asset
          - performance por transacción (incluida dentro de cada asset)
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        assets = instance.assets.all().prefetch_related('transactions')

        from decimal import Decimal as D
        total_cost = D('0')
        total_profit_loss = D('0')

        perf_by_asset_id = {}
        for asset in assets:
            perf = asset_weighted_performance(asset)
            perf_by_asset_id[asset.id] = perf
            if 'error' not in perf:
                total_cost += D(str(perf.get('total_cost', 0)))
                total_profit_loss += D(str(perf.get('total_profit_loss', 0)))

        if total_cost > 0:
            performance_pct = (total_profit_loss / total_cost) * 100
        else:
            performance_pct = D('0')
        current_value = total_cost + total_profit_loss

        data = dict(serializer.data)

        enriched_assets = []
        for asset_item in data.get('assets', []):
            aid = asset_item.get('id')
            perf = perf_by_asset_id.get(aid, {})
            if perf and 'error' not in perf:
                # Merge transaction-level performance into existing serializer transactions.
                base_transactions = asset_item.get('transactions', []) or []
                perf_transactions = perf.get('transactions') or []
                enriched_tx = []
                if perf_transactions:
 
                    from collections import defaultdict
                    perf_queue = list(perf_transactions)
                    
                    if len(base_transactions) == len(perf_queue):
                        
                        if len(base_transactions) > 1 and base_transactions[0]['created_at'] > base_transactions[-1]['created_at']:

                            ordered_base = list(reversed(base_transactions))
                        else:
                            ordered_base = list(base_transactions)
                        merged_ordered = []
                        for b, p in zip(ordered_base, perf_queue):
                            merged = {
                                'id': b.get('id'),
                                'created_at': b.get('created_at'),
                                # Replace price with buy_price for clarity.
                                'price': p.get('buy_price', b.get('price')),
                                'quantity': p.get('quantity', b.get('quantity')),
                                'actual_price': p.get('actual_price'),
                                'profit_loss': p.get('profit_loss'),
                                'performance_pct': p.get('performance_pct'),
                            }
                            merged_ordered.append(merged)
                        # Restore original order of base list.
                        if ordered_base is not base_transactions:
                            merged_ordered = list(reversed(merged_ordered))
                        enriched_tx = merged_ordered
                    else:
                        for p in perf_queue:
                            enriched_tx.append({
                                'price': p.get('buy_price'),
                                'quantity': p.get('quantity'),
                                'actual_price': p.get('actual_price'),
                                'profit_loss': p.get('profit_loss'),
                                'performance_pct': p.get('performance_pct'),
                            })
                else:
                    enriched_tx = base_transactions

                asset_item.update({
                    'total_cost': perf.get('total_cost'),
                    'actual_value': perf.get('actual_value'),
                    'total_profit_loss': perf.get('total_profit_loss'),
                    'performance_pct': perf.get('performance'),
                    'total_quantity_calc': perf.get('total_quantity'),
                    'transactions': enriched_tx,
                })
            else:
                asset_item.update({'performance_error': perf.get('error', 'No performance data')})
            enriched_assets.append(asset_item)
        data['assets'] = enriched_assets
        # Métricas agregadas del portafolio a nivel raíz (sin nueva clave agrupadora).
        data.update({
            'total_cost': float(round(total_cost, 2)),
            'current_value': float(round(current_value, 2)),
            'total_profit_loss': float(round(total_profit_loss, 2)),
            'performance_pct': float(round(performance_pct, 2)),
        })
        return Response(data)

    @action(detail=True, methods=["post"], url_path="assets")
    def add_asset(self, request, pk=None):
        """POST /portfolios/<id>/assets/

        Crea un nuevo asset dentro del portfolio especificado. Ignora cualquier valor de 'portfolio' enviado
        en el payload y fuerza la asociación al portfolio de la URL.
        """
        portfolio = self.get_object()
        data = request.data.copy()
        data.pop('portfolio', None) 
        serializer = AssetSerializer(data=data)
        serializer.is_valid(raise_exception=True)
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
        out = AssetSerializer(asset, context={'request': request})
        return Response(out.data, status=status.HTTP_201_CREATED)


    # suma total de los activos del portafolio
    @action(detail=False, methods=["get"], url_path="dashboard")
    def get_dashboard_info(self, request):
        portfolios = Portfolio.objects.filter(owner=request.user).prefetch_related('assets')
        total_portfolios = portfolios.count()
        total_investment_cost = 0
        total_profit_loss = 0

        for portfolio in portfolios:
            for asset in portfolio.assets.all():
                perf = asset_weighted_performance(asset)
                if 'error' not in perf:
                    total_investment_cost += perf.get('total_cost', 0)
                    total_profit_loss += perf.get('total_profit_loss', 0)

        if total_investment_cost > 0:
            total_performance_pct = (total_profit_loss / total_investment_cost) * 100
        else:
            total_performance_pct = 0
        
        total_current_value = total_investment_cost + total_profit_loss

        return Response({
            "total_current_value": total_current_value,
            "total_investment_cost": total_investment_cost,
            "total_profit_loss": total_profit_loss,
            "total_portfolios": total_portfolios,
            "total_performance_pct": total_performance_pct,
            "portfolios": PortfolioSerializer(portfolios, many=True).data
        })

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
