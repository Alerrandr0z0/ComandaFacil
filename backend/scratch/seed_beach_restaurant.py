# ruff: noqa: PLR0915, C901, PLR0912, PLR2004
# pyright: reportPrivateUsage=false
from __future__ import annotations

import asyncio
import datetime
import hashlib
import secrets
from decimal import Decimal

from sqlalchemy import delete, select

from app.auth.infrastructure.orm_models import EmployeeORM, SessionORM, TenantORM, UserTenantRoleORM
from app.kitchen.infrastructure.orm_models import KitchenOrderItemORM
from app.menu.api.routes import _resolve_menu_doc
from app.menu.domain.menu import Menu
from app.menu.infrastructure.mongo_sync import MenuReadModelSync
from app.menu.infrastructure.orm_models import (
    CategoryItemORM,
    MenuItemORM,
    MenuORM,
    PriceListItemORM,
    PriceListORM,
)
from app.order.infrastructure.orm_models import OrderFormItemORM, OrderFormORM
from app.payment.infrastructure.orm_models import PaymentORM
from app.settings import get_settings
from app.shared.database import (
    close_mongo,
    close_postgres,
    get_async_session,
    get_mongo_db,
    init_mongo,
    init_postgres,
)
from app.stock.domain.enums import TransactionType
from app.stock.domain.measured_quantity import MeasuredQuantity
from app.stock.domain.stock_item import SimpleStockItem
from app.stock.domain.transaction import StockTransaction
from app.stock.infrastructure.orm_models import (
    RecipeIngredientORM,
    RecipeORM,
    StockItemORM,
    StockTransactionORM,
)
from app.stock.infrastructure.stock_read_sync import StockReadModelSync


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"pbkdf2_sha256$100000${salt}${key.hex()}"

