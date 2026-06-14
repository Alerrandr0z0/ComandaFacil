from __future__ import annotations

import hashlib
import logging

from app.auth.infrastructure.orm_models import AuditLogORM
from app.kitchen.domain.kitchen_events import KitchenItemCreated, KitchenItemStatusChanged
from app.menu.domain.menu_events import (
    MenuItemCreated,
    MenuItemDeleted,
    MenuItemUpdated,
)
from app.menu.domain.price_list_events import (
    PriceListCreated,
    PriceListDeleted,
    PriceListItemAdded,
    PriceListItemRemoved,
    PriceListItemUpdated,
    PriceListUpdated,
)
from app.order.domain.order_events import OrderCreated, OrderItemAdded
from app.shared import database
from app.shared.actor_context import current_actor_var
from app.shared.domain_events import EventBus

# Import event types
from app.stock.domain.stock_events import (
    RecipeSaved,
    StockAdjusted,
    StockItemCreated,
    StockTransactionRegistered,
)

logger = logging.getLogger("app.auth.audit_listener")


async def _save_audit_log(
    tenant_id: str | int,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: str | None = None,
) -> None:
    if database.session_factory is None:
        logger.error("session_factory is not initialized. Cannot persist audit log.")
        return

    # Convert tenant_id to int, with a stable hash fallback for test/dev string IDs
    try:
        t_id = int(str(tenant_id))
    except ValueError:
        t_id = int(hashlib.sha256(str(tenant_id).encode("utf-8")).hexdigest(), 16) % 1000000

    actor = current_actor_var.get(None)
    actor_id = actor.id if actor else None
    actor_name = actor.name if actor else "System"

    async with database.session_factory() as session:
        try:
            log_orm = AuditLogORM(
                tenant_id=t_id,
                actor_id=actor_id,
                actor_name=actor_name,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
            )
            session.add(log_orm)
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to persist audit log for action {action}: {e}", exc_info=True)


async def handle_stock_item_created(event: StockItemCreated) -> None:
    await _save_audit_log(
        tenant_id=event.tenant_id,
        action="STOCK_ITEM_CREATED",
        entity_type="stock_item",
        entity_id=str(event.item_id),
        details=f"Item de estoque '{event.name}' criado com categoria {event.category} e nível mínimo {event.min_stock_level}.",
    )


async def handle_stock_adjusted(event: StockAdjusted) -> None:
    await _save_audit_log(
        tenant_id=event.tenant_id,
        action="STOCK_ADJUST",
        entity_type="stock_item",
        entity_id=str(event.item_id),
        details=f"Quantidade do item '{event.name}' ajustada de {event.old_quantity} {event.unit} para {event.new_quantity} {event.unit}. Motivo: {event.reason or 'não especificado'}.",
    )


async def handle_stock_transaction_registered(event: StockTransactionRegistered) -> None:
    action_labels = {
        "INPUT": "Entrada",
        "OUTPUT": "Saída",
        "WASTE": "Perda",
        "PRODUCTION": "Produção",
    }
    label = action_labels.get(event.transaction_type, event.transaction_type)
    details = f"{label} de {event.quantity} {event.unit} registrada para '{event.name}'."
    if event.cost_amount > 0:
        details += f" Custo: R$ {event.cost_amount:.2f}."
    if event.reason:
        details += f" Motivo: {event.reason}."
    await _save_audit_log(
        tenant_id=event.tenant_id,
        action=f"STOCK_{event.transaction_type}",
        entity_type="stock_item",
        entity_id=str(event.item_id),
        details=details,
    )


async def handle_recipe_saved(event: RecipeSaved) -> None:
    await _save_audit_log(
        tenant_id=event.tenant_id,
        action="RECIPE_SAVED",
        entity_type="recipe",
        entity_id=str(event.menu_item_id),
        details=f"Receita salva/atualizada para o menu item {event.menu_item_id} com {event.ingredient_count} ingredientes.",
    )


async def handle_menu_item_created(event: MenuItemCreated) -> None:
    await _save_audit_log(
        tenant_id=event.tenant_id,
        action="MENU_ITEM_CREATED",
        entity_type="menu_item",
        entity_id=str(event.item_id),
        details=f"Item do cardápio '{event.name}' criado com preço base R$ {event.price:.2f} na categoria {event.category}.",
    )


async def handle_menu_item_updated(event: MenuItemUpdated) -> None:
    status_str = "disponível" if event.is_available else "indisponível"
    await _save_audit_log(
        tenant_id=event.tenant_id,
        action="MENU_ITEM_UPDATE",
        entity_type="menu_item",
        entity_id=str(event.item_id),
        details=f"Item do cardápio '{event.name}' atualizado. Preço base: R$ {event.price:.2f}, status: {status_str}.",
    )


async def handle_menu_item_deleted(event: MenuItemDeleted) -> None:
    await _save_audit_log(
        tenant_id=event.tenant_id,
        action="MENU_ITEM_DELETE",
        entity_type="menu_item",
        entity_id=str(event.item_id),
        details=f"Item do cardápio ID {event.item_id} removido.",
    )


async def handle_price_list_created(event: PriceListCreated) -> None:
    await _save_audit_log(
        tenant_id=event.tenant_id,
        action="PRICE_LIST_CREATED",
        entity_type="price_list",
        entity_id=str(event.price_list_id),
        details=f"Lista de preços '{event.name}' criada.",
    )


