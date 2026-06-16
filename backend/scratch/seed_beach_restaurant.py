# ruff: noqa: PLR0915, C901, PLR0912, PLR2004, S105, S311, PLW0602, ERA001, PERF403, ARG001, F841, SIM113
# pyright: reportPrivateUsage=false
from __future__ import annotations

import asyncio
import calendar
import datetime
import hashlib
import random
import secrets
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.auth.infrastructure.orm_models import (
    AuditLogORM,
    EmployeeORM,
    EmployeePermissionORM,
    SessionORM,
    TenantORM,
    UserTenantRoleORM,
)
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

# ─── Helpers ──────────────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"pbkdf2_sha256$100000${salt}${key.hex()}"


def fmt_ts(dt: datetime.datetime) -> str:
    return dt.isoformat()


def fmt_price(value: float) -> str:
    return f"{value:.2f}"


def random_choice_weighted(options: list[tuple[Any, float]]) -> Any:
    total = sum(w for _, w in options)
    r = secrets.randbelow(10000) / 10000 * total
    cumulative = 0.0
    for item, weight in options:
        cumulative += weight
        if r <= cumulative:
            return item
    return options[-1][0]


@dataclass(frozen=True)
class ComboItem:
    menu_item_id: int
    quantity: int


@dataclass(frozen=True)
class Combo:
    items: tuple[ComboItem, ...]
    label: str


# ─── ID Ranges ────────────────────────────────────────────────────────────────

ID_ORDER_GLOBAL = 100_000
ID_PAYMENT_GLOBAL = 200_000
ID_KITCHEN_GLOBAL = 300_000
ID_AUDIT_GLOBAL = 400_000
ID_TX_GLOBAL = 500_000

ID_COUNTERS: dict[str, int] = {}


def next_id(key: str) -> int:
    global ID_COUNTERS
    base = {
        "order": ID_ORDER_GLOBAL,
        "payment": ID_PAYMENT_GLOBAL,
        "kitchen": ID_KITCHEN_GLOBAL,
        "audit": ID_AUDIT_GLOBAL,
        "tx": ID_TX_GLOBAL,
    }[key]
    ID_COUNTERS[key] = ID_COUNTERS.get(key, 0) + 1
    return base + ID_COUNTERS[key]


# ─── Tenant Configurations ────────────────────────────────────────────────────

# Each tenant defines: employees, menu_items, stock_items, recipes, combos (for
# historical order generation), opening hours, and order patterns.

# ───── Tenant 1: Barraca do Sol (beach restaurant) ───────────────────────────

T1 = "1"

T1_EMPLOYEES: list[tuple[int, str, str, str]] = [
    (501, "Lucas Gerente", "lucas.gerente@barracadosol.com", "MANAGER"),
    (502, "Marcos Garçom", "marcos.garcom@barracadosol.com", "WAITER"),
    (503, "Sandra Cozinheira", "sandra.cozinheira@barracadosol.com", "COOK"),
    (504, "Roberta Caixa", "roberta.caixa@barracadosol.com", "CASHIER"),
]

T1_MENU_ITEMS: list[tuple[int, str, str, float, str, str]] = [
    # Entradas
    (
        101,
        "Caldinho de Feijão",
        "Caldinho temperado servido com torresmo e cheiro verde.",
        12.00,
        "Entradas",
        "GRILL",
    ),
    (
        102,
        "Casquinha de Siri",
        "Siri desfiado gratinado com queijo e farofa.",
        18.00,
        "Entradas",
        "GRILL",
    ),
    (
        103,
        "Queijo Coalho na Brasa",
        "Espeto de queijo coalho grelhado com mel de engenho.",
        15.00,
        "Entradas",
        "GRILL",
    ),
    # Petiscos
    (
        104,
        "Camarão ao Alho e Óleo",
        "Camarão grelhado salpicado com alho dourado e azeite.",
        65.00,
        "Petiscos",
        "GRILL",
    ),
    (
        105,
        "Lula à Dorê",
        "Anéis de lula empanados e fritos, servidos com limão.",
        55.00,
        "Petiscos",
        "GRILL",
    ),
    (
        106,
        "Isca de Peixe Crocante",
        "Tiras de peixe fresco empanadas servidas com molho tártaro.",
        45.00,
        "Petiscos",
        "GRILL",
    ),
    (
        107,
        "Porção de Batata Frita",
        "Batatas fritas crocantes com sal e orégano.",
        25.00,
        "Petiscos",
        "GRILL",
    ),
    # Pratos Principais
    (
        108,
        "Moqueca de Camarão",
        "Camarão cozido no leite de coco, azeite de dendê e coentro.",
        120.00,
        "Pratos Principais",
        "GRILL",
    ),
    (
        109,
        "Peixe Frito Inteiro",
        "Pargo inteiro frito na hora, acompanha arroz e vinagrete.",
        95.00,
        "Pratos Principais",
        "GRILL",
    ),
    (
        110,
        "Filé à Parmegiana",
        "Filé mignon empanado, coberto com queijo e molho de tomate.",
        85.00,
        "Pratos Principais",
        "GRILL",
    ),
    # Bebidas
    (111, "Água de Coco", "Coco gelado servido na fruta natural.", 8.00, "Bebidas", "BEVERAGE"),
    (
        112,
        "Caipirinha de Limão",
        "Cachaça artesanal, limão espremido e açúcar.",
        18.00,
        "Bebidas",
        "BEVERAGE",
    ),
    (
        113,
        "Suco de Abacaxi com Hortelã",
        "Suco natural e refrescante feito na hora.",
        10.00,
        "Bebidas",
        "BEVERAGE",
    ),
    (114, "Cerveja Heineken Long Neck", "Cerveja Heineken gelada.", 12.00, "Bebidas", "BEVERAGE"),
    # Sobremesas
    (
        115,
        "Açaí na Tigela",
        "Açaí completo com granola, banana fatiada e leite condensado.",
        22.00,
        "Sobremesas",
        "GRILL",
    ),
    (
        116,
        "Pudim de Leite",
        "Pudim de leite condensado tradicional com calda de caramelo.",
        12.00,
        "Sobremesas",
        "GRILL",
    ),
]

T1_NO_PREP_IDS = {111, 114}

T1_STOCK_ITEMS: list[tuple[int, str, str, str, float, float]] = [
    # Insumos (Raw Materials)
    (201, "Coco Verde", "RAW_MATERIAL", "un", 20.0, 1000000.0),
    (202, "Cachaça Artesanal", "RAW_MATERIAL", "ml", 1000.0, 1000000.0),
    (203, "Limão", "RAW_MATERIAL", "un", 30.0, 1000000.0),
    (204, "Peixe Cação", "RAW_MATERIAL", "g", 2000.0, 1000000.0),
    (205, "Camarão Médio", "RAW_MATERIAL", "g", 2000.0, 1000000.0),
    (206, "Lula Inteira", "RAW_MATERIAL", "g", 2000.0, 1000000.0),
    (207, "Polpa de Siri", "RAW_MATERIAL", "g", 1000.0, 1000000.0),
    (208, "Feijão Preto", "RAW_MATERIAL", "g", 2000.0, 1000000.0),
    (209, "Queijo Coalho Espeto", "RAW_MATERIAL", "un", 40.0, 1000000.0),
    (210, "Batata Pré-Frita Congelada", "RAW_MATERIAL", "g", 5000.0, 1000000.0),
    (211, "Abacaxi", "RAW_MATERIAL", "un", 10.0, 1000000.0),
    (212, "Heineken LN", "RAW_MATERIAL", "un", 48.0, 1000000.0),
    (213, "Polpa de Açaí", "RAW_MATERIAL", "g", 5000.0, 1000000.0),
    (214, "Pudim Caseiro", "RAW_MATERIAL", "un", 10.0, 1000000.0),
    (215, "Filé Mignon", "RAW_MATERIAL", "g", 2000.0, 1000000.0),
    (216, "Pargo Inteiro", "RAW_MATERIAL", "un", 10.0, 1000000.0),
    # Embalagens (Packaging)
    (217, "Caixa de Isopor Takeaway", "PACKAGING", "un", 50.0, 1000000.0),
    (218, "Copo Plástico 400ml", "PACKAGING", "un", 100.0, 1000000.0),
    (219, "Canudo de Papel", "PACKAGING", "un", 100.0, 1000000.0),
    (220, "Guardanapo de Papel (PCT)", "PACKAGING", "un", 20.0, 1000000.0),
    # Suplementos/Outros (Supplements/Others)
    (221, "Detergente Neutro 5L", "SUPPLEMENT", "un", 2.0, 1000000.0),
    (222, "Álcool em Gel 70% 5L", "SUPPLEMENT", "un", 2.0, 1000000.0),
    (223, "Papel Toalha Cozinha", "SUPPLEMENT", "un", 12.0, 1000000.0),
    (224, "Gás GLP 13kg", "OTHER", "un", 1.0, 1000000.0),
]

