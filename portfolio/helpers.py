from datetime import datetime, timedelta
from decimal import Decimal
import yfinance as yf


def asset_transactions_performance(asset):
    """
    Calcula el rendimiento individual de cada transacción de un asset.
    Retorna lista de dicts con: buy_price, quantity, actual_price, profit_loss, performance_pct.
    Todos los valores numéricos con máx 2 decimales.
    """
    transactions = asset.transactions.order_by('created_at')
    if not transactions.exists():
        return []
    symbol = asset.symbol
    try:
        ticker = yf.Ticker(symbol)
        info = getattr(ticker, 'info', {}) or {}
        actual_price = info.get('regularMarketPrice')
        if actual_price is None:
            fast_info = getattr(ticker, 'fast_info', None)
            if fast_info:
                actual_price = getattr(fast_info, 'lastPrice', None) or getattr(fast_info, 'last_price', None)
        if actual_price is None:
            return []
        actual_price_dec = Decimal(actual_price)
        results = []
        for tx in transactions:
            buy_price = Decimal(tx.price)
            quantity = Decimal(tx.quantity)
            profit_loss = (actual_price_dec - buy_price) * quantity
            performance_pct = (actual_price_dec - buy_price) / buy_price * 100 if buy_price != 0 else Decimal('0')
            results.append({
                'buy_price': float(round(buy_price, 2)),
                'quantity': float(round(quantity, 2)),
                'actual_price': float(round(actual_price_dec, 2)),
                'profit_loss': float(round(profit_loss, 2)),
                'performance_pct': float(round(performance_pct, 2)),
            })
        return results
    except Exception:
        return []

def asset_weighted_performance(asset):
    """
    Calcula métricas usando los valores registrados de assets.
    Retorna dict: symbol, total_quantity, total_cost, actual_value, total_profit_loss, performance, transactions.
    Valores con máximo 2 decimales. performance = (ganancia_total / costo_total) * 100.
    """
    tx_perf = asset_transactions_performance(asset)
    if not tx_perf:
        return {
            'symbol': asset.symbol,
            'error': 'No hay transacciones o precio actual.'
        }
    from decimal import Decimal as D
    total_cost = D('0')
    actual_value = D('0')
    total_quantity = D('0')
    for row in tx_perf:
        buy_price = D(str(row['buy_price']))
        quantity = D(str(row['quantity']))
        actual_price = D(str(row['actual_price']))
        total_cost += buy_price * quantity
        actual_value += actual_price * quantity
        total_quantity += quantity
    if total_cost == 0:
        return {
            'symbol': asset.symbol,
            'error': 'Costo total es cero.'
        }
    total_profit_loss = actual_value - total_cost
    performance = (total_profit_loss / total_cost) * 100
    return {
        'symbol': asset.symbol,
        'total_quantity': float(round(total_quantity, 2)),
        'total_cost': float(round(total_cost, 2)),
        'actual_value': float(round(actual_value, 2)),
        'total_profit_loss': float(round(total_profit_loss, 2)),
        'performance': float(round(performance, 2)),
        'transactions': tx_perf
    }
