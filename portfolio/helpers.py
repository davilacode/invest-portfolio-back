from datetime import datetime, timedelta
from decimal import Decimal
import yfinance as yf


def asset_performance(asset):
    """
    Calcula el rendimiento de un asset usando yfinance.
    Usa la fecha y precio de la primera transacción (compra) y el precio actual.
    Retorna un dict con: symbol, fecha_compra, precio_compra, precio_actual, rendimiento_pct.
    """
    tx = asset.transactions.order_by('created_at').first()
    if not tx:
        return {
            'symbol': asset.symbol,
            'error': 'No hay transacciones para este asset.'
        }
    fecha_compra = tx.created_at.date()
    precio_compra = Decimal(tx.price)
    symbol = asset.symbol
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=fecha_compra, end=datetime.now().date() + timedelta(days=1))
        if not hist.empty:
            precio_historico = Decimal(hist['Close'].iloc[0])
        else:
            precio_historico = precio_compra
        info = getattr(ticker, 'info', {}) or {}
        precio_actual = info.get('regularMarketPrice')
        if precio_actual is None:
            fast_info = getattr(ticker, 'fast_info', None)
            if fast_info:
                precio_actual = getattr(fast_info, 'lastPrice', None) or getattr(fast_info, 'last_price', None)
        if precio_actual is None:
            return {
                'symbol': symbol,
                'error': 'No se pudo obtener el precio actual.'
            }
        precio_actual = Decimal(precio_actual)
        rendimiento_pct = float((precio_actual - precio_compra) / precio_compra * 100)
        return {
            'symbol': symbol,
            'fecha_compra': str(fecha_compra),
            'precio_compra': float(precio_compra),
            'precio_actual': float(precio_actual),
            'rendimiento_pct': rendimiento_pct
        }
    except Exception as e:
        return {
            'symbol': symbol,
            'error': str(e)
        }