T1_RECIPES: list[tuple[int, int, list[tuple[int, float, str]]]] = [
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

T1_COMBOS: list[tuple[tuple[tuple[int, int], ...], str, float]] = [
    # Leve / petisco (peso alto — mais comum)
    (((107, 1), (114, 1)), "Batata + Heineken", 0.18),
    (((106, 1), (111, 1)), "Isca de Peixe + Água de Coco", 0.12),
    (((105, 1), (112, 1)), "Lula à Dorê + Caipirinha", 0.08),
    # Bebidas rápidas
    (((111, 1),), "Água de Coco", 0.10),
    (((114, 2),), "2 Heinekens", 0.08),
    (((112, 1),), "Caipirinha", 0.06),
    (((113, 1),), "Suco de Abacaxi", 0.05),
    # Almoço completo
    (((101, 1), (109, 1), (113, 1), (115, 1)), "Caldinho + Peixe + Suco + Açaí", 0.06),
    (((103, 1), (108, 1), (114, 1), (116, 1)), "Queijo Coalho + Moqueca + Heineken + Pudim", 0.05),
    (((102, 1), (110, 1), (112, 1)), "Casquinha + Filé + Caipirinha", 0.04),
    # Jantar
    (((104, 1), (108, 1), (114, 1)), "Camarão Alho + Moqueca + Heineken", 0.04),
    (((107, 2), (114, 3)), "2 Batatas + 3 Heinekens (grupo)", 0.04),
    # Sobremesa
    (((115, 1),), "Açaí na Tigela", 0.05),
    (((116, 1),), "Pudim de Leite", 0.03),
    # Grupo grande
    (((104, 2), (107, 2), (114, 4)), "2 Camarão + 2 Batata + 4 Heineken", 0.02),
]


# ───── Tenant 2: Pizza da Vila (pizzeria) ────────────────────────────────────

T2 = "2"

T2_EMPLOYEES: list[tuple[int, str, str, str]] = [
    (601, "Carlos Dono", "carlos.dono@pizzadavila.com", "MANAGER"),
    (602, "Ana Garçonete", "ana.garconete@pizzadavila.com", "WAITER"),
    (603, "Pedro Pizzaiolo", "pedro.pizzaiolo@pizzadavila.com", "COOK"),
    (604, "Julia Caixa", "julia.caixa@pizzadavila.com", "CASHIER"),
]

T2_MENU_ITEMS: list[tuple[int, str, str, float, str, str]] = [
    (301, "Pizza Margherita", "Molho de tomate, mussarela e manjericão.", 42.00, "Pizzas", "GRILL"),
    (302, "Pizza Pepperoni", "Pepperoni e mussarela.", 48.00, "Pizzas", "GRILL"),
    (
        303,
        "Pizza Portuguesa",
        "Presunto, mussarela, ovo, cebola e pimentão.",
        50.00,
        "Pizzas",
        "GRILL",
    ),
    (304, "Pizza Frango com Catupiry", "Frango desfiado e catupiry.", 46.00, "Pizzas", "GRILL"),
    (305, "Pizza Calabresa", "Calabresa fatiada, cebola e mussarela.", 44.00, "Pizzas", "GRILL"),
    (
        306,
        "Pizza Quatro Queijos",
        "Mussarela, provolone, parmesão e gorgonzola.",
        52.00,
        "Pizzas",
        "GRILL",
    ),
    (
        307,
        "Pizza Vegetariana",
        "Legumes grelhados, mussarela e molho de tomate.",
        42.00,
        "Pizzas",
        "GRILL",
    ),
    (308, "Pizza Doce de Leite", "Doce de leite, banana e canela.", 38.00, "Pizzas Doces", "GRILL"),
    (309, "Coca-Cola Lata", "Refrigerante Coca-Cola 350ml.", 6.00, "Bebidas", "BEVERAGE"),
    (310, "Guaraná Antarctica Lata", "Refrigerante Guaraná 350ml.", 6.00, "Bebidas", "BEVERAGE"),
    (311, "Suco de Laranja", "Suco natural de laranja.", 8.00, "Bebidas", "BEVERAGE"),
    (312, "Heineken Long Neck", "Cerveja Heineken 355ml.", 10.00, "Bebidas", "BEVERAGE"),
    (313, "Brahma Chopp 300ml", "Chopp Brahma 300ml.", 8.00, "Bebidas", "BEVERAGE"),
    (314, "Água Mineral", "Água mineral sem gás 500ml.", 4.00, "Bebidas", "BEVERAGE"),
    (
        315,
        "Pudim de Leite",
        "Pudim tradicional com calda de caramelo.",
        14.00,
        "Sobremesas",
        "GRILL",
    ),
    (
        316,
        "Petit Gateau",
        "Bolo de chocolate com recheio cremoso e sorvete.",
        22.00,
        "Sobremesas",
        "GRILL",
    ),
]

T2_NO_PREP_IDS = {309, 310, 311, 312, 313, 314}

T2_STOCK_ITEMS: list[tuple[int, str, str, str, float, float]] = [
    # Insumos (Raw Materials)
    (401, "Farinha de Trigo", "RAW_MATERIAL", "g", 5000.0, 1000000.0),
    (402, "Molho de Tomate", "RAW_MATERIAL", "ml", 1000.0, 1000000.0),
    (403, "Mussarela", "RAW_MATERIAL", "g", 2000.0, 1000000.0),
    (404, "Pepperoni", "RAW_MATERIAL", "g", 500.0, 1000000.0),
    (405, "Presunto", "RAW_MATERIAL", "g", 500.0, 1000000.0),
    (406, "Frango Desfiado", "RAW_MATERIAL", "g", 500.0, 1000000.0),
    (407, "Catupiry", "RAW_MATERIAL", "g", 500.0, 1000000.0),
    (408, "Calabresa", "RAW_MATERIAL", "g", 500.0, 1000000.0),
    (409, "Provolone", "RAW_MATERIAL", "g", 500.0, 1000000.0),
    (410, "Parmesão", "RAW_MATERIAL", "g", 500.0, 1000000.0),
    (411, "Gorgonzola", "RAW_MATERIAL", "g", 500.0, 1000000.0),
    (412, "Cebola", "RAW_MATERIAL", "un", 50.0, 1000000.0),
    (413, "Pimentão", "RAW_MATERIAL", "un", 50.0, 1000000.0),
    (414, "Ovo", "RAW_MATERIAL", "un", 30.0, 1000000.0),
    (415, "Coca-Cola Lata", "RAW_MATERIAL", "un", 24.0, 1000000.0),
    (416, "Guaraná Lata", "RAW_MATERIAL", "un", 24.0, 1000000.0),
    (417, "Suco de Laranja", "RAW_MATERIAL", "ml", 1000.0, 1000000.0),
    (418, "Heineken LN", "RAW_MATERIAL", "un", 12.0, 1000000.0),
    (419, "Brahma Chopp", "RAW_MATERIAL", "ml", 5000.0, 1000000.0),
    (420, "Água Mineral", "RAW_MATERIAL", "un", 12.0, 1000000.0),
    (421, "Massa de Pizza", "RAW_MATERIAL", "un", 20.0, 1000000.0),
    (422, "Banana", "RAW_MATERIAL", "un", 10.0, 1000000.0),
    (423, "Doce de Leite", "RAW_MATERIAL", "g", 500.0, 1000000.0),
    (424, "Chocolate Meio Amargo", "RAW_MATERIAL", "g", 500.0, 1000000.0),
    (425, "Sorvete de Creme", "RAW_MATERIAL", "ml", 1000.0, 1000000.0),
    # Embalagens (Packaging)
    (426, "Caixa de Pizza G", "PACKAGING", "un", 50.0, 1000000.0),
    (427, "Caixa de Pizza M", "PACKAGING", "un", 50.0, 1000000.0),
    (428, "Lacre de Segurança", "PACKAGING", "un", 100.0, 1000000.0),
    (429, "Guardanapo Personalizado", "PACKAGING", "un", 500.0, 1000000.0),
    # Suplementos/Outros (Supplements/Others)
    (430, "Lenha de Eucalipto", "OTHER", "kg", 100.0, 1000000.0),
    (431, "Detergente Máquina", "SUPPLEMENT", "un", 2.0, 1000000.0),
    (432, "Esponja de Aço", "SUPPLEMENT", "un", 5.0, 1000000.0),
]

T2_RECIPES: list[tuple[int, int, list[tuple[int, float, str]]]] = [
    (501, 301, [(401, 250, "g"), (402, 100, "ml"), (403, 150, "g")]),
    (502, 302, [(401, 250, "g"), (402, 100, "ml"), (403, 150, "g"), (404, 50, "g")]),
    (
        503,
        303,
        [
            (401, 250, "g"),
            (402, 100, "ml"),
            (403, 150, "g"),
            (405, 50, "g"),
            (414, 1, "un"),
            (412, 20, "g"),
            (413, 20, "g"),
        ],
    ),
    (
        504,
        304,
        [(401, 250, "g"), (402, 100, "ml"), (403, 150, "g"), (406, 100, "g"), (407, 80, "g")],
    ),
    (
        505,
        305,
        [(401, 250, "g"), (402, 100, "ml"), (403, 150, "g"), (408, 80, "g"), (412, 20, "g")],
    ),
    (
        506,
        306,
        [
            (401, 250, "g"),
            (402, 100, "ml"),
            (403, 80, "g"),
            (409, 80, "g"),
            (410, 50, "g"),
            (411, 50, "g"),
        ],
    ),
    (
        507,
        307,
        [(401, 250, "g"), (402, 100, "ml"), (403, 100, "g"), (413, 30, "g"), (412, 20, "g")],
    ),
    (508, 308, [(401, 200, "g"), (423, 80, "g"), (422, 1, "un")]),
    (509, 309, [(415, 1, "un")]),
    (510, 310, [(416, 1, "un")]),
    (511, 311, [(417, 300, "ml")]),
    (512, 312, [(418, 1, "un")]),
    (513, 313, [(419, 300, "ml")]),
    (514, 314, [(420, 1, "un")]),
    (515, 315, [(214, 1, "un")]),
    (516, 316, [(424, 150, "g"), (425, 100, "ml")]),
]

T2_COMBOS: list[tuple[tuple[tuple[int, int], ...], str, float]] = [
    # Pizza simples (mais comum)
    (((301, 1), (309, 1)), "Margherita + Coke", 0.15),
    (((302, 1), (312, 1)), "Pepperoni + Heineken", 0.12),
    (((305, 1), (313, 1)), "Calabresa + Chopp", 0.10),
    (((304, 1), (311, 1)), "Frango Catupiry + Suco", 0.08),
    # Casal
    (((304, 1), (306, 1), (312, 2)), "Frango Catupiry + 4 Queijos + 2 Heineken", 0.07),
    (((303, 1), (305, 1), (313, 2)), "Portuguesa + Calabresa + 2 Chopp", 0.06),
    # Família
    (((301, 1), (302, 1), (306, 1), (309, 2), (312, 2)), "3 Pizzas + 4 Bebidas (família)", 0.04),
    # Só bebida
    (((312, 2),), "2 Heinekens", 0.06),
    (((309, 1), (310, 1)), "Coca + Guaraná", 0.04),
    # Sobremesa
    (((315, 1),), "Pudim de Leite", 0.05),
    (((316, 1),), "Petit Gateau", 0.04),
    # Pizza doce
    (((308, 1), (314, 1)), "Pizza Doce + Água", 0.03),
    # Completo (pizza + bebida + sobremesa)
    (((301, 1), (312, 1), (315, 1)), "Margherita + Heineken + Pudim", 0.06),
    (((304, 1), (311, 1), (316, 1)), "Frango + Suco + Petit Gateau", 0.04),
    # Grupo grande
    (
        ((302, 1), (303, 1), (304, 1), (305, 1), (312, 4), (313, 2)),
        "4 Pizzas + 6 Bebidas (grupo)",
        0.02,
    ),
]


# ─── Order Generation Helpers ─────────────────────────────────────────────────


def _format_payload_item(
    item_id: int,
    menu_item_id: int,
    name: str,
    item_price: Decimal,
    station: str,
    qty: int,
    subtotal: Decimal,
) -> dict[str, Any]:
    return {
        "id": item_id,
        "menu_item_id": menu_item_id,
        "name": name,
        "category": station,
        "price": float(item_price),
        "quantity": qty,
        "subtotal": float(subtotal),
    }


def _format_history_item(
    item_id: int,
    menu_item_id: int,
    name: str,
    item_price: Decimal,
    station: str,
    qty: int,
    subtotal: Decimal,
) -> dict[str, Any]:
    return {
        "id": item_id,
        "menu_item_id": menu_item_id,
        "name": name,
        "price": str(item_price),
        "station_type": station,
        "quantity": qty,
        "notes": "",
        "subtotal": str(subtotal),
    }


def _build_menu_item_map(
    menu_items: list[tuple[int, str, str, float, str, str]],
) -> dict[int, dict[str, Any]]:
    return {
        mid: {"name": name, "price": Decimal(str(price)), "category": cat, "station_type": station}
        for mid, name, _desc, price, cat, station in menu_items
    }


def _build_stock_by_menu(
    recipes: list[tuple[int, int, list[tuple[int, float, str]]]],
) -> dict[int, list[tuple[int, float, str]]]:
    mapping: dict[int, list[tuple[int, float, str]]] = {}
    for _rid, menu_item_id, ingredients in recipes:
        mapping[menu_item_id] = ingredients
    return mapping


def _day_type(d: datetime.date) -> str:
    """Returns 'weekday' (Mon-Thu), 'friday', 'saturday', 'sunday'."""
    wd = d.weekday()
    if wd == 4:
        return "friday"
    if wd == 5:
        return "saturday"
    if wd == 6:
        return "sunday"
    return "weekday"


def _order_count_for_day(day_type: str, is_pizzeria: bool = False) -> int:
    if is_pizzeria:
        counts = {
            "weekday": (15, 25),
            "friday": (28, 40),
            "saturday": (38, 55),
            "sunday": (30, 45),
        }
    else:
        counts = {
            "weekday": (28, 42),
            "friday": (45, 60),
            "saturday": (58, 78),
            "sunday": (50, 68),
        }
    lo, hi = counts[day_type]
    return random.randint(lo, hi)


def _order_times_for_day(
    day_type: str,
    num_orders: int,
    base_date: datetime.date,
    is_pizzeria: bool = False,
    rng: Any = None,
) -> list[datetime.datetime]:
    """Generate realistic order timestamps clustered around peak hours."""
    if rng is None:
        rng = random

    base_dt = datetime.datetime.combine(base_date, datetime.time(), tzinfo=datetime.UTC)

    if is_pizzeria:
        # Pizzeria: dinner only, 18:00-23:30, peak 19:30-21:30
        open_hour, close_hour = 18, 23
        peak_start, peak_end = 19.5, 21.5  # 19:30-21:30
    else:
        # Beach restaurant: 10:00-22:00, lunch peak 12:00-14:00, dinner peak 18:30-20:00
        open_hour, close_hour = 10, 22
        peak_start, peak_end = 12.0, 14.0
        dinner_peak_start, dinner_peak_end = 18.5, 20.0

    times: list[datetime.datetime] = []
    for _ in range(num_orders):
        r = rng.random()
        if is_pizzeria:
            if r < 0.65:
                # Peak
                hour = rng.uniform(peak_start, peak_end)
            elif r < 0.85:
                # Early (18:00-19:30)
                hour = rng.uniform(open_hour, peak_start)
            else:
                # Late (21:30-23:30)
                hour = rng.uniform(peak_end, 23.5)
        elif r < 0.35:
            # Lunch peak
            hour = rng.uniform(peak_start, peak_end)
        elif r < 0.55:
            # Dinner peak
            hour = rng.uniform(dinner_peak_start, dinner_peak_end)
        elif r < 0.75:
            # Off-peak afternoon
            hour = rng.uniform(14.0, 18.5)
        elif r < 0.90:
            # Morning (10:00-12:00)
            hour = rng.uniform(open_hour, peak_start)
        else:
            # Late (20:00-22:00)
            hour = rng.uniform(dinner_peak_end, 22.0)

        h = int(hour)
        m = int((hour - h) * 60)
        if m >= 60:
            h += 1
            m = 0
        if h >= 24:
            h = 23
            m = 59
        times.append(base_dt.replace(hour=h, minute=m))
    return times


# ─── Seed function ────────────────────────────────────────────────────────────


async def _setup_tenant(
    db: Any,
    mongo_db: Any,
    tenant_id: str,
    tenant_name: str,
    employees: list[tuple[int, str, str, str]],
    menu_items_data: list[tuple[int, str, str, float, str, str]],
    no_prep_ids: set[int],
    stock_items_data: list[tuple[int, str, str, str, float, float]],
    recipes_data: list[tuple[int, int, list[tuple[int, float, str]]]],
    have_data: bool,
) -> dict[str, Any]:
    """Setup a tenant's base data (employees, menu, stock, recipes, pricelist)."""

    passwd = "password123"

    # ── Employees ──────────────────────────────────────────────────────────
    if not have_data:
        print(f"  Seeding employees for '{tenant_name}'...")
        for emp_id, name, email, role in employees:
            existing_emp = await db.scalar(
                select(EmployeeORM).where((EmployeeORM.email == email) | (EmployeeORM.id == emp_id))
            )
            if existing_emp:
                await db.execute(
                    delete(UserTenantRoleORM).where(
                        UserTenantRoleORM.employee_id == existing_emp.id
                    )
                )
                await db.execute(delete(EmployeeORM).where(EmployeeORM.id == existing_emp.id))
                await db.flush()

            emp = EmployeeORM(
                id=emp_id,
                name=name,
                email=email,
                password_hash=hash_password(passwd),
            )
            db.add(emp)
            await db.flush()

            role_orm = UserTenantRoleORM(
                tenant_id=int(tenant_id),
                employee_id=emp.id,
                role_type=role,
                is_active=True,
                removed=False,
            )
            db.add(role_orm)
        await db.flush()

        # Manager permission
        manager_id = employees[0][0]
        perm_orm = EmployeePermissionORM(
            id=manager_id,
            tenant_id=int(tenant_id),
            employee_id=manager_id,
            action="MANAGE_MENU",
            granted=True,
        )
        db.add(perm_orm)
        await db.flush()

    # ── Menu Items ─────────────────────────────────────────────────────────
    if not have_data:
        print(f"  Seeding menu items for '{tenant_name}'...")
        for mid, name, desc, price, cat_name, station in menu_items_data:
            existing = await db.scalar(select(MenuItemORM).where(MenuItemORM.id == mid))
            if not existing:
                mi = MenuItemORM(
                    id=mid,
                    tenant_id=tenant_id,
                    name=name,
                    description=desc,
                    base_price=Decimal(str(price)),
                    category_name=cat_name,
                    station_type=station,
                    is_available=True,
                    preparation_profile="NO_PREP" if mid in no_prep_ids else "STANDARD",
                )
                db.add(mi)
        await db.flush()

    # ── Stock Items + initial transactions ─────────────────────────────────
    if not have_data:
        stock_sync = StockReadModelSync(mongo_db)
        print(f"  Seeding stock items for '{tenant_name}'...")
        for sid, name, category, unit, min_stock, initial_qty in stock_items_data:
            existing = await db.scalar(select(StockItemORM).where(StockItemORM.id == sid))
            if existing:
                continue
            s_orm = StockItemORM(
                id=sid,
                tenant_id=tenant_id,
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
                cost_amount=Decimal("5.00"),
                occurred_at=datetime.datetime(2020, 1, 1, 0, 0, tzinfo=datetime.UTC),
            )
            db.add(tx_orm)
            await db.flush()

            domain_item = SimpleStockItem(
                id=sid,
                tenant_id=tenant_id,
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
                        cost_amount=Decimal("5.00"),
                        reason="Seed initial stock",
                        occurred_at=datetime.datetime(2020, 1, 1, 0, 0, tzinfo=datetime.UTC),
                    )
                ],
            )
            await stock_sync.sync(domain_item)

    # ── Recipes ────────────────────────────────────────────────────────────
    if not have_data:
        print(f"  Seeding recipes for '{tenant_name}'...")
        for rid, menu_item_id, ingredients in recipes_data:
            existing = await db.scalar(select(RecipeORM).where(RecipeORM.id == rid))
            if existing:
                continue
            r_orm = RecipeORM(id=rid, menu_item_id=menu_item_id, tenant_id=tenant_id)
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

    # ── Menu + Categories + PriceList ──────────────────────────────────────
    menu_name_map = {
        "1": "Cardápio Barraca do Sol",
        "2": "Cardápio Pizza da Vila",
    }

    if not have_data:
        print(f"  Seeding menu structure for '{tenant_name}'...")
        menu_name = menu_name_map[tenant_id]
        existing_menu = await db.scalar(select(MenuORM).where(MenuORM.tenant_id == tenant_id))
        if not existing_menu:
            menu_orm = MenuORM(
                id=int(tenant_id),
                tenant_id=tenant_id,
                name=menu_name,
                description="",
                is_active=True,
            )
            db.add(menu_orm)
            await db.flush()
        else:
            menu_orm = existing_menu

        # Delete existing categories
        await db.execute(delete(CategoryItemORM).where(CategoryItemORM.menu_id == menu_orm.id))
        await db.flush()

        categories = list(dict.fromkeys([cat for _, _, _, _, cat, _ in menu_items_data]))
        for cat in categories:
            for mi_id, _name, _desc, _price, cat_name, _station in menu_items_data:
                if cat_name == cat:
                    ci_orm = CategoryItemORM(
                        menu_id=menu_orm.id,
                        category_name=cat,
                        menu_item_id=mi_id,
                    )
                    db.add(ci_orm)
        await db.flush()

        # Price lists
        if tenant_id == "1":
            existing_pl = await db.scalar(select(PriceListORM).where(PriceListORM.id == 1))
            if not existing_pl:
                pl_orm = PriceListORM(
                    id=1,
                    tenant_id=tenant_id,
                    menu_id=menu_orm.id,
                    name="Happy Hour",
                    description="Preços especiais para bebidas no happy hour (18h-20h)",
                    is_active=True,
                )
                db.add(pl_orm)
                await db.flush()
                drink_overrides = [
                    (112, Decimal("12.00")),
                    (113, Decimal("15.00")),
                    (111, Decimal("6.00")),
                    (114, Decimal("10.00")),
                ]
                for mi_id, price in drink_overrides:
                    pli = PriceListItemORM(
                        id=mi_id,
                        price_list_id=1,
                        menu_item_id=mi_id,
                        price=price,
                    )
                    db.add(pli)
                await db.flush()
                menu_orm.active_price_list_id = 1
            else:
                menu_orm.active_price_list_id = 1

        if tenant_id == "2":
            existing_pl = await db.scalar(select(PriceListORM).where(PriceListORM.id == 3))
            if not existing_pl:
                pl_orm = PriceListORM(
                    id=3,
                    tenant_id=tenant_id,
                    menu_id=menu_orm.id,
                    name="Happy Hour",
                    description="Preços especiais para bebidas (18h-20h)",
                    is_active=True,
                )
                db.add(pl_orm)
                await db.flush()
                drink_overrides = [
                    (312, Decimal("7.00")),
                    (309, Decimal("4.00")),
                    (310, Decimal("4.00")),
                    (311, Decimal("6.00")),
                ]
                for mi_id, price in drink_overrides:
                    pli = PriceListItemORM(
                        id=mi_id + 100,
                        price_list_id=3,
                        menu_item_id=mi_id,
                        price=price,
                    )
                    db.add(pli)
                await db.flush()
                menu_orm.active_price_list_id = 3
            else:
                menu_orm.active_price_list_id = 3

        await db.flush()
        await db.commit()
        await db.begin()

        # Sync menu to MongoDB
        menu_domain = Menu(id=int(tenant_id), tenant_id=tenant_id, name=menu_name, description="")
        for cat in categories:
            for mi_id, _name, _desc, _price, cat_name, _station in menu_items_data:
                if cat_name == cat:
                    menu_domain.add_item_to_category(cat, mi_id)
        menu_doc = await _resolve_menu_doc(db, menu_domain)
        await MenuReadModelSync(mongo_db).sync(menu_doc)

        price_list_id = 1 if tenant_id == "1" else 3
        menu_domain_with_pl = Menu(
            id=int(tenant_id),
            tenant_id=tenant_id,
            name=menu_name,
            description="",
            price_list_id=price_list_id,
        )
        for cat in categories:
            for mi_id, _name, _desc, _price, cat_name, _station in menu_items_data:
                if cat_name == cat:
                    menu_domain_with_pl.add_item_to_category(cat, mi_id)
        menu_doc_with_pl = await _resolve_menu_doc(db, menu_domain_with_pl)
        await MenuReadModelSync(mongo_db).sync(menu_doc_with_pl)

    return {
        "menu_item_map": _build_menu_item_map(menu_items_data),
        "stock_by_menu": _build_stock_by_menu(recipes_data),
    }


