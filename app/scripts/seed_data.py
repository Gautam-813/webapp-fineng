import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal, init_db
from app.models import ProductCategory, Product, User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed():
    init_db()
    db = SessionLocal()

    try:
        admin = db.query(User).filter(User.email == "admin@thefinancecompany.com").first()
        if not admin:
            db.add(User(
                email="admin@thefinancecompany.com",
                full_name="Admin",
                password_hash=pwd_context.hash("admin123"),
                role="admin",
                status="active",
            ))
            print("Admin user created: admin@thefinancecompany.com / admin123")
        else:
            print("Admin user already exists")
        categories = [
            {"name": "Scalping", "slug": "scalping", "description": "High-frequency short-term trading EAs"},
            {"name": "Trend Following", "slug": "trend-following", "description": "EAs that follow market trends"},
            {"name": "Grid Trading", "slug": "grid-trading", "description": "Grid-based trading strategies"},
            {"name": "Martingale", "slug": "martingale", "description": "Martingale strategy EAs"},
            {"name": "Custom Indicators", "slug": "custom-indicators", "description": "Technical indicators and tools"},
        ]

        for cat in categories:
            existing = db.query(ProductCategory).filter(ProductCategory.slug == cat["slug"]).first()
            if not existing:
                db.add(ProductCategory(**cat))

        db.flush()

        cat_map = {c.slug: c.id for c in db.query(ProductCategory).all()}

        products = [
            {
                "name": "Gold Scalper Pro",
                "slug": "gold-scalper-pro",
                "short_description": "Advanced scalping EA optimized for XAUUSD with real-time market analysis and rapid execution.",
                "description": "Gold Scalper Pro is a professional-grade scalping Expert Advisor specifically optimized for Gold (XAUUSD). It uses a combination of price action analysis, support/resistance levels, and momentum indicators to identify high-probability entry points. Features include dynamic position sizing, news filter, and trailing stop management.",
                "price": 299.00,
                "category_id": cat_map["scalping"],
                "platform": "MT4, MT5",
                "version": "3.2",
                "featured": True,
            },
            {
                "name": "TrendMaster EA",
                "slug": "trendmaster-ea",
                "short_description": "Multi-timeframe trend detection EA with adaptive position management.",
                "description": "TrendMaster EA identifies trending markets across multiple timeframes and executes trades in the direction of the dominant trend. It features adaptive stop-loss placement, partial profit taking, and a sophisticated trend strength filter that keeps you out of choppy markets.",
                "price": 199.00,
                "category_id": cat_map["trend-following"],
                "platform": "MT4, MT5",
                "version": "2.1",
                "featured": True,
            },
            {
                "name": "GridBot Elite",
                "slug": "gridbot-elite",
                "short_description": "Intelligent grid trading system with dynamic spacing and risk controls.",
                "description": "GridBot Elite implements an advanced grid trading strategy with dynamic grid spacing that adapts to market volatility. Includes drawdown limiters, auto-recovery mode, and multi-currency support. Suitable for experienced traders who understand grid trading mechanics.",
                "price": 249.00,
                "category_id": cat_map["grid-trading"],
                "platform": "MT4, MT5",
                "version": "4.0",
                "featured": True,
            },
            {
                "name": "SafeMartingale X",
                "slug": "safemartingale-x",
                "short_description": "Risk-controlled martingale strategy with recovery management.",
                "description": "SafeMartingale X applies martingale principles with strict risk controls. Features include max position limits, equity-based lot sizing, cooldown periods between sequences, and an intelligent recovery system that minimizes drawdown during losing streaks.",
                "price": 179.00,
                "category_id": cat_map["martingale"],
                "platform": "MT4",
                "version": "1.5",
            },
            {
                "name": "Forex Trend Pulse",
                "slug": "forex-trend-pulse",
                "short_description": "Pulse detection algorithm for catching trend reversals early.",
                "description": "Forex Trend Pulse uses a proprietary pulse detection algorithm to identify potential trend reversals before they become obvious. It excels in ranging-to-trending transitions and works best on major forex pairs. Includes a built-in volatility filter to avoid low-probability setups.",
                "price": 149.00,
                "category_id": cat_map["trend-following"],
                "platform": "MT4, MT5",
                "version": "2.3",
            },
            {
                "name": "UltraScalp AI",
                "slug": "ultrascalp-ai",
                "short_description": "AI-enhanced scalping EA with pattern recognition and adaptive execution.",
                "description": "UltraScalp AI incorporates machine learning pattern recognition to identify high-probability scalping setups. It continuously adapts to changing market conditions and features sub-second execution, multiple take-profit levels, and a sophisticated risk management module.",
                "price": 399.00,
                "category_id": cat_map["scalping"],
                "platform": "MT5",
                "version": "1.0",
                "featured": True,
            },
            {
                "name": "GridGuard Pro",
                "slug": "gridguard-pro",
                "short_description": "Grid trading with automatic hedging and drawdown recovery.",
                "description": "GridGuard Pro combines grid trading with intelligent hedging strategies. When drawdown exceeds configured thresholds, it automatically initiates hedge positions to protect capital. Features include multi-level take profit, customizable grid parameters, and comprehensive risk management.",
                "price": 219.00,
                "category_id": cat_map["grid-trading"],
                "platform": "MT4, MT5",
                "version": "2.0",
            },
            {
                "name": "DipCatcher EA",
                "slug": "dipcatcher-ea",
                "short_description": "Strategic dip-buying EA for strong trending markets.",
                "description": "DipCatcher EA is designed to buy dips in strongly trending markets. It identifies pullbacks within established trends and enters positions at optimal re-entry points. Features include trend confirmation filter, scaled entry positions, and trailing break-even management.",
                "price": 129.00,
                "category_id": cat_map["trend-following"],
                "platform": "MT4",
                "version": "1.8",
            },
        ]

        for prod in products:
            existing = db.query(Product).filter(Product.slug == prod["slug"]).first()
            if not existing:
                db.add(Product(**prod))

        db.commit()
        print("Seed data inserted successfully!")
        print(f"  - {len(categories)} categories")
        print(f"  - {len(products)} products")

    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
