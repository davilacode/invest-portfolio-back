from rest_framework.routers import DefaultRouter
from portfolio.views import PortfolioViewSet, AssetViewSet, MarketQuoteView
from django.urls import path

router = DefaultRouter()
router.register(r'portfolios', PortfolioViewSet, basename='portfolio')
router.register(r'assets', AssetViewSet, basename='asset')

urlpatterns = router.urls + [
	path('market/quote/', MarketQuoteView.as_view(), name='market-quote'),
]