async def _seed_active_orders(
    db: Any,
    mongo_db: Any,
    now: datetime.datetime,
) -> None:
    """Seed active orders, kitchen items, and audit logs for current state."""

    # ── Tenant 1 active orders ─────────────────────────────────────────────
    print("  Seeding active orders (Tenant 1)...")

    # Check if orders already exist
    existing = await db.scalar(select(OrderFormORM).where(OrderFormORM.id == 2))
    if existing:
        print("  Active orders already exist, skipping.")
        return

    # Mesa 2 (OPEN)
    order_m2 = OrderFormORM(
        id=2,
        tenant_id=T1,
        display_code="MESA-02",
        state="OPEN",
        table_number=2,
        fulfillment_type="TABLE",
        created_at=now,
    )
    db.add(order_m2)
    await db.flush()

    db.add(
        OrderFormItemORM(
            id=60021,
            order_id=2,
            menu_item_id=112,
            name_cpy="Caipirinha de Limão",
            price_cpy=Decimal("18.00"),
            station_type_cpy="BEVERAGE",
            quantity=2,
        )
    )
    db.add(
        OrderFormItemORM(
            id=60022,
            order_id=2,
            menu_item_id=105,
            name_cpy="Lula à Dorê",
            price_cpy=Decimal("55.00"),
            station_type_cpy="GRILL",
            quantity=1,
        )
    )
    db.add(
        OrderFormItemORM(
            id=60023,
            order_id=2,
            menu_item_id=106,
            name_cpy="Isca de Peixe Crocante",
            price_cpy=Decimal("45.00"),
            station_type_cpy="GRILL",
            quantity=1,
        )
    )
    await db.flush()

    # Mesa 3 (OPEN)
    order_m3 = OrderFormORM(
        id=3,
        tenant_id=T1,
        state="OPEN",
        display_code="MESA-03",
        table_number=3,
        fulfillment_type="TABLE",
        created_at=now,
    )
    db.add(order_m3)
    await db.flush()
    db.add(
        OrderFormItemORM(
            id=60031,
            order_id=3,
            menu_item_id=111,
            name_cpy="Água de Coco",
            price_cpy=Decimal("8.00"),
            station_type_cpy="BEVERAGE",
            quantity=3,
        )
    )
    db.add(
        OrderFormItemORM(
            id=60032,
            order_id=3,
            menu_item_id=103,
            name_cpy="Queijo Coalho na Brasa",
            price_cpy=Decimal("15.00"),
            station_type_cpy="GRILL",
            quantity=2,
        )
    )
    await db.flush()

    # Mesa 4 (PAYMENT_REQUESTED)
    order_m4 = OrderFormORM(
        id=4,
        tenant_id=T1,
        state="OPEN",
        display_code="MESA-04",
        table_number=4,
        fulfillment_type="TABLE",
        payment_requested=True,
        created_at=now,
    )
    db.add(order_m4)
    await db.flush()
    db.add(
        OrderFormItemORM(
            id=60041,
            order_id=4,
            menu_item_id=108,
            name_cpy="Moqueca de Camarão",
            price_cpy=Decimal("120.00"),
            station_type_cpy="GRILL",
            quantity=1,
        )
    )
    db.add(
        OrderFormItemORM(
            id=60042,
            order_id=4,
            menu_item_id=107,
            name_cpy="Porção de Batata Frita",
            price_cpy=Decimal("25.00"),
            station_type_cpy="GRILL",
            quantity=1,
        )
    )
    db.add(
        OrderFormItemORM(
            id=60043,
            order_id=4,
            menu_item_id=114,
            name_cpy="Cerveja Heineken Long Neck",
            price_cpy=Decimal("12.00"),
            station_type_cpy="BEVERAGE",
            quantity=4,
        )
    )
    await db.flush()

    pm4 = PaymentORM(
        order_id=4, tenant_id=T1, amount=Decimal("193.00"), method="CREDIT_CARD", status="PENDING"
    )
    db.add(pm4)

    # ── Tenant 1 kitchen items ─────────────────────────────────────────────
    kitchen_items_data = [
        (7001, 60022, "Lula à Dorê", "GRILL", "PREPARING", "STANDARD"),
        (7002, 60023, "Isca de Peixe Crocante", "GRILL", "WAITING", "STANDARD"),
        (7003, 60032, "Queijo Coalho na Brasa", "GRILL", "READY", "STANDARD"),
        (7004, 60021, "Caipirinha de Limão", "BEVERAGE", "WAITING", "STANDARD"),
        (7005, 60031, "Água de Coco", "BEVERAGE", "WAITING", "NO_PREP"),
        (7006, 60043, "Cerveja Heineken Long Neck", "BEVERAGE", "WAITING", "NO_PREP"),
        (7007, 60041, "Moqueca de Camarão", "GRILL", "WAITING", "STANDARD"),
        (7008, 60042, "Porção de Batata Frita", "GRILL", "WAITING", "STANDARD"),
    ]
    for kid, corr_id, name, station, state, prep in kitchen_items_data:
        db.add(
            KitchenOrderItemORM(
                id=kid,
                correlation_id=corr_id,
                name_cpy=name,
                station_type_cpy=station,
                tenant_id=T1,
                state=state,
                preparation_profile=prep,
            )
        )
    await db.flush()

    # ── Active orders audit logs ───────────────────────────────────────────
    active_audit_logs = [
        AuditLogORM(
            id=10,
            tenant_id=1,
            actor_id=502,
            actor_name="Marcos Garçom",
            action="ORDER_CREATED",
            entity_type="order",
            entity_id="2",
            details="Comanda ID 2 (MESA-02) criada.",
            created_at=now - datetime.timedelta(minutes=10),
        ),
        AuditLogORM(
            id=11,
            tenant_id=1,
            actor_id=502,
            actor_name="Marcos Garçom",
            action="ORDER_ITEM_ADD",
            entity_type="order",
            entity_id="2",
            details="Item 'Caipirinha de Limão' (Qtd: 2) adicionado.",
            created_at=now - datetime.timedelta(minutes=9),
        ),
        AuditLogORM(
            id=12,
            tenant_id=1,
            actor_id=502,
            actor_name="Marcos Garçom",
            action="ORDER_ITEM_ADD",
            entity_type="order",
            entity_id="2",
            details="Item 'Lula à Dorê' (Qtd: 1) adicionado.",
            created_at=now - datetime.timedelta(minutes=9),
        ),
        AuditLogORM(
            id=13,
            tenant_id=1,
            actor_id=502,
            actor_name="Marcos Garçom",
            action="ORDER_ITEM_ADD",
            entity_type="order",
            entity_id="2",
            details="Item 'Isca de Peixe Crocante' (Qtd: 1) adicionado.",
            created_at=now - datetime.timedelta(minutes=9),
        ),
        AuditLogORM(
            id=14,
            tenant_id=1,
            actor_id=502,
            actor_name="Marcos Garçom",
            action="KITCHEN_ITEM_CREATED",
            entity_type="kitchen_item",
            entity_id="7001",
            details="Item 'Lula à Dorê' enviado para GRILL.",
            created_at=now - datetime.timedelta(minutes=8),
        ),
        AuditLogORM(
            id=15,
            tenant_id=1,
            actor_id=503,
            actor_name="Sandra Cozinheira",
            action="KITCHEN_STATUS_PREPARING",
            entity_type="kitchen_item",
            entity_id="7001",
            details="Item 'Lula à Dorê' foi para 'Em Preparo'.",
            created_at=now - datetime.timedelta(minutes=5),
        ),
        AuditLogORM(
            id=16,
            tenant_id=1,
            actor_id=502,
            actor_name="Marcos Garçom",
            action="ORDER_CREATED",
            entity_type="order",
            entity_id="3",
            details="Comanda ID 3 (MESA-03) criada.",
            created_at=now - datetime.timedelta(minutes=15),
        ),
        AuditLogORM(
            id=17,
            tenant_id=1,
            actor_id=502,
            actor_name="Marcos Garçom",
            action="ORDER_ITEM_ADD",
            entity_type="order",
            entity_id="3",
            details="Item 'Água de Coco' (Qtd: 3) adicionado.",
            created_at=now - datetime.timedelta(minutes=14),
        ),
        AuditLogORM(
            id=18,
            tenant_id=1,
            actor_id=502,
            actor_name="Marcos Garçom",
            action="ORDER_ITEM_ADD",
            entity_type="order",
            entity_id="3",
            details="Item 'Queijo Coalho na Brasa' (Qtd: 2) adicionado.",
            created_at=now - datetime.timedelta(minutes=14),
        ),
        AuditLogORM(
            id=19,
            tenant_id=1,
            actor_id=502,
            actor_name="Marcos Garçom",
            action="ORDER_CREATED",
            entity_type="order",
            entity_id="4",
            details="Comanda ID 4 (MESA-04) criada.",
            created_at=now - datetime.timedelta(minutes=25),
        ),
        AuditLogORM(
            id=20,
            tenant_id=1,
            actor_id=502,
            actor_name="Marcos Garçom",
            action="ORDER_ITEM_ADD",
            entity_type="order",
            entity_id="4",
            details="Item 'Moqueca de Camarão' (Qtd: 1) adicionado.",
            created_at=now - datetime.timedelta(minutes=24),
        ),
        AuditLogORM(
            id=21,
            tenant_id=1,
            actor_id=502,
            actor_name="Marcos Garçom",
            action="ORDER_ITEM_ADD",
            entity_type="order",
            entity_id="4",
            details="Item 'Porção de Batata Frita' (Qtd: 1) adicionado.",
            created_at=now - datetime.timedelta(minutes=24),
        ),
        AuditLogORM(
            id=22,
            tenant_id=1,
            actor_id=502,
            actor_name="Marcos Garçom",
            action="ORDER_ITEM_ADD",
            entity_type="order",
            entity_id="4",
            details="Item 'Cerveja Heineken Long Neck' (Qtd: 4) adicionado.",
            created_at=now - datetime.timedelta(minutes=24),
        ),
        AuditLogORM(
            id=23,
            tenant_id=1,
            actor_id=503,
            actor_name="Sandra Cozinheira",
            action="KITCHEN_STATUS_READY",
            entity_type="kitchen_item",
            entity_id="7003",
            details="Item 'Queijo Coalho na Brasa' ficou 'Pronto'.",
            created_at=now - datetime.timedelta(minutes=2),
        ),
    ]
    for log in active_audit_logs:
        db.add(log)
    await db.flush()

    # ── Kitchen MongoDB docs ───────────────────────────────────────────────
    kitchen_docs = [
        {
            "kitchen_item_id": 7001,
            "correlation_id": 60022,
            "tenant_id": T1,
            "name_cpy": "Lula à Dorê",
            "station_type_cpy": "GRILL",
            "preparation_profile": "STANDARD",
            "state": "PREPARING",
            "started_at": now - datetime.timedelta(minutes=5),
            "created_at": now - datetime.timedelta(minutes=8),
            "menu_item_id": 105,
        },
        {
            "kitchen_item_id": 7002,
            "correlation_id": 60023,
            "tenant_id": T1,
            "name_cpy": "Isca de Peixe Crocante",
            "station_type_cpy": "GRILL",
            "preparation_profile": "STANDARD",
            "state": "WAITING",
            "started_at": None,
            "created_at": now - datetime.timedelta(minutes=8),
            "menu_item_id": 106,
        },
        {
            "kitchen_item_id": 7003,
            "correlation_id": 60032,
            "tenant_id": T1,
            "name_cpy": "Queijo Coalho na Brasa",
            "station_type_cpy": "GRILL",
            "preparation_profile": "STANDARD",
            "state": "READY",
            "started_at": now - datetime.timedelta(minutes=8),
            "completed_at": now - datetime.timedelta(minutes=2),
            "created_at": now - datetime.timedelta(minutes=13),
            "menu_item_id": 103,
        },
        {
            "kitchen_item_id": 7004,
            "correlation_id": 60021,
            "tenant_id": T1,
            "name_cpy": "Caipirinha de Limão",
            "station_type_cpy": "BEVERAGE",
            "preparation_profile": "NO_PREP",
            "state": "WAITING",
            "started_at": None,
            "created_at": now - datetime.timedelta(minutes=8),
            "menu_item_id": 112,
        },
        {
            "kitchen_item_id": 7005,
            "correlation_id": 60031,
            "tenant_id": T1,
            "name_cpy": "Água de Coco",
            "station_type_cpy": "BEVERAGE",
            "preparation_profile": "NO_PREP",
            "state": "WAITING",
            "started_at": None,
            "created_at": now - datetime.timedelta(minutes=13),
            "menu_item_id": 111,
        },
        {
            "kitchen_item_id": 7006,
            "correlation_id": 60043,
            "tenant_id": T1,
            "name_cpy": "Cerveja Heineken Long Neck",
            "station_type_cpy": "BEVERAGE",
            "preparation_profile": "NO_PREP",
            "state": "WAITING",
            "started_at": None,
            "created_at": now - datetime.timedelta(minutes=23),
            "menu_item_id": 114,
        },
        {
            "kitchen_item_id": 7007,
            "correlation_id": 60041,
            "tenant_id": T1,
            "name_cpy": "Moqueca de Camarão",
            "station_type_cpy": "GRILL",
            "preparation_profile": "STANDARD",
            "state": "WAITING",
            "started_at": None,
            "created_at": now - datetime.timedelta(minutes=23),
            "menu_item_id": 108,
        },
        {
            "kitchen_item_id": 7008,
            "correlation_id": 60042,
            "tenant_id": T1,
            "name_cpy": "Porção de Batata Frita",
            "station_type_cpy": "GRILL",
            "preparation_profile": "STANDARD",
            "state": "WAITING",
            "started_at": None,
            "created_at": now - datetime.timedelta(minutes=23),
            "menu_item_id": 107,
        },
    ]
    await mongo_db["kitchen_read"].insert_many(kitchen_docs)

    # ── Tenant 2 active orders (Pizza da Vila) ─────────────────────────────
    print("  Seeding active orders (Tenant 2)...")

    # Mesa 5 (OPEN)
    order_m5 = OrderFormORM(
        id=5,
        tenant_id=T2,
        display_code="MESA-05",
        state="OPEN",
        table_number=5,
        fulfillment_type="TABLE",
        created_at=now,
    )
    db.add(order_m5)
    await db.flush()
    db.add(
        OrderFormItemORM(
            id=60051,
            order_id=5,
            menu_item_id=301,
            name_cpy="Pizza Margherita",
            price_cpy=Decimal("42.00"),
            station_type_cpy="GRILL",
            quantity=1,
        )
    )
    db.add(
        OrderFormItemORM(
            id=60052,
            order_id=5,
            menu_item_id=309,
            name_cpy="Coca-Cola Lata",
            price_cpy=Decimal("6.00"),
            station_type_cpy="BEVERAGE",
            quantity=2,
        )
    )
    await db.flush()

    # Mesa 6 (OPEN)
    order_m6 = OrderFormORM(
        id=6,
        tenant_id=T2,
        display_code="MESA-06",
        state="OPEN",
        table_number=6,
        fulfillment_type="TABLE",
        created_at=now,
    )
    db.add(order_m6)
    await db.flush()
    db.add(
        OrderFormItemORM(
            id=60061,
            order_id=6,
            menu_item_id=304,
            name_cpy="Pizza Frango com Catupiry",
            price_cpy=Decimal("46.00"),
            station_type_cpy="GRILL",
            quantity=1,
        )
    )
    db.add(
        OrderFormItemORM(
            id=60062,
            order_id=6,
            menu_item_id=312,
            name_cpy="Heineken Long Neck",
            price_cpy=Decimal("10.00"),
            station_type_cpy="BEVERAGE",
            quantity=2,
        )
    )
    await db.flush()

    # Mesa 7 (PAYMENT_REQUESTED)
    order_m7 = OrderFormORM(
        id=7,
        tenant_id=T2,
        state="OPEN",
        display_code="MESA-07",
        table_number=7,
        fulfillment_type="TABLE",
        payment_requested=True,
        created_at=now,
    )
    db.add(order_m7)
    await db.flush()
    db.add(
        OrderFormItemORM(
            id=60071,
            order_id=7,
            menu_item_id=302,
            name_cpy="Pizza Pepperoni",
            price_cpy=Decimal("48.00"),
            station_type_cpy="GRILL",
            quantity=2,
        )
    )
    db.add(
        OrderFormItemORM(
            id=60072,
            order_id=7,
            menu_item_id=313,
            name_cpy="Brahma Chopp 300ml",
            price_cpy=Decimal("8.00"),
            station_type_cpy="BEVERAGE",
            quantity=4,
        )
    )
    db.add(
        OrderFormItemORM(
            id=60073,
            order_id=7,
            menu_item_id=315,
            name_cpy="Pudim de Leite",
            price_cpy=Decimal("14.00"),
            station_type_cpy="GRILL",
            quantity=1,
        )
    )
    await db.flush()

    pm7 = PaymentORM(
        order_id=7, tenant_id=T2, amount=Decimal("150.00"), method="PIX", status="PENDING"
    )
    db.add(pm7)

    # Tenant 2 kitchen items
    t2_kitchen_items = [
        (8001, 60051, "Pizza Margherita", "GRILL", "PREPARING", "STANDARD"),
        (8002, 60052, "Coca-Cola Lata", "BEVERAGE", "WAITING", "NO_PREP"),
        (8003, 60061, "Pizza Frango com Catupiry", "GRILL", "WAITING", "STANDARD"),
        (8004, 60062, "Heineken Long Neck", "BEVERAGE", "WAITING", "NO_PREP"),
        (8005, 60071, "Pizza Pepperoni", "GRILL", "PREPARING", "STANDARD"),
        (8006, 60072, "Brahma Chopp 300ml", "BEVERAGE", "WAITING", "NO_PREP"),
        (8007, 60073, "Pudim de Leite", "GRILL", "WAITING", "STANDARD"),
    ]
    for kid, corr_id, name, station, state, prep in t2_kitchen_items:
        db.add(
            KitchenOrderItemORM(
                id=kid,
                correlation_id=corr_id,
                name_cpy=name,
                station_type_cpy=station,
                tenant_id=T2,
                state=state,
                preparation_profile=prep,
            )
        )
    await db.flush()

    # Tenant 2 kitchen MongoDB docs
    t2_kitchen_docs = [
        {
            "kitchen_item_id": 8001,
            "correlation_id": 60051,
            "tenant_id": T2,
            "name_cpy": "Pizza Margherita",
            "station_type_cpy": "GRILL",
            "preparation_profile": "STANDARD",
            "state": "PREPARING",
            "started_at": now - datetime.timedelta(minutes=3),
            "created_at": now - datetime.timedelta(minutes=10),
            "menu_item_id": 301,
        },
        {
            "kitchen_item_id": 8002,
            "correlation_id": 60052,
            "tenant_id": T2,
            "name_cpy": "Coca-Cola Lata",
            "station_type_cpy": "BEVERAGE",
            "preparation_profile": "NO_PREP",
            "state": "WAITING",
            "started_at": None,
            "created_at": now - datetime.timedelta(minutes=10),
            "menu_item_id": 309,
        },
        {
            "kitchen_item_id": 8003,
            "correlation_id": 60061,
            "tenant_id": T2,
            "name_cpy": "Pizza Frango com Catupiry",
            "station_type_cpy": "GRILL",
            "preparation_profile": "STANDARD",
            "state": "WAITING",
            "started_at": None,
            "created_at": now - datetime.timedelta(minutes=5),
            "menu_item_id": 304,
        },
        {
            "kitchen_item_id": 8004,
            "correlation_id": 60062,
            "tenant_id": T2,
            "name_cpy": "Heineken Long Neck",
            "station_type_cpy": "BEVERAGE",
            "preparation_profile": "NO_PREP",
            "state": "WAITING",
            "started_at": None,
            "created_at": now - datetime.timedelta(minutes=5),
            "menu_item_id": 312,
        },
        {
            "kitchen_item_id": 8005,
            "correlation_id": 60071,
            "tenant_id": T2,
            "name_cpy": "Pizza Pepperoni",
            "station_type_cpy": "GRILL",
            "preparation_profile": "STANDARD",
            "state": "PREPARING",
            "started_at": now - datetime.timedelta(minutes=8),
            "created_at": now - datetime.timedelta(minutes=12),
            "menu_item_id": 302,
        },
        {
            "kitchen_item_id": 8006,
            "correlation_id": 60072,
            "tenant_id": T2,
            "name_cpy": "Brahma Chopp 300ml",
            "station_type_cpy": "BEVERAGE",
            "preparation_profile": "NO_PREP",
            "state": "WAITING",
            "started_at": None,
            "created_at": now - datetime.timedelta(minutes=12),
            "menu_item_id": 313,
        },
        {
            "kitchen_item_id": 8007,
            "correlation_id": 60073,
            "tenant_id": T2,
            "name_cpy": "Pudim de Leite",
            "station_type_cpy": "GRILL",
            "preparation_profile": "STANDARD",
            "state": "WAITING",
            "started_at": None,
            "created_at": now - datetime.timedelta(minutes=12),
            "menu_item_id": 315,
        },
    ]
    await mongo_db["kitchen_read"].insert_many(t2_kitchen_docs)


