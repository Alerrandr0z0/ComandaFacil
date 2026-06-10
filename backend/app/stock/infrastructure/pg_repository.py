from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from app.stock.domain.enums import TransactionType
from app.stock.domain.measured_quantity import MeasuredQuantity
from app.stock.domain.recipe import Recipe, RecipeIngredient
from app.stock.domain.stock_item import CompositeStockItem, SimpleStockItem, StockItem
from app.stock.domain.transaction import StockTransaction
from app.stock.infrastructure.orm_models import (
    CompositeStockItemRelationORM,
    RecipeIngredientORM,
    RecipeORM,
    StockItemORM,
    StockTransactionORM,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyStockItemRepository:
    """SQLAlchemy implementation of StockItemRepository supporting Composite pattern and Transaction Ledgers."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, id: int, tenant_id: str) -> StockItem | None:
        stmt = select(StockItemORM).where(
            StockItemORM.id == id, StockItemORM.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return await self._map_to_domain(orm)

    async def find_by_name(self, name: str, tenant_id: str) -> StockItem | None:
        stmt = select(StockItemORM).where(
            StockItemORM.name == name, StockItemORM.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return await self._map_to_domain(orm)

    async def find_all(self, tenant_id: str) -> list[StockItem]:
        stmt = (
            select(StockItemORM)
            .where(StockItemORM.tenant_id == tenant_id)
            .order_by(StockItemORM.name)
        )
        result = await self._session.execute(stmt)
        orms: Sequence[StockItemORM] = result.scalars().all()
        items = []
        for orm in orms:
            mapped = await self._map_to_domain(orm)
            items.append(mapped)
        return items

    async def find_low_stock(self, tenant_id: str) -> list[StockItem]:
        all_items = await self.find_all(tenant_id)
        return [item for item in all_items if item.is_low_stock]

    async def save(self, item: StockItem) -> None:
        stmt = select(StockItemORM).where(StockItemORM.id == item.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        unit = getattr(item, "unit", "un")
        item_type = "COMPOSITE" if isinstance(item, CompositeStockItem) else "SIMPLE"

        if orm:
            orm.name = item.name
            orm.category = item.category
            orm.min_stock_level = item.min_stock_level
            orm.is_active = item.is_active
            orm.type = item_type
            orm.unit = unit
        else:
            orm = StockItemORM(
                tenant_id=item.tenant_id,
                name=item.name,
                category=item.category,
                type=item_type,
                unit=unit,
                min_stock_level=item.min_stock_level,
                is_active=item.is_active,
            )
            self._session.add(orm)

        await self._session.flush()
        if item.id == 0:
            item.id = orm.id

        # Save relationships for composite items
        if isinstance(item, CompositeStockItem):
            # Clear old relations
            await self._session.execute(
                delete(CompositeStockItemRelationORM).where(
                    CompositeStockItemRelationORM.parent_id == item.id
                )
            )
            for child in item.components:
                # Ensure child is saved first
                await self.save(child)
                relation = CompositeStockItemRelationORM(
                    parent_id=item.id,
                    child_id=child.id,
                )
                self._session.add(relation)

        # Save new transactions (where transaction id is 0 or new)
        existing_txs_stmt = select(StockTransactionORM.id).where(
            StockTransactionORM.stock_item_id == item.id
        )
        existing_txs_res = await self._session.execute(existing_txs_stmt)
        existing_tx_ids = set(existing_txs_res.scalars().all())

        for tx in item.transactions:
            if tx.id == 0 or tx.id not in existing_tx_ids:
                tx_orm = StockTransactionORM(
                    stock_item_id=item.id,
                    transaction_type=tx.type.value,
                    quantity_value=tx.quantity.value,
                    quantity_unit=tx.quantity.unit,
                    reason=tx.reason,
                    occurred_at=tx.occurred_at,
                )
                self._session.add(tx_orm)

        await self._session.flush()

    async def delete(self, id: int, tenant_id: str) -> None:
        stmt = select(StockItemORM).where(
            StockItemORM.id == id, StockItemORM.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            await self._session.delete(orm)
            await self._session.flush()

    async def _map_to_domain(self, orm: StockItemORM) -> StockItem:
        # Load transactions
        tx_stmt = (
            select(StockTransactionORM)
            .where(StockTransactionORM.stock_item_id == orm.id)
            .order_by(StockTransactionORM.occurred_at)
        )
        tx_result = await self._session.execute(tx_stmt)
        tx_orms = tx_result.scalars().all()
        transactions = [
            StockTransaction(
                id=t.id,
                quantity=MeasuredQuantity(t.quantity_value, t.quantity_unit),
                type=TransactionType(t.transaction_type),
                reason=t.reason,
                occurred_at=t.occurred_at,
            )
            for t in tx_orms
        ]

        if orm.type == "COMPOSITE":
            # Load composite children relationships
            comp_stmt = select(CompositeStockItemRelationORM.child_id).where(
                CompositeStockItemRelationORM.parent_id == orm.id
            )
            comp_result = await self._session.execute(comp_stmt)
            child_ids = comp_result.scalars().all()

            components: list[StockItem] = []
            for cid in child_ids:
                child_item = await self.find_by_id(cid, orm.tenant_id)
                if child_item:
                    components.append(child_item)

            return CompositeStockItem(
                id=orm.id,
                tenant_id=orm.tenant_id,
                name=orm.name,
                category=orm.category,
                unit=orm.unit,
                min_stock_level=orm.min_stock_level,
                is_active=orm.is_active,
                components=components,
                transactions=transactions,
            )

        return SimpleStockItem(
            id=orm.id,
            tenant_id=orm.tenant_id,
            name=orm.name,
            category=orm.category,
            unit=orm.unit,
            min_stock_level=orm.min_stock_level,
            is_active=orm.is_active,
            transactions=transactions,
        )


class SQLAlchemyRecipeRepository:
    """SQLAlchemy implementation of RecipeRepository."""

    def __init__(self, session: AsyncSession, item_repo: SQLAlchemyStockItemRepository) -> None:
        self._session = session
        self._item_repo = item_repo

    async def find_by_menu_item(self, menu_item_id: int, tenant_id: str) -> Recipe | None:
        stmt = select(RecipeORM).where(
            RecipeORM.menu_item_id == menu_item_id, RecipeORM.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None

        # Load ingredients
        ing_stmt = select(RecipeIngredientORM).where(RecipeIngredientORM.recipe_id == orm.id)
        ing_result = await self._session.execute(ing_stmt)
        ing_orms = ing_result.scalars().all()

        ingredients: list[RecipeIngredient] = []
        for ing_orm in ing_orms:
            stock_item = await self._item_repo.find_by_id(ing_orm.stock_item_id, tenant_id)
            if stock_item:
                qty = MeasuredQuantity(ing_orm.quantity_value, ing_orm.quantity_unit)
                ingredients.append(RecipeIngredient(stock_item, qty))

        return Recipe(
            id=orm.id,
            menu_item_id=orm.menu_item_id,
            tenant_id=orm.tenant_id,
            ingredients=ingredients,
        )

    async def save(self, recipe: Recipe) -> None:
        stmt = select(RecipeORM).where(RecipeORM.id == recipe.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm:
            orm.menu_item_id = recipe.menu_item_id
        else:
            orm = RecipeORM(
                id=recipe.id,
                menu_item_id=recipe.menu_item_id,
                tenant_id=recipe.tenant_id,
            )
            self._session.add(orm)

        await self._session.flush()

        # Update ingredients
        await self._session.execute(
            delete(RecipeIngredientORM).where(RecipeIngredientORM.recipe_id == orm.id)
        )
        for ing in recipe.get_ingredients():
            # Ensure stock item is saved
            await self._item_repo.save(ing.stock_item)
            ing_orm = RecipeIngredientORM(
                recipe_id=orm.id,
                stock_item_id=ing.stock_item.id,
                quantity_value=ing.quantity.value,
                quantity_unit=ing.quantity.unit,
            )
            self._session.add(ing_orm)

        await self._session.flush()