async def handle_price_list_updated(event: PriceListUpdated) -> None:
    status_str = "ativa" if event.is_active else "inativa"
    await _save_audit_log(
        tenant_id=event.tenant_id,
        action="PRICE_LIST_UPDATE",
        entity_type="price_list",
        entity_id=str(event.price_list_id),
        details=f"Lista de preços '{event.name}' atualizada. Status: {status_str}.",
    )


async def handle_price_list_deleted(event: PriceListDeleted) -> None:
    await _save_audit_log(
        tenant_id=event.tenant_id,
        action="PRICE_LIST_DELETE",
        entity_type="price_list",
        entity_id=str(event.price_list_id),
        details=f"Lista de preços ID {event.price_list_id} removida.",
    )


async def handle_price_list_item_added(event: PriceListItemAdded) -> None:
    await _save_audit_log(
        tenant_id=event.tenant_id,
        action="PRICE_LIST_ITEM_ADD",
        entity_type="price_list",
        entity_id=str(event.price_list_id),
        details=f"Item de cardápio ID {event.menu_item_id} adicionado à lista de preços com valor R$ {event.price_amount:.2f}.",
    )


async def handle_price_list_item_removed(event: PriceListItemRemoved) -> None:
    await _save_audit_log(
        tenant_id=event.tenant_id,
        action="PRICE_LIST_ITEM_REMOVE",
        entity_type="price_list",
        entity_id=str(event.price_list_id),
        details=f"Item de cardápio ID {event.menu_item_id} removido da lista de preços.",
    )


async def handle_price_list_item_updated(event: PriceListItemUpdated) -> None:
    await _save_audit_log(
        tenant_id=event.tenant_id,
        action="PRICE_LIST_ITEM_UPDATE",
        entity_type="price_list",
        entity_id=str(event.price_list_id),
        details=f"Preço do item de cardápio ID {event.menu_item_id} alterado de R$ {event.old_price_amount:.2f} para R$ {event.new_price_amount:.2f}.",
    )


async def handle_order_item_added(event: OrderItemAdded) -> None:
    await _save_audit_log(
        tenant_id=event.tenant_id,
        action="ORDER_ITEM_ADD",
        entity_type="order",
        entity_id=str(event.order_id),
        details=f"Item '{event.name}' (Qtd: {event.quantity}, Valor: R$ {event.price:.2f}) adicionado à comanda ID {event.order_id}.",
    )


async def handle_kitchen_item_status_changed(event: KitchenItemStatusChanged) -> None:
    action_map = {
        "WAITING": "Aguardando",
        "PREPARING": "Em Preparo",
        "READY": "Pronto",
        "CANCELLED": "Cancelado",
        "SURPLUS": "Excedente",
    }
    old_label = action_map.get(event.old_state, event.old_state)
    new_label = action_map.get(event.new_state, event.new_state)
    await _save_audit_log(
        tenant_id=event.tenant_id,
        action=f"KITCHEN_STATUS_{event.new_state}",
        entity_type="kitchen_item",
        entity_id=str(event.item_id),
        details=f"Item de cozinha '{event.name}' (ID: {event.item_id}, Comanda Ref ID: {event.correlation_id}) alterou de '{old_label}' para '{new_label}'.",
    )


async def handle_order_created(event: OrderCreated) -> None:
    await _save_audit_log(
        tenant_id=event.tenant_id,
        action="ORDER_CREATED",
        entity_type="order",
        entity_id=str(event.order_id),
        details=f"Comanda ID {event.order_id} (Código: {event.display_code}) criada com tipo de atendimento {event.fulfillment_type}.",
    )


async def handle_kitchen_item_created(event: KitchenItemCreated) -> None:
    details = f"Item de cozinha '{event.name}' (ID: {event.item_id}, Comanda Ref ID: {event.correlation_id}) enviado para a praça {event.station_type}."
    if event.notes:
        details += f" Observações: {event.notes}."
    await _save_audit_log(
        tenant_id=event.tenant_id,
        action="KITCHEN_ITEM_CREATED",
        entity_type="kitchen_item",
        entity_id=str(event.item_id),
        details=details,
    )


def register_audit_listeners() -> None:
    """Subscribes all audit log handler functions to their corresponding domain events."""
    EventBus.register(StockItemCreated, handle_stock_item_created)
    EventBus.register(StockAdjusted, handle_stock_adjusted)
    EventBus.register(StockTransactionRegistered, handle_stock_transaction_registered)
    EventBus.register(RecipeSaved, handle_recipe_saved)

    EventBus.register(MenuItemCreated, handle_menu_item_created)
    EventBus.register(MenuItemUpdated, handle_menu_item_updated)
    EventBus.register(MenuItemDeleted, handle_menu_item_deleted)

    EventBus.register(PriceListCreated, handle_price_list_created)
    EventBus.register(PriceListUpdated, handle_price_list_updated)
    EventBus.register(PriceListDeleted, handle_price_list_deleted)
    EventBus.register(PriceListItemAdded, handle_price_list_item_added)
    EventBus.register(PriceListItemRemoved, handle_price_list_item_removed)
    EventBus.register(PriceListItemUpdated, handle_price_list_item_updated)

    EventBus.register(OrderCreated, handle_order_created)
    EventBus.register(OrderItemAdded, handle_order_item_added)
    EventBus.register(KitchenItemCreated, handle_kitchen_item_created)
    EventBus.register(KitchenItemStatusChanged, handle_kitchen_item_status_changed)
