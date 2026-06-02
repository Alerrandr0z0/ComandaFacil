from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.dependencies import db_session
from app.main import app
from app.payment.domain.enums import PaymentMethod, PaymentStatus
from app.payment.domain.payment import Payment
from app.payment.infrastructure.pg_repository import SQLAlchemyPaymentRepository
from app.shared.base_orm import Base
from app.shared.money import Money

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture
async def sqlite_session() -> AsyncGenerator[AsyncSession, None]:
    """In-memory SQLite session with all database schemas generated."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest.fixture
async def api_client(sqlite_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP Client that overrides db_session to use our temporary SQLite db."""

    async def override_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield sqlite_session

    app.dependency_overrides[db_session] = override_db_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Tenant-ID": "franquia_001"},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_payment_repository_persistence_success(sqlite_session: AsyncSession) -> None:
    # Arrange
    repo = SQLAlchemyPaymentRepository(sqlite_session)
    payment = Payment(
        id=10,
        order_id=42,
        tenant_id="franquia_001",
        amount=Money.from_float(75.50),
        method=PaymentMethod.PIX,
    )

    # Act
    await repo.save(payment)
    await sqlite_session.commit()

    # Assert
    persisted = await repo.find_by_id(10, "franquia_001")
    assert persisted is not None
    assert persisted.order_id == 42
    assert persisted.amount.amount == Decimal("75.50")
    assert persisted.method == PaymentMethod.PIX
    assert persisted.status == PaymentStatus.PENDING

    persisted_by_order = await repo.find_by_order(42, "franquia_001")
    assert persisted_by_order is not None
    assert persisted_by_order.id == 10


@pytest.mark.asyncio
async def test_request_payment_endpoint_cash_success(api_client: AsyncClient) -> None:
    # Act: Request CASH payment (processed locally instantly without calling external Stripe)
    response = await api_client.post(
        "/api/v1/payments/request",
        json={
            "order_id": 100,
            "amount": "25.00",
            "method": "CASH",
        },
    )

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["order_id"] == 100
    assert json_data["amount"] == "25.00"
    assert json_data["method"] == "CASH"
    assert json_data["status"] == "CONFIRMED"
    assert json_data["gateway_ref"] == "ch_cash_2500"


@pytest.mark.asyncio
async def test_request_payment_endpoint_card_success(api_client: AsyncClient) -> None:
    # Arrange: Mock StripeGateway.charge to return a successful GatewayResponse
    from app.payment.domain.gateway import GatewayResponse

    with patch(
        "app.payment.infrastructure.stripe_gateway.StripeGateway.charge",
        return_value=GatewayResponse(
            success=True, gateway_ref="pi_test_intent_999", error_message=None
        ),
    ) as mock_charge:
        # Act
        response = await api_client.post(
            "/api/v1/payments/request",
            json={
                "order_id": 101,
                "amount": "150.00",
                "method": "CREDIT_CARD",
            },
        )

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "CONFIRMED"
    assert json_data["gateway_ref"] == "pi_test_intent_999"
    mock_charge.assert_called_once()


@pytest.mark.asyncio
async def test_request_payment_endpoint_card_failure(api_client: AsyncClient) -> None:
    # Arrange: Mock StripeGateway.charge to return a failed GatewayResponse
    from app.payment.domain.gateway import GatewayResponse

    with patch(
        "app.payment.infrastructure.stripe_gateway.StripeGateway.charge",
        return_value=GatewayResponse(
            success=False, gateway_ref=None, error_message="Your card was declined."
        ),
    ) as mock_charge:
        # Act
        response = await api_client.post(
            "/api/v1/payments/request",
            json={
                "order_id": 102,
                "amount": "150.00",
                "method": "CREDIT_CARD",
            },
        )

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "FAILED"
    assert json_data["gateway_ref"] is None
    assert json_data["failure_reason"] == "Your card was declined."
    mock_charge.assert_called_once()


@pytest.mark.asyncio
async def test_refund_payment_endpoint_card_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange: Insert confirmed payment first
    repo = SQLAlchemyPaymentRepository(sqlite_session)
    payment = Payment(
        id=20,
        order_id=200,
        tenant_id="franquia_001",
        amount=Money.from_float(50.00),
        method=PaymentMethod.CREDIT_CARD,
    )
    payment.confirm(gateway_ref="pi_stripe_to_refund")
    await repo.save(payment)
    await sqlite_session.commit()

    # Mock StripeGateway.refund to return a successful GatewayResponse
    from app.payment.domain.gateway import GatewayResponse

    with patch(
        "app.payment.infrastructure.stripe_gateway.StripeGateway.refund",
        return_value=GatewayResponse(
            success=True, gateway_ref="re_stripe_refund_999", error_message=None
        ),
    ) as mock_refund:
        # Act
        response = await api_client.post(
            "/api/v1/payments/refund",
            json={
                "order_id": 200,
            },
        )

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "REFUNDED"
    assert json_data["gateway_ref"] == "pi_stripe_to_refund"
    mock_refund.assert_called_once()


@pytest.mark.asyncio
async def test_get_payment_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange: Insert a payment record
    repo = SQLAlchemyPaymentRepository(sqlite_session)
    payment = Payment(
        id=30,
        order_id=300,
        tenant_id="franquia_001",
        amount=Money.from_float(80.00),
        method=PaymentMethod.DEBIT_CARD,
    )
    payment.confirm(gateway_ref="pi_debit_300")
    await repo.save(payment)
    await sqlite_session.commit()

    # Act
    response = await api_client.get("/api/v1/payments/order/300")

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["order_id"] == 300
    assert json_data["amount"] == "80.00"
    assert json_data["status"] == "CONFIRMED"
    assert json_data["gateway_ref"] == "pi_debit_300"


@pytest.mark.asyncio
async def test_get_payment_endpoint_not_found(api_client: AsyncClient) -> None:
    # Act
    response = await api_client.get("/api/v1/payments/order/99999")

    # Assert
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_request_payment_invalid_method_returns_400(api_client: AsyncClient) -> None:
    # Act
    response = await api_client.post(
        "/api/v1/payments/request",
        json={"order_id": 400, "amount": "50.00", "method": "BITCOIN"},
    )

    # Assert
    assert response.status_code == 400
    assert "BITCOIN" in response.json()["detail"]


@pytest.mark.asyncio
async def test_request_payment_zero_amount_returns_422(api_client: AsyncClient) -> None:
    # Act
    response = await api_client.post(
        "/api/v1/payments/request",
        json={"order_id": 401, "amount": "0.00", "method": "CASH"},
    )

    # Assert
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_refund_payment_not_found_returns_400(api_client: AsyncClient) -> None:
    # Act
    response = await api_client.post(
        "/api/v1/payments/refund",
        json={"order_id": 99999},
    )

    # Assert
    assert response.status_code == 400
    assert "No payment record" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refund_payment_wrong_state_returns_400(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange: Insert a PENDING payment
    repo = SQLAlchemyPaymentRepository(sqlite_session)
    payment = Payment(
        id=40,
        order_id=401,
        tenant_id="franquia_001",
        amount=Money.from_float(30.0),
        method=PaymentMethod.PIX,
    )
    await repo.save(payment)
    await sqlite_session.commit()

    # Act
    response = await api_client.post(
        "/api/v1/payments/refund",
        json={"order_id": 401},
    )

    # Assert
    assert response.status_code == 400
    assert "Cannot refund" in response.json()["detail"]
