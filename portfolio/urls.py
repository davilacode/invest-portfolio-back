from rest_framework.routers import DefaultRouter
from portfolio.views import PortfolioViewSet, AssetViewSet

router = DefaultRouter()
router.register(r'portfolios', PortfolioViewSet, basename='portfolio')
router.register(r'assets', AssetViewSet, basename='asset')

urlpatterns = router.urls