async def _generate_month(
    db: Any,
    mongo_db: Any,
    tenant_id: str,
    year: int,
    month: int,
    menu_item_map: dict[int, dict[str, Any]],
    stock_by_menu: dict[int, list[tuple[int, float, str]]],
    combos: list[tuple[tuple[tuple[int, int], ...], str, float]],
    is_pizzeria: bool,
    stock_sync: StockReadModelSync,
) -> int:
    """Generate one month of historical orders. Returns number of orders created."""

    method_weights: list[tuple[str, float]] = [
        ("PIX", 0.40),
        ("CREDIT_CARD", 0.35),
        ("DEBIT_CARD", 0.15),
        ("CASH", 0.10),
    ]
    waiter_id = 502 if tenant_id == T1 else 602
    waiter_name = "Marcos Garçom" if tenant_id == T1 else "Ana Garçonete"
    cook_id = 503 if tenant_id == T1 else 603
    cook_name = "Sandra Cozinheira" if tenant_id == T1 else "Pedro Pizzaiolo"

    days_in_month = calendar.monthrange(year, month)[1]

    chunk_size = 1000

    async def _bulk_insert(orm_class: Any, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        for i in range(0, len(rows), chunk_size):
            await db.execute(pg_insert(orm_class).values(rows[i : i + chunk_size]))

    all_orders_pg: list[dict[str, Any]] = []
    all_items_pg: list[dict[str, Any]] = []
    all_payments_pg: list[dict[str, Any]] = []
    all_kitchen_pg: list[dict[str, Any]] = []
    all_audit_pg: list[dict[str, Any]] = []
    all_tx_pg: list[dict[str, Any]] = []
    all_orders_read_mongo: list[dict[str, Any]] = []
    all_history_mongo: list[dict[str, Any]] = []
    all_kitchen_mongo: list[dict[str, Any]] = []

    total_orders = 0

    today = datetime.date.today()

    for day in range(1, days_in_month + 1):
        d = datetime.date(year, month, day)
        if d > today:
            break
        dt = _day_type(d)
        num_orders = _order_count_for_day(dt, is_pizzeria=is_pizzeria)
        times = _order_times_for_day(dt, num_orders, d, is_pizzeria=is_pizzeria)

        for t in times:
            order_id = next_id("order")
            table_num = random.randint(1, 15)

            # Select combo
            selected = random.choices(combos, weights=[w for _, _, w in combos])[0]
            combo_items = selected[0]
            combo_label = selected[1]

            total_amount = Decimal("0.00")
            order_items_pg: list[dict[str, Any]] = []
            items_for_mongo: list[dict[str, Any]] = []
            history_items_for_mongo: list[dict[str, Any]] = []
            kitchen_pg_list: list[dict[str, Any]] = []
            kitchen_mongo_list: list[dict[str, Any]] = []
            tx_list: list[dict[str, Any]] = []
            subtotals_for_audit: list[str] = []

            item_counter = 0
            for mi_id, qty in combo_items:
                item_counter += 1
                item_id = order_id * 100 + item_counter
                mi = menu_item_map[mi_id]
                name = mi["name"]
                price = mi["price"]
                station = mi["station_type"]
                subtotal = price * qty
                total_amount += subtotal

                order_items_pg.append(
                    {
                        "id": item_id,
                        "order_id": order_id,
                        "menu_item_id": mi_id,
                        "name_cpy": name,
                        "price_cpy": price,
                        "station_type_cpy": station,
                        "quantity": qty,
                        "delivered_quantity": qty,
                        "canceled_quantity": 0,
                        "notes": "",
                        "status": "READY" if random.random() > 0.05 else "CANCELED",
                    }
                )

                items_for_mongo.append(
                    _format_payload_item(
                        item_id,
                        mi_id,
                        name,
                        price,
                        station,
                        qty,
                        subtotal,
                    )
                )
                history_items_for_mongo.append(
                    _format_history_item(
                        item_id,
                        mi_id,
                        name,
                        price,
                        station,
                        qty,
                        subtotal,
                    )
                )
                subtotals_for_audit.append(f"'{name}' (Qtd: {qty}, R$ {fmt_price(price)})")

                # Kitchen item
                is_no_prep = station == "BEVERAGE" and price < Decimal("15")
                kitchen_id = next_id("kitchen")
                # Simulate realistic prep: started 2-15 min after order, ready 10-40 min later
                started_delta = random.randint(2, 15)
                prep_duration = random.randint(10, 40) if not is_no_prep else random.randint(0, 5)
                started_at = t + datetime.timedelta(minutes=started_delta)
                completed_at = started_at + datetime.timedelta(minutes=prep_duration)
                kitchen_state = "READY"

                kitchen_pg_list.append(
                    {
                        "id": kitchen_id,
                        "correlation_id": item_id,
                        "name_cpy": name,
                        "station_type_cpy": station,
                        "tenant_id": tenant_id,
                        "state": kitchen_state,
                        "preparation_profile": "NO_PREP" if is_no_prep else "STANDARD",
                        "notes": "",
                        "previous_state": "PREPARING",
                    }
                )
                kitchen_mongo_list.append(
                    {
                        "kitchen_item_id": kitchen_id,
                        "correlation_id": item_id,
                        "tenant_id": tenant_id,
                        "name_cpy": name,
                        "station_type_cpy": station,
                        "preparation_profile": "NO_PREP" if is_no_prep else "STANDARD",
                        "state": kitchen_state,
                        "started_at": started_at,
                        "completed_at": completed_at,
                        "created_at": t,
                        "menu_item_id": mi_id,
                    }
                )

                # Stock consumption
                if mi_id in stock_by_menu:
                    for stock_id, qty_needed, unit in stock_by_menu[mi_id]:
                        qty_consumed = Decimal(str(qty_needed)) * qty
                        tx_id = next_id("tx")
                        tx_list.append(
                            {
                                "id": tx_id,
                                "stock_item_id": stock_id,
                                "transaction_type": "OUTPUT",
                                "quantity_value": qty_consumed,
                                "quantity_unit": unit,
                                "reason": f"Consumo: {combo_label}",
                                "cost_amount": Decimal("0.00"),
                                "occurred_at": t,
                            }
                        )

            # Payment
            pay_id = next_id("payment")
            method = random_choice_weighted(method_weights)
            pay_gateway = f"gtw_{secrets.token_hex(8)}"

            all_orders_pg.append(
                {
                    "id": order_id,
                    "tenant_id": tenant_id,
                    "display_code": f"MESA-{table_num:02d}",
                    "state": "CLOSED",
                    "table_number": table_num,
                    "fulfillment_type": "TABLE",
                    "created_at": t,
                }
            )
            all_items_pg.extend(order_items_pg)
            all_payments_pg.append(
                {
                    "id": pay_id,
                    "order_id": order_id,
                    "tenant_id": tenant_id,
                    "amount": total_amount,
                    "method": method,
                    "status": "CONFIRMED",
                    "gateway_ref": pay_gateway,
                }
            )
            all_kitchen_pg.extend(kitchen_pg_list)
            all_tx_pg.extend(tx_list)

            # Audit logs
            audit_id = next_id("audit")
            all_audit_pg.append(
                {
                    "id": audit_id,
                    "tenant_id": int(tenant_id),
                    "actor_id": waiter_id,
                    "actor_name": waiter_name,
                    "action": "ORDER_CREATED",
                    "entity_type": "order",
                    "entity_id": str(order_id),
                    "details": f"Comanda ID {order_id} criada na MESA-{table_num:02d}.",
                    "created_at": t,
                }
            )
            audit_id2 = next_id("audit")
            all_audit_pg.append(
                {
                    "id": audit_id2,
                    "tenant_id": int(tenant_id),
                    "actor_id": waiter_id,
                    "actor_name": waiter_name,
                    "action": "ORDER_ITEM_ADD",
                    "entity_type": "order",
                    "entity_id": str(order_id),
                    "details": f"Itens adicionados: {', '.join(subtotals_for_audit)}.",
                    "created_at": t + datetime.timedelta(minutes=1),
                }
            )
            # Kitchen audit for first item only (skip detail for brevity)
            if kitchen_pg_list:
                audit_id3 = next_id("audit")
                all_audit_pg.append(
                    {
                        "id": audit_id3,
                        "tenant_id": int(tenant_id),
                        "actor_id": waiter_id,
                        "actor_name": waiter_name,
                        "action": "KITCHEN_ITEM_CREATED",
                        "entity_type": "kitchen_item",
                        "entity_id": str(kitchen_pg_list[0]["id"]),
                        "details": "Item enviado para a cozinha.",
                        "created_at": t + datetime.timedelta(minutes=2),
                    }
                )
            # Ready audit
            if kitchen_mongo_list and kitchen_mongo_list[0]["completed_at"]:
                audit_id4 = next_id("audit")
                all_audit_pg.append(
                    {
                        "id": audit_id4,
                        "tenant_id": int(tenant_id),
                        "actor_id": cook_id,
                        "actor_name": cook_name,
                        "action": "KITCHEN_STATUS_READY",
                        "entity_type": "kitchen_item",
                        "entity_id": str(kitchen_pg_list[0]["id"]),
                        "details": "Item ficou 'Pronto'.",
                        "created_at": kitchen_mongo_list[0]["completed_at"],
                    }
                )

            # MongoDB docs
            all_orders_read_mongo.append(
                {
                    "order_id": order_id,
                    "tenant_id": tenant_id,
                    "total": float(total_amount),
                    "items": items_for_mongo,
                    "created_at": t,
                }
            )
            all_history_mongo.append(
                {
                    "order_id": order_id,
                    "tenant_id": tenant_id,
                    "total": str(total_amount),
                    "state": "CLOSED",
                    "fulfillment": {
                        "type": "TABLE",
                        "fee": "0.00",
                        "table": {"table_number": table_num},
                    },
                    "items": history_items_for_mongo,
                    "closed_at": t.isoformat(),
                }
            )
            all_kitchen_mongo.extend(kitchen_mongo_list)

            total_orders += 1

    # Bulk insert PostgreSQL (chunked to avoid parameter limit)
    await _bulk_insert(OrderFormORM, all_orders_pg)
    await _bulk_insert(OrderFormItemORM, all_items_pg)
    await _bulk_insert(PaymentORM, all_payments_pg)
    await _bulk_insert(KitchenOrderItemORM, all_kitchen_pg)
    await _bulk_insert(AuditLogORM, all_audit_pg)
    await _bulk_insert(StockTransactionORM, all_tx_pg)

    # Bulk insert MongoDB
    if all_orders_read_mongo:
        await mongo_db["orders_read"].insert_many(all_orders_read_mongo)
    if all_history_mongo:
        await mongo_db["order_history"].insert_many(all_history_mongo)
    if all_kitchen_mongo:
        await mongo_db["kitchen_read"].insert_many(all_kitchen_mongo)

    # Sync stock read model — calculate net consumption per item
    stock_consumption: dict[int, dict[str, Any]] = {}
    for tx in all_tx_pg:
        sid = tx["stock_item_id"]
        if sid not in stock_consumption:
            si_orm = await db.scalar(select(StockItemORM).where(StockItemORM.id == sid))
            if si_orm:
                stock_consumption[sid] = {
                    "orm": si_orm,
                    "net_qty": Decimal("0"),
                    "unit": si_orm.unit,
                }
        if sid in stock_consumption:
            sc = stock_consumption[sid]
            if tx["transaction_type"] == "OUTPUT":
                sc["net_qty"] -= tx["quantity_value"]
            else:
                sc["net_qty"] += tx["quantity_value"]

    # Replenish stock every month (add INPUT tx for each stock item)
    replenish_txs: list[dict[str, Any]] = []
    for sid, sc in stock_consumption.items():
        tx_id = next_id("tx")
        unit = sc["unit"]
        repl_qty = Decimal("1000000")
        replenish_txs.append(
            {
                "id": tx_id,
                "stock_item_id": sid,
                "transaction_type": "INPUT",
                "quantity_value": repl_qty,
                "quantity_unit": unit,
                "reason": "Reabastecimento mensal",
                "cost_amount": Decimal("25.00"),
                "occurred_at": datetime.datetime(year, month, 1, 8, 0, tzinfo=datetime.UTC),
            }
        )
    if replenish_txs:
        all_tx_pg.extend(replenish_txs)
        await _bulk_insert(StockTransactionORM, replenish_txs)

    # Sync stock read model — calculate net consumption per item
    for sid, sc in stock_consumption.items():
        si_orm = sc["orm"]
        # Calculate total balance from all transactions in DB for this item
        total_qty_stmt = select(StockTransactionORM.transaction_type, StockTransactionORM.quantity_value).where(
            StockTransactionORM.stock_item_id == sid
        )
        txs_res = await db.execute(total_qty_stmt)
        total_balance = Decimal("0")
        for tx_type, tx_val in txs_res.all():
            if tx_type in ("INPUT", "PRODUCTION", "ADJUSTMENT"):
                total_balance += tx_val
            elif tx_type in ("OUTPUT", "WASTE"):
                total_balance -= tx_val
        
        current_qty = max(Decimal("0"), total_balance)
        domain_item_simple = SimpleStockItem(
            id=si_orm.id,
            tenant_id=si_orm.tenant_id,
            name=si_orm.name,
            category=si_orm.category,
            unit=si_orm.unit,
            min_stock_level=si_orm.min_stock_level,
            is_active=si_orm.is_active,
            transactions=[
                StockTransaction(
                    id=0,
                    quantity=MeasuredQuantity(current_qty, sc["unit"]),
                    type=TransactionType.INPUT,
                    cost_amount=Decimal("1.00"),
                    reason="Snapshot for sync",
                )
            ],
        )
        await stock_sync.sync(domain_item_simple)

    return total_orders


async def seed() -> None:
    settings = get_settings()
    await init_postgres(settings)
    await init_mongo(settings)

    mongo_db = get_mongo_db()
    now = datetime.datetime.now(datetime.UTC)

    async for db in get_async_session():
        print("=" * 60)
        print("ComandaFácil Seed")
        print("=" * 60)

        # ─── Tenants ───────────────────────────────────────────────────────
        print("\n[1/8] Setting up tenants...")
        for tid, tname, plan, active in [
            (1, "Barraca do Sol", "BASIC", True),
            (2, "Pizza da Vila", "PREMIUM", True),
        ]:
            tenant_orm = await db.scalar(select(TenantORM).where(TenantORM.id == tid))
            if not tenant_orm:
                tenant_orm = TenantORM(id=tid, name=tname, plan_type=plan, is_active=active)
                db.add(tenant_orm)
            else:
                tenant_orm.name = tname
        await db.flush()

        # ─── Clean existing data ───────────────────────────────────────────
        print("\n[2/8] Cleaning existing data...")
        for tid_str in (T1, T2):
            tid_int = int(tid_str)
            
            # Use subqueries for efficient deletion without argument limits
            await db.execute(
                delete(KitchenOrderItemORM).where(KitchenOrderItemORM.tenant_id == tid_str)
            )
            
            # Delete order items first (FK constraint)
            await db.execute(
                delete(OrderFormItemORM).where(
                    OrderFormItemORM.order_id.in_(
                        select(OrderFormORM.id).where(OrderFormORM.tenant_id == tid_str)
                    )
                )
            )
            
            await db.execute(delete(OrderFormORM).where(OrderFormORM.tenant_id == tid_str))
            await db.execute(delete(PaymentORM).where(PaymentORM.tenant_id == tid_str))
            await db.execute(
                delete(EmployeePermissionORM).where(EmployeePermissionORM.tenant_id == tid_int)
            )
            await db.execute(delete(AuditLogORM).where(AuditLogORM.tenant_id == tid_int))
            await db.execute(delete(SessionORM).where(SessionORM.tenant_id == tid_int))
            await db.execute(
                delete(UserTenantRoleORM).where(UserTenantRoleORM.tenant_id == tid_int)
            )

            await db.execute(delete(CategoryItemORM).where(
                CategoryItemORM.menu_id.in_(
                    select(MenuORM.id).where(MenuORM.tenant_id == tid_str)
                )
            ))
            await db.execute(delete(MenuORM).where(MenuORM.tenant_id == tid_str))
            
            await db.execute(delete(RecipeIngredientORM).where(
                RecipeIngredientORM.recipe_id.in_(
                    select(RecipeORM.id).where(RecipeORM.tenant_id == tid_str)
                )
            ))
            
            await db.execute(delete(RecipeORM).where(RecipeORM.tenant_id == tid_str))
            
            await db.execute(
                delete(StockTransactionORM).where(
                    StockTransactionORM.stock_item_id.in_(
                        select(StockItemORM.id).where(StockItemORM.tenant_id == tid_str)
                    )
                )
            )
            await db.execute(delete(StockItemORM).where(StockItemORM.tenant_id == tid_str))
            await db.execute(delete(MenuItemORM).where(MenuItemORM.tenant_id == tid_str))
            
            await db.execute(delete(PriceListItemORM).where(
                PriceListItemORM.price_list_id.in_(
                    select(PriceListORM.id).where(PriceListORM.tenant_id == tid_str)
                )
            ))
            await db.execute(delete(PriceListORM).where(PriceListORM.tenant_id == tid_str))
            
            # Clean employees only if they belong to these specific seed tenants
            # (Note: employees table is shared, filtered by roles cleaned above)
            emp_ids = [e[0] for e in T1_EMPLOYEES + T2_EMPLOYEES]
            await db.execute(delete(EmployeeORM).where(EmployeeORM.id.in_(emp_ids)))

            await mongo_db["stock_read"].delete_many({"tenant_id": tid_str})
            await mongo_db["menu_read_models"].delete_many({"tenant_id": tid_str})
            await mongo_db["orders_read"].delete_many({"tenant_id": tid_str})
            await mongo_db["order_history"].delete_many({"tenant_id": tid_str})
            await mongo_db["kitchen_read"].delete_many({"tenant_id": tid_str})

        await db.flush()

        # ─── Setup Tenant 1 ────────────────────────────────────────────────
        print("\n[3/8] Seeding Tenant 1: Barraca do Sol...")
        t1_items = await _setup_tenant(
            db,
            mongo_db,
            T1,
            "Barraca do Sol",
            T1_EMPLOYEES,
            T1_MENU_ITEMS,
            T1_NO_PREP_IDS,
            T1_STOCK_ITEMS,
            T1_RECIPES,
            False,
        )

        # ─── Setup Tenant 2 ────────────────────────────────────────────────
        print("\n[4/8] Seeding Tenant 2: Pizza da Vila...")
        t2_items = await _setup_tenant(
            db,
            mongo_db,
            T2,
            "Pizza da Vila",
            T2_EMPLOYEES,
            T2_MENU_ITEMS,
            T2_NO_PREP_IDS,
            T2_STOCK_ITEMS,
            T2_RECIPES,
            False,
        )

        # ─── Active orders ─────────────────────────────────────────────────
        print("\n[5/8] Seeding active orders...")
        await _seed_active_orders(db, mongo_db, now)

        # Commit base data before history generation
        await db.commit()
        await db.begin()

        # ─── Historical orders ─────────────────────────────────────────────
        print("\n[6/8] Generating 1 year of historical orders...")

        # 2 years of history
        start_year, start_month = 2024, 6
        end_year, end_month = 2026, 6

        stock_sync = StockReadModelSync(mongo_db)

        total = 0
        cy, cm = start_year, start_month
        while (cy, cm) <= (end_year, end_month):
            t1_start = datetime.datetime.now(datetime.UTC)

            t1_count = await _generate_month(
                db,
                mongo_db,
                T1,
                cy,
                cm,
                t1_items["menu_item_map"],
                t1_items["stock_by_menu"],
                T1_COMBOS,
                False,
                stock_sync,
            )

            t2_count = await _generate_month(
                db,
                mongo_db,
                T2,
                cy,
                cm,
                t2_items["menu_item_map"],
                t2_items["stock_by_menu"],
                T2_COMBOS,
                True,
                stock_sync,
            )

            await db.commit()

            t1_elapsed = (datetime.datetime.now(datetime.UTC) - t1_start).total_seconds()
            total += t1_count + t2_count
            month_name = datetime.date(cy, cm, 1).strftime("%b/%Y")
            print(
                f"    {month_name}: {t1_count} (T1) + {t2_count} (T2) = {t1_count + t2_count} ordens ({t1_elapsed:.1f}s)"
            )

            # Next month
            cm += 1
            if cm > 12:
                cm = 1
                cy += 1

            db.begin()

        print(f"\n  Total histórico: {total} ordens geradas.")

        # ─── Base audit logs ───────────────────────────────────────────────
        print("\n[7/8] Seeding base audit logs...")
        base_audit_logs = [
            AuditLogORM(
                id=1,
                tenant_id=1,
                actor_id=501,
                actor_name="Lucas Gerente",
                action="EMPLOYEE_CREATED",
                entity_type="employee",
                entity_id="502",
                details="Marcos Garçom cadastrado.",
                created_at=now - datetime.timedelta(days=30),
            ),
            AuditLogORM(
                id=2,
                tenant_id=1,
                actor_id=501,
                actor_name="Lucas Gerente",
                action="ROLE_ASSIGNED",
                entity_type="employee",
                entity_id="503",
                details="Cargo COOK atribuído a Sandra Cozinheira.",
                created_at=now - datetime.timedelta(days=30),
            ),
            AuditLogORM(
                id=3,
                tenant_id=1,
                actor_id=501,
                actor_name="Lucas Gerente",
                action="ROLE_ASSIGNED",
                entity_type="employee",
                entity_id="504",
                details="Cargo CASHIER atribuído a Roberta Caixa.",
                created_at=now - datetime.timedelta(days=30),
            ),
            AuditLogORM(
                id=4,
                tenant_id=2,
                actor_id=601,
                actor_name="Carlos Dono",
                action="EMPLOYEE_CREATED",
                entity_type="employee",
                entity_id="602",
                details="Ana Garçonete cadastrada.",
                created_at=now - datetime.timedelta(days=20),
            ),
            AuditLogORM(
                id=5,
                tenant_id=2,
                actor_id=601,
                actor_name="Carlos Dono",
                action="ROLE_ASSIGNED",
                entity_type="employee",
                entity_id="603",
                details="Cargo COOK atribuído a Pedro Pizzaiolo.",
                created_at=now - datetime.timedelta(days=20),
            ),
            AuditLogORM(
                id=6,
                tenant_id=2,
                actor_id=601,
                actor_name="Carlos Dono",
                action="ROLE_ASSIGNED",
                entity_type="employee",
                entity_id="604",
                details="Cargo CASHIER atribuído a Julia Caixa.",
                created_at=now - datetime.timedelta(days=20),
            ),
        ]
        for log in base_audit_logs:
            db.add(log)

        # ─── Final commit ──────────────────────────────────────────────────
        print("\n[8/8] Final commit...")
        await db.commit()

        # ─── Sync Sequences ────────────────────────────────────────────────
        print("\nSyncing PostgreSQL sequences...")
        tables_to_sync = [
            ("order_forms", "order_forms_id_seq"),
            ("order_form_items", "order_form_items_id_seq"),
            ("kitchen_order_items", "kitchen_order_items_id_seq"),
            ("payments", "payments_id_seq"),
            ("stock_items", "stock_items_id_seq"),
            ("stock_transactions", "stock_transactions_id_seq"),
            ("recipes", "recipes_id_seq"),
            ("recipe_ingredients", "recipe_ingredients_id_seq"),
            ("menus", "menus_id_seq"),
            ("menu_items", "menu_items_id_seq"),
            ("employees", "employees_id_seq"),
        ]
        
        from sqlalchemy import text
        for table, seq in tables_to_sync:
            max_id_res = await db.execute(text(f"SELECT MAX(id) FROM {table}"))
            max_id = max_id_res.scalar()
            if max_id:
                await db.execute(text(f"SELECT setval('{seq}', {max_id})"))
                print(f"  Sequence '{seq}' synced to {max_id}")
        
        await db.commit()
        print("\n✓ Seed concluído com sucesso!")

    await close_postgres()
    await close_mongo()


if __name__ == "__main__":
    asyncio.run(seed())
