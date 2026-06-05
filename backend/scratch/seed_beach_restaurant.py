# ruff: noqa: PLR0915
# pyright: reportPrivateUsage=false
from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import delete, select

from app.auth.infrastructure.orm_models import TenantORM
from app.menu.api.routes import _resolve_menu_doc
from app.menu.domain.menu import Menu
from app.menu.infrastructure.mongo_sync import MenuReadModelSync
from app.menu.infrastructure.orm_models import CategoryItemORM, MenuItemORM, MenuORM
from app.order.infrastructure.orm_models import OrderFormORM
from app.settings import get_settings
from app.shared.database import (
    close_mongo,
    close_postgres,
    get_async_session,
    get_mongo_db,
    init_mongo,
    init_postgres,
)
from app.shared.value_objects import MeasuredQuantity
from app.stock.domain.enums import TransactionType
from app.stock.domain.stock_item import SimpleStockItem
from app.stock.domain.transaction import StockTransaction
from app.stock.infrastructure.orm_models import (
    RecipeIngredientORM,
    RecipeORM,
    StockItemORM,
    StockTransactionORM,
)
from app.stock.infrastructure.stock_read_sync import StockReadModelSync


async def seed() -> None:
    settings = get_settings()
    await init_postgres(settings)
    await init_mongo(settings)

    mongo_db = get_mongo_db()

    async for db in get_async_session():
        print("Cleaning up old database records...")

        # 1. Clean table 1 order forms
        # Clean Postgres
        await db.execute(delete(OrderFormORM).where(OrderFormORM.table_number == 1))
        # Clean Mongo
        await mongo_db["orders_read"].delete_many({"table_number": 1})
        await mongo_db["orders_read"].delete_many({"table_number": "1"})

        # 2. Make sure tenant 1 exists
        tenant_orm = await db.scalar(select(TenantORM).where(TenantORM.id == 1))
        if not tenant_orm:
            tenant_orm = TenantORM(id=1, name="Barraca do Sol", plan_type="BASIC", is_active=True)
            db.add(tenant_orm)
            await db.flush()
        else:
            tenant_orm.name = "Barraca do Sol"

        # Clean existing menus, menu items, recipes, stock items for fresh start
        await db.execute(delete(CategoryItemORM))
        await db.execute(delete(MenuORM))
        await db.execute(delete(RecipeIngredientORM))
        await db.execute(delete(RecipeORM))
        await db.execute(delete(StockTransactionORM))
        await db.execute(delete(StockItemORM))
        await db.execute(delete(MenuItemORM))
        await db.flush()

        # Clean Mongo read models
        await mongo_db["stock_read"].delete_many({})
        await mongo_db["menu_read_models"].delete_many({})

        print("Seeding beach restaurant menu items...")
        # Add Menu Items
        menu_items_data = [
            (101, "Água de Coco", "Coco gelado servido na fruta natural.", 8.00, "Bebidas", "BAR"),
            (
                102,
                "Caipirinha de Limão",
                "Cachaça artesanal, limão espremido e açúcar.",
                18.00,
                "Bebidas",
                "BAR",
            ),
            (
                103,
                "Isca de Peixe Crocante",
                "Tiras de peixe fresco empanadas servidas com molho tártaro.",
                45.00,
                "Petiscos",
                "COZINHA",
            ),
            (
                104,
                "Camarão ao Alho e Óleo",
                "Camarão grelhado salpicado com alho dourado e azeite.",
                65.00,
                "Petiscos",
                "COZINHA",
            ),
            (
                105,
                "Pastel de Camarão",
                "Pastel super recheado frito na hora.",
                12.00,
                "Entradas",
                "COZINHA",
            ),
            (
                106,
                "Açaí na Tigela",
                "Açaí completo com granola, banana fatiada e leite condensado.",
                22.00,
                "Sobremesas",
                "COZINHA",
            ),
            (
                107,
                "Suco de Abacaxi com Hortelã",
                "Suco natural e refrescante feito na hora.",
                10.00,
                "Bebidas",
                "BAR",
            ),
        ]

        menu_items = []
        for mid, name, desc, price, cat_name, station in menu_items_data:
            mi = MenuItemORM(
                id=mid,
                tenant_id="1",
                name=name,
                description=desc,
                base_price=Decimal(str(price)),
                category_name=cat_name,
                station_type=station,
                is_available=True,
            )
            db.add(mi)
            menu_items.append(mi)

        await db.flush()

        print("Seeding stock items and transactions...")
        # Add Stock Items
        stock_items_data = [
            (201, "Coco Verde", "BEVERAGE", "un", 5.0, 100),
            (202, "Cachaça Artesanal", "BEVERAGE", "ml", 1000.0, 5000),
            (203, "Limão", "RAW_MATERIAL", "un", 10.0, 200),
            (204, "Peixe Cação", "RAW_MATERIAL", "g", 1000.0, 10000),
            (205, "Camarão Médio", "RAW_MATERIAL", "g", 500.0, 5000),
            (206, "Massa de Pastel", "RAW_MATERIAL", "un", 20.0, 150),
            (207, "Polpa de Açaí", "RAW_MATERIAL", "g", 2000.0, 20000),
            (208, "Abacaxi", "RAW_MATERIAL", "un", 5.0, 50),
        ]

        stock_sync = StockReadModelSync(mongo_db)

        for sid, name, category, unit, min_stock, initial_qty in stock_items_data:
            s_orm = StockItemORM(
                id=sid,
                tenant_id="1",
                name=name,
                category=category,
                type="SIMPLE",
                unit=unit,
                min_stock_level=min_stock,
                is_active=True,
            )
            db.add(s_orm)
            await db.flush()

            # Initial stock input transaction
            tx_orm = StockTransactionORM(
                stock_item_id=sid,
                transaction_type="INPUT",
                quantity_value=Decimal(str(initial_qty)),
                quantity_unit=unit,
            )
            db.add(tx_orm)
            await db.flush()

            # Reconstruct and Sync to Mongo
            domain_item = SimpleStockItem(
                id=sid,
                tenant_id="1",
                name=name,
                category=category,
                unit=unit,
                min_stock_level=min_stock,
                is_active=True,
                transactions=[
                    StockTransaction(
                        id=tx_orm.id,
                        quantity=MeasuredQuantity(Decimal(str(initial_qty)), unit),
                        type=TransactionType.INPUT,
                    )
                ],
            )
            await stock_sync.sync(domain_item)

        print("Seeding recipes...")
        # Add Recipes
        recipes_data = [
            (301, 101, [(201, 1, "un")]),  # Água de Coco -> 1 Coco
            (302, 102, [(202, 50, "ml"), (203, 1, "un")]),  # Caipirinha -> 50ml cachaça + 1 limão
            (303, 103, [(204, 250, "g")]),  # Iscas Peixe -> 250g Peixe
            (304, 104, [(205, 300, "g")]),  # Camarão -> 300g camarão
            (305, 105, [(205, 50, "g"), (206, 1, "un")]),  # Pastel -> 50g camarão + 1 massa
            (306, 106, [(207, 250, "g")]),  # Açaí -> 250g polpa
            (307, 107, [(208, 0.25, "un")]),  # Suco abacaxi -> 0.25 abacaxi
        ]

        for rid, menu_item_id, ingredients in recipes_data:
            r_orm = RecipeORM(id=rid, menu_item_id=menu_item_id, tenant_id="1")
            db.add(r_orm)
            await db.flush()

            for stock_id, qty, unit in ingredients:
                ing_orm = RecipeIngredientORM(
                    recipe_id=rid,
                    stock_item_id=stock_id,
                    quantity_value=Decimal(str(qty)),
                    quantity_unit=unit,
                )
                db.add(ing_orm)
            await db.flush()

        print("Seeding default beach menu structure...")
        # Add Menu
        menu_orm = MenuORM(
            id=1,
            tenant_id="1",
            name="Cardápio Barraca do Sol",
            description="Sabores tropicais e delícias à beira-mar.",
            is_active=True,
            price_list_id=None,
        )
        db.add(menu_orm)
        await db.flush()

        # Categories and Map items to category
        categories = ["Entradas", "Petiscos", "Bebidas", "Sobremesas"]
        for cat in categories:
            for mi in menu_items:
                if mi.category_name == cat:
                    ci_orm = CategoryItemORM(menu_id=1, category_name=cat, menu_item_id=mi.id)
                    db.add(ci_orm)
            await db.flush()

        await db.commit()

        # Sync menu to Mongo
        menu_domain = Menu(
            id=1,
            tenant_id="1",
            name="Cardápio Barraca do Sol",
            description="Sabores tropicais e delícias à beira-mar.",
        )
        menu_domain.add_item_to_category("Entradas", 105)
        menu_domain.add_item_to_category("Petiscos", 103)
        menu_domain.add_item_to_category("Petiscos", 104)
        menu_domain.add_item_to_category("Bebidas", 101)
        menu_domain.add_item_to_category("Bebidas", 102)
        menu_domain.add_item_to_category("Bebidas", 107)
        menu_domain.add_item_to_category("Sobremesas", 106)
        menu_doc = await _resolve_menu_doc(db, menu_domain)
        await MenuReadModelSync(mongo_db).sync(menu_doc)

        print("Beach restaurant data successfully seeded and synced!")

    await close_postgres()
    await close_mongo()


if __name__ == "__main__":
    asyncio.run(seed())