async def seed() -> None:
    settings = get_settings()
    await init_postgres(settings)
    await init_mongo(settings)

    mongo_db = get_mongo_db()

    async for db in get_async_session():
        print("Cleaning up old database records...")

        # Make sure tenant 1 exists
        tenant_orm = await db.scalar(select(TenantORM).where(TenantORM.id == 1))
        if not tenant_orm:
            tenant_orm = TenantORM(id=1, name="Barraca do Sol", plan_type="BASIC", is_active=True)
            db.add(tenant_orm)
            await db.flush()
        else:
            tenant_orm.name = "Barraca do Sol"

        # Clean all data for Tenant 1 to ensure a fresh, consistent seed
        await db.execute(delete(KitchenOrderItemORM).where(KitchenOrderItemORM.tenant_id == "1"))

        # Clean orders, items, payments
        order_forms_stmt = select(OrderFormORM.id).where(OrderFormORM.tenant_id == "1")
        order_ids = (await db.scalars(order_forms_stmt)).all()

        # Also include explicit IDs 2, 3, 4, 1002, 1003, 1004 just in case they exist from other runs
        all_order_ids_to_clean = list({*order_ids, 2, 3, 4, 1002, 1003, 1004})
        await db.execute(delete(OrderFormItemORM).where(OrderFormItemORM.order_id.in_(all_order_ids_to_clean)))
        await db.execute(delete(OrderFormORM).where(OrderFormORM.id.in_(all_order_ids_to_clean)))
        await db.execute(delete(PaymentORM).where(PaymentORM.tenant_id == "1"))

        # Clean auth roles for Tenant 1
        await db.execute(delete(SessionORM).where(SessionORM.tenant_id == 1))
        await db.execute(delete(UserTenantRoleORM).where(UserTenantRoleORM.tenant_id == 1))

        # Clean stock, recipes, menu
        await db.execute(delete(CategoryItemORM))
        await db.execute(delete(MenuORM).where(MenuORM.tenant_id == "1"))
        await db.execute(delete(RecipeIngredientORM))

        recipe_stmt = select(RecipeORM.id).where(RecipeORM.tenant_id == "1")
        recipe_ids = (await db.scalars(recipe_stmt)).all()
        if recipe_ids:
            await db.execute(delete(RecipeORM).where(RecipeORM.id.in_(recipe_ids)))

        await db.execute(delete(StockTransactionORM).where(StockTransactionORM.stock_item_id.in_(
            select(StockItemORM.id).where(StockItemORM.tenant_id == "1")
        )))
        await db.execute(delete(StockItemORM).where(StockItemORM.tenant_id == "1"))
        await db.execute(delete(MenuItemORM).where(MenuItemORM.tenant_id == "1"))
        await db.flush()

        # Clean MongoDB collections
        await mongo_db["stock_read"].delete_many({"tenant_id": "1"})
        await mongo_db["menu_read_models"].delete_many({"tenant_id": "1"})
        await mongo_db["orders_read"].delete_many({"tenant_id": "1"})
        await mongo_db["order_history"].delete_many({"tenant_id": "1"})
        await mongo_db["kitchen_read"].delete_many({"tenant_id": "1"})

        print("Seeding beach restaurant employees...")
        employees_data = [
            (501, "Lucas Gerente", "lucas.gerente@barracadosol.com", "MANAGER"),
            (502, "Marcos Garçom", "marcos.garcom@barracadosol.com", "WAITER"),
            (503, "Sandra Cozinheira", "sandra.cozinheira@barracadosol.com", "COOK"),
            (504, "Roberta Caixa", "roberta.caixa@barracadosol.com", "CASHIER"),
            (999, "Admin Global", "admin@comanda.facil", "SUPER_ADMIN"),
        ]

        for emp_id, name, email, role in employees_data:
            existing_emp = await db.scalar(select(EmployeeORM).where(
                (EmployeeORM.email == email) | (EmployeeORM.id == emp_id)
            ))
            if existing_emp:
                await db.execute(delete(UserTenantRoleORM).where(UserTenantRoleORM.employee_id == existing_emp.id))
                await db.execute(delete(EmployeeORM).where(EmployeeORM.id == existing_emp.id))
                await db.flush()

            emp = EmployeeORM(
                id=emp_id,
                name=name,
                email=email,
                password_hash=hash_password("password123")
            )
            db.add(emp)
            await db.flush()

            role_orm = UserTenantRoleORM(
                tenant_id=1,
                employee_id=emp.id,
                role_type=role,
                is_active=True
            )
            db.add(role_orm)
            await db.flush()

        print("Seeding beach restaurant menu items...")
        menu_items_data = [
            # Entradas
            (101, "Caldinho de Feijão", "Caldinho temperado servido com torresmo e cheiro verde.", 12.00, "Entradas", "GRILL"),
            (102, "Casquinha de Siri", "Siri desfiado gratinado com queijo e farofa.", 18.00, "Entradas", "GRILL"),
            (103, "Queijo Coalho na Brasa", "Espeto de queijo coalho grelhado com mel de engenho.", 15.00, "Entradas", "GRILL"),
            # Petiscos
            (104, "Camarão ao Alho e Óleo", "Camarão grelhado salpicado com alho dourado e azeite.", 65.00, "Petiscos", "GRILL"),
            (105, "Lula à Dorê", "Anéis de lula empanados e fritos, servidos com limão.", 55.00, "Petiscos", "GRILL"),
            (106, "Isca de Peixe Crocante", "Tiras de peixe fresco empanadas servidas com molho tártaro.", 45.00, "Petiscos", "GRILL"),
            (107, "Porção de Batata Frita", "Batatas fritas crocantes com sal e orégano.", 25.00, "Petiscos", "GRILL"),
            # Pratos Principais
            (108, "Moqueca de Camarão", "Camarão cozido no leite de coco, azeite de dendê e coentro.", 120.00, "Pratos Principais", "GRILL"),
            (109, "Peixe Frito Inteiro", "Pargo inteiro frito na hora, acompanha arroz e vinagrete.", 95.00, "Pratos Principais", "GRILL"),
            (110, "Filé à Parmegiana", "Filé mignon empanado, coberto com queijo e molho de tomate.", 85.00, "Pratos Principais", "GRILL"),
            # Bebidas
            (111, "Água de Coco", "Coco gelado servido na fruta natural.", 8.00, "Bebidas", "BEVERAGE"),
            (112, "Caipirinha de Limão", "Cachaça artesanal, limão espremido e açúcar.", 18.00, "Bebidas", "BEVERAGE"),
            (113, "Suco de Abacaxi com Hortelã", "Suco natural e refrescante feito na hora.", 10.00, "Bebidas", "BEVERAGE"),
            (114, "Cerveja Heineken Long Neck", "Cerveja Heineken gelada.", 12.00, "Bebidas", "BEVERAGE"),
            # Sobremesas
            (115, "Açaí na Tigela", "Açaí completo com granola, banana fatiada e leite condensado.", 22.00, "Sobremesas", "GRILL"),
            (116, "Pudim de Leite", "Pudim de leite condensado tradicional com calda de caramelo.", 12.00, "Sobremesas", "GRILL"),
        ]

        # Override preparation_profile per item (only ready-to-serve drinks skip prep)
        no_prep_ids = {111, 114}  # Água de Coco, Cerveja Heineken
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
                preparation_profile="NO_PREP" if mid in no_prep_ids else "STANDARD",
            )
            db.add(mi)
            menu_items.append(mi)

        await db.flush()

        print("Seeding stock items and transactions...")
        stock_items_data = [
            (201, "Coco Verde", "BEVERAGE", "un", 10.0, 150),
            (202, "Cachaça Artesanal", "BEVERAGE", "ml", 1000.0, 10000),
            (203, "Limão", "RAW_MATERIAL", "un", 15.0, 300),
            (204, "Peixe Cação", "RAW_MATERIAL", "g", 1000.0, 15000),
            (205, "Camarão Médio", "RAW_MATERIAL", "g", 1000.0, 20000),
            (206, "Lula Inteira", "RAW_MATERIAL", "g", 1000.0, 10000),
            (207, "Polpa de Siri", "RAW_MATERIAL", "g", 500.0, 5000),
            (208, "Feijão Preto", "RAW_MATERIAL", "g", 1000.0, 8000),
            (209, "Queijo Coalho Espeto", "RAW_MATERIAL", "un", 20.0, 100),
            (210, "Batata Pré-Frita Congelada", "RAW_MATERIAL", "g", 2000.0, 25000),
            (211, "Abacaxi", "RAW_MATERIAL", "un", 5.0, 80),
            (212, "Heineken LN", "BEVERAGE", "un", 24.0, 240),
            (213, "Polpa de Açaí", "RAW_MATERIAL", "g", 2000.0, 15000),
            (214, "Pudim Caseiro", "RAW_MATERIAL", "un", 5.0, 30),
            (215, "Filé Mignon", "RAW_MATERIAL", "g", 1000.0, 12000),
            (216, "Pargo Inteiro", "RAW_MATERIAL", "un", 5.0, 30),
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

            tx_orm = StockTransactionORM(
                stock_item_id=sid,
                transaction_type="INPUT",
                quantity_value=Decimal(str(initial_qty)),
                quantity_unit=unit,
            )
            db.add(tx_orm)
            await db.flush()

            domain_item = SimpleStockItem(
                id=sid,
                tenant_id="1",
                name=name,
                category=category,
                unit=unit,
                min_stock_level=min_stock,
                is_active=True,
                transactions=[
                    StockTransaction(id=tx_orm.id, quantity=MeasuredQuantity(Decimal(str(initial_qty)), unit), type=TransactionType.INPUT, reason="Seed initial stock")
                ]
            )
            await stock_sync.sync(domain_item)

        print("Seeding recipes...")
        recipes_data = [
            (301, 101, [(208, 150, "g")]),
            (302, 102, [(207, 100, "g")]),
            (303, 103, [(209, 1, "un")]),
            (304, 104, [(205, 300, "g")]),
            (305, 105, [(206, 250, "g")]),
            (306, 106, [(204, 250, "g")]),
            (307, 107, [(210, 400, "g")]),
            (308, 108, [(205, 400, "g")]),
            (309, 109, [(216, 1, "un")]),
            (310, 110, [(215, 250, "g")]),
            (311, 111, [(201, 1, "un")]),
            (312, 112, [(202, 50, "ml"), (203, 1, "un")]),
            (313, 113, [(211, 0.25, "un")]),
            (314, 114, [(212, 1, "un")]),
            (315, 115, [(213, 250, "g")]),
            (316, 116, [(214, 1, "un")]),
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
        menu_orm = MenuORM(
            id=1,
            tenant_id="1",
            name="Cardápio Barraca do Sol",
            description="Sabores tropicais e delícias à beira-mar.",
            is_active=True,
        )
        db.add(menu_orm)
        await db.flush()

        categories = ["Entradas", "Petiscos", "Pratos Principais", "Bebidas", "Sobremesas"]
        for cat in categories:
            for mi in menu_items:
                if mi.category_name == cat:
                    ci_orm = CategoryItemORM(menu_id=1, category_name=cat, menu_item_id=mi.id)
                    db.add(ci_orm)
            await db.flush()

        await db.commit()
        await db.begin()

        # Sync menu to Mongo
        menu_domain = Menu(
            id=1,
            tenant_id="1",
            name="Cardápio Barraca do Sol",
            description="Sabores tropicais e delícias à beira-mar.",
        )
        for cat in categories:
            for mi in menu_items:
                if mi.category_name == cat:
                    menu_domain.add_item_to_category(cat, mi.id)
        menu_doc = await _resolve_menu_doc(db, menu_domain)
        await MenuReadModelSync(mongo_db).sync(menu_doc)

        print("Seeding PriceList with Happy Hour overrides...")
        pl_orm = PriceListORM(
            id=1, tenant_id="1", menu_id=1, name="Happy Hour",
            description="Preços especiais para bebidas no happy hour (18h-20h)",
            is_active=True,
        )
        db.add(pl_orm)
        await db.flush()

        # Override prices for drink items during happy hour
        drink_overrides = [
            (112, Decimal("12.00")),   # Caipirinha: base 18 → 12
            (113, Decimal("15.00")),   # Caipirinha de Frutas: base 22 → 15
            (114, Decimal("6.00")),    # Água de Coco: base 8 → 6
            (115, Decimal("10.00")),   # Heineken: base 12 → 10
        ]
        for menu_item_id, happy_price in drink_overrides:
            pli_orm = PriceListItemORM(
                id=menu_item_id,
                price_list_id=1,
                menu_item_id=menu_item_id,
                price=happy_price,
            )
            db.add(pli_orm)
        await db.flush()

        # Second PriceList: "Diurno" — no overrides (base prices only)
        pl_diurno = PriceListORM(
            id=2, tenant_id="1", menu_id=1, name="Diurno",
            description="Preços base do cardápio (sem descontos)",
            is_active=True,
        )
        db.add(pl_diurno)
        await db.flush()

        # Associate PriceList "Happy Hour" as active
        menu_orm.active_price_list_id = 1
        await db.flush()

        # Re-sync menu to MongoDB with PriceList overrides
        menu_domain_with_pl = Menu(
            id=1, tenant_id="1", name="Cardápio Barraca do Sol",
            description="Sabores tropicais e delícias à beira-mar.",
            price_list_id=1,
        )
        for cat in categories:
            for mi in menu_items:
                if mi.category_name == cat:
                    menu_domain_with_pl.add_item_to_category(cat, mi.id)
        menu_doc_with_pl = await _resolve_menu_doc(db, menu_domain_with_pl)
        await MenuReadModelSync(mongo_db).sync(menu_doc_with_pl)
        print("PriceLists seeded and synced.")

        print("Seeding active orders (Salão)...")
        # In the frontend, the order_id for Table 2 is 2, Table 3 is 3, Table 4 is 4

        # Mesa 2 (OPEN)
        order_m2 = OrderFormORM(id=2, tenant_id="1", display_code="MESA-02", state="OPEN", table_number=2, fulfillment_type="TABLE")
        db.add(order_m2)
        await db.flush()

        item_m2_1 = OrderFormItemORM(id=60021, order_id=2, menu_item_id=112, name_cpy="Caipirinha de Limão", price_cpy=Decimal("18.00"), station_type_cpy="BEVERAGE", quantity=2)
        item_m2_2 = OrderFormItemORM(id=60022, order_id=2, menu_item_id=105, name_cpy="Lula à Dorê", price_cpy=Decimal("55.00"), station_type_cpy="GRILL", quantity=1)
        item_m2_3 = OrderFormItemORM(id=60023, order_id=2, menu_item_id=106, name_cpy="Isca de Peixe Crocante", price_cpy=Decimal("45.00"), station_type_cpy="GRILL", quantity=1)
        db.add(item_m2_1)
        db.add(item_m2_2)
        db.add(item_m2_3)
        await db.flush()

        # Mesa 3 (OPEN)
        order_m3 = OrderFormORM(id=3, tenant_id="1", state="OPEN", display_code="MESA-03", table_number=3, fulfillment_type="TABLE")
        db.add(order_m3)
        await db.flush()

        item_m3_1 = OrderFormItemORM(id=60031, order_id=3, menu_item_id=111, name_cpy="Água de Coco", price_cpy=Decimal("8.00"), station_type_cpy="BEVERAGE", quantity=3)
        item_m3_2 = OrderFormItemORM(id=60032, order_id=3, menu_item_id=103, name_cpy="Queijo Coalho na Brasa", price_cpy=Decimal("15.00"), station_type_cpy="GRILL", quantity=2)
        db.add(item_m3_1)
        db.add(item_m3_2)
        await db.flush()

        # Mesa 4 (PAYMENT_REQUESTED)
        order_m4 = OrderFormORM(id=4, tenant_id="1", state="OPEN", display_code="MESA-04", table_number=4, fulfillment_type="TABLE", payment_requested=True)
        db.add(order_m4)
        await db.flush()

        item_m4_1 = OrderFormItemORM(id=60041, order_id=4, menu_item_id=108, name_cpy="Moqueca de Camarão", price_cpy=Decimal("120.00"), station_type_cpy="GRILL", quantity=1)
        item_m4_2 = OrderFormItemORM(id=60042, order_id=4, menu_item_id=107, name_cpy="Porção de Batata Frita", price_cpy=Decimal("25.00"), station_type_cpy="GRILL", quantity=1)
        item_m4_3 = OrderFormItemORM(id=60043, order_id=4, menu_item_id=114, name_cpy="Cerveja Heineken Long Neck", price_cpy=Decimal("12.00"), station_type_cpy="BEVERAGE", quantity=4)
        db.add(item_m4_1)
        db.add(item_m4_2)
        db.add(item_m4_3)
        await db.flush()

        pm4 = PaymentORM(order_id=4, tenant_id="1", amount=Decimal("193.00"), method="CREDIT_CARD", status="PENDING")
        db.add(pm4)
        await db.flush()

        print("Seeding active kitchen preparation items...")
        kitchen_seed_items = [
            # Order 2 - Mesa 2
            KitchenOrderItemORM(id=7001, correlation_id=60022, name_cpy="Lula à Dorê", station_type_cpy="GRILL", tenant_id="1", state="PREPARING", preparation_profile="STANDARD"),
            KitchenOrderItemORM(id=7002, correlation_id=60023, name_cpy="Isca de Peixe Crocante", station_type_cpy="GRILL", tenant_id="1", state="WAITING", preparation_profile="STANDARD"),
            KitchenOrderItemORM(id=7003, correlation_id=60032, name_cpy="Queijo Coalho na Brasa", station_type_cpy="GRILL", tenant_id="1", state="READY", preparation_profile="STANDARD"),
            # Missing beverage items (Mesa 2 - Caipirinha, Mesa 3 - Agua de Coco, Mesa 4 - Heineken)
            KitchenOrderItemORM(id=7004, correlation_id=60021, name_cpy="Caipirinha de Limão", station_type_cpy="BEVERAGE", tenant_id="1", state="WAITING", preparation_profile="STANDARD"),
            KitchenOrderItemORM(id=7005, correlation_id=60031, name_cpy="Água de Coco", station_type_cpy="BEVERAGE", tenant_id="1", state="WAITING", preparation_profile="NO_PREP"),
            KitchenOrderItemORM(id=7006, correlation_id=60043, name_cpy="Cerveja Heineken Long Neck", station_type_cpy="BEVERAGE", tenant_id="1", state="WAITING", preparation_profile="NO_PREP"),
            # Missing Mesa 4 GRILL items
            KitchenOrderItemORM(id=7007, correlation_id=60041, name_cpy="Moqueca de Camarão", station_type_cpy="GRILL", tenant_id="1", state="WAITING", preparation_profile="STANDARD"),
            KitchenOrderItemORM(id=7008, correlation_id=60042, name_cpy="Porção de Batata Frita", station_type_cpy="GRILL", tenant_id="1", state="WAITING", preparation_profile="STANDARD"),
        ]
        for k in kitchen_seed_items:
            db.add(k)
        await db.flush()

        # Sync ALL kitchen items to MongoDB "kitchen_read"
        now = datetime.datetime.now(datetime.UTC)
        kitchen_docs = [
            {
                "kitchen_item_id": 7001,
                "correlation_id": 60022,
                "tenant_id": "1",
                "name_cpy": "Lula à Dorê",
                "station_type_cpy": "GRILL",
                "preparation_profile": "STANDARD",
                "state": "PREPARING",
                "started_at": now,
                "completed_at": None,
                "created_at": now,
            },
            {
                "kitchen_item_id": 7002,
                "correlation_id": 60023,
                "tenant_id": "1",
                "name_cpy": "Isca de Peixe Crocante",
                "station_type_cpy": "GRILL",
                "preparation_profile": "STANDARD",
                "state": "WAITING",
                "started_at": None,
                "completed_at": None,
                "created_at": now,
            },
            {
                "kitchen_item_id": 7003,
                "correlation_id": 60032,
                "tenant_id": "1",
                "name_cpy": "Queijo Coalho na Brasa",
                "station_type_cpy": "GRILL",
                "preparation_profile": "STANDARD",
                "state": "READY",
                "started_at": None,
                "completed_at": None,
                "created_at": now,
            },
            {
                "kitchen_item_id": 7004,
                "correlation_id": 60021,
                "tenant_id": "1",
                "name_cpy": "Caipirinha de Limão",
                "station_type_cpy": "BEVERAGE",
                "preparation_profile": "NO_PREP",
                "state": "WAITING",
                "started_at": None,
                "completed_at": None,
                "created_at": now,
            },
            {
                "kitchen_item_id": 7005,
                "correlation_id": 60031,
                "tenant_id": "1",
                "name_cpy": "Água de Coco",
                "station_type_cpy": "BEVERAGE",
                "preparation_profile": "NO_PREP",
                "state": "WAITING",
                "started_at": None,
                "completed_at": None,
                "created_at": now,
            },
            {
                "kitchen_item_id": 7006,
                "correlation_id": 60043,
                "tenant_id": "1",
                "name_cpy": "Cerveja Heineken Long Neck",
                "station_type_cpy": "BEVERAGE",
                "preparation_profile": "NO_PREP",
                "state": "WAITING",
                "started_at": None,
                "completed_at": None,
                "created_at": now,
            },
            {
                "kitchen_item_id": 7007,
                "correlation_id": 60041,
                "tenant_id": "1",
                "name_cpy": "Moqueca de Camarão",
                "station_type_cpy": "GRILL",
                "preparation_profile": "STANDARD",
                "state": "WAITING",
                "started_at": None,
                "completed_at": None,
                "created_at": now,
            },
            {
                "kitchen_item_id": 7008,
                "correlation_id": 60042,
                "tenant_id": "1",
                "name_cpy": "Porção de Batata Frita",
                "station_type_cpy": "GRILL",
                "preparation_profile": "STANDARD",
                "state": "WAITING",
                "started_at": None,
                "completed_at": None,
                "created_at": now,
            },
        ]
        await mongo_db["kitchen_read"].insert_many(kitchen_docs)

        print("Seeding past closed orders and payments (Analytics history)...")
        methods = ["PIX", "CREDIT_CARD", "DEBIT_CARD", "CASH"]

        historical_item_pools = [
            [(101, "Caldinho de Feijão", "12.00", "GRILL"), (114, "Cerveja Heineken Long Neck", "12.00", "BEVERAGE")],
            [(104, "Camarão ao Alho e Óleo", "65.00", "GRILL"), (112, "Caipirinha de Limão", "18.00", "BEVERAGE")],
            [(106, "Isca de Peixe Crocante", "45.00", "GRILL"), (107, "Porção de Batata Frita", "25.00", "GRILL"), (114, "Cerveja Heineken Long Neck", "12.00", "BEVERAGE")],
            [(108, "Moqueca de Camarão", "120.00", "GRILL"), (111, "Água de Coco", "8.00", "BEVERAGE")],
            [(115, "Açaí na Tigela", "22.00", "GRILL")],
        ]

        order_seq = 2000
        for i in range(25):
            order_seq += 1

            # To populate the daily dashboard, we make 8 of the orders be created TODAY
            if i < 8:
                order_time = now - datetime.timedelta(minutes=30 * i)
            else:
                day_offset = (i % 6) + 1
                hour_offset = (i * 2) % 12 + 10
                order_time = now - datetime.timedelta(days=day_offset, hours=hour_offset)

            order_hist = OrderFormORM(
                id=order_seq,
                tenant_id="1",
                display_code=str(order_seq),
                state="CLOSED",
                table_number=(i % 10) + 5,
                fulfillment_type="TABLE"
            )
            db.add(order_hist)
            await db.flush()

            pool = historical_item_pools[i % len(historical_item_pools)]
            total_amount = Decimal("0.00")
            items_list = []
            history_items_list = []

            item_seq = 50000 + i * 10
            for menu_item_id, item_name, item_price_str, station in pool:
                item_seq += 1
                qty = (i % 2) + 1
                price = Decimal(item_price_str)
                subtotal = price * qty
                total_amount += subtotal

                oh_item = OrderFormItemORM(
                    id=item_seq,
                    order_id=order_seq,
                    menu_item_id=menu_item_id,
                    name_cpy=item_name,
                    price_cpy=price,
                    station_type_cpy=station,
                    quantity=qty
                )
                db.add(oh_item)

                items_list.append({
                    "id": item_seq,
                    "menu_item_id": menu_item_id,
                    "name": item_name,
                    "category": station,
                    "price": float(price),
                    "quantity": qty,
                    "subtotal": float(subtotal)
                })

                history_items_list.append({
                    "id": item_seq,
                    "menu_item_id": menu_item_id,
                    "name": item_name,
                    "price": str(price),
                    "station_type": station,
                    "quantity": qty,
                    "notes": "",
                    "subtotal": str(subtotal)
                })
            await db.flush()

            pay_hist = PaymentORM(
                order_id=order_seq,
                tenant_id="1",
                amount=total_amount,
                method=methods[i % len(methods)],
                status="CONFIRMED",
                gateway_ref=f"gtw_ref_{secrets.token_hex(8)}"
            )
            db.add(pay_hist)
            await db.flush()

            # Sync to Mongo "orders_read" (for analytics queries)
            mongo_doc = {
                "order_id": order_seq,
                "tenant_id": "1",
                "total": float(total_amount),
                "items": items_list,
                "created_at": order_time
            }
            await mongo_db["orders_read"].replace_one(
                {"order_id": order_seq, "tenant_id": "1"},
                mongo_doc,
                upsert=True
            )

            # Sync to Mongo "order_history" (for history page)
            history_doc = {
                "order_id": order_seq,
                "tenant_id": "1",
                "total": str(total_amount),
                "state": "CLOSED",
                "fulfillment": {
                    "type": "TABLE",
                    "fee": "0.00",
                    "table": {
                        "table_number": (i % 10) + 5
                    }
                },
                "items": history_items_list,
                "closed_at": order_time.isoformat()
            }
            await mongo_db["order_history"].replace_one(
                {"order_id": order_seq, "tenant_id": "1"},
                history_doc,
                upsert=True
            )

        await db.commit()
        print("Beach restaurant data successfully seeded and synced!")

    await close_postgres()
    await close_mongo()

if __name__ == "__main__":
    asyncio.run(seed())
