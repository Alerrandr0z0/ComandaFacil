import datetime
import pytest

from app.auth.domain.tenant import Tenant, PlanType
from app.auth.domain.employee import Employee, RoleType, ManagerStrategy, WaiterStrategy, CookStrategy, CashierStrategy
from app.auth.domain.session import Session
from app.shared.exceptions import DomainException
from app.shared.value_objects import Email


def test_tenant_creation_and_status() -> None:
    tenant = Tenant(id=1, name="ComandaFacil Franquia 1", plan_type=PlanType.PRO, is_active=True)
    assert tenant.id == 1
    assert tenant.name == "ComandaFacil Franquia 1"
    assert tenant.plan_type == PlanType.PRO
    assert tenant.is_active is True
    assert tenant.is_active_tenant() is True


def test_employee_creation_and_password() -> None:
    email = Email("waiter@comandafacil.com")
    employee = Employee(
        id=1,
        name="John Doe",
        email=email,
        password_hash="hashed_dummy",
    )
    assert employee.id == 1
    assert employee.name == "John Doe"
    assert employee.email == email
    
    employee.set_password("secure_password")
    assert employee.check_password("secure_password") is True
    assert employee.check_password("wrong_password") is False


def test_employee_role_management() -> None:
    tenant = Tenant(id=1, name="Franquia 1", plan_type=PlanType.BASIC, is_active=True)
    email = Email("waiter@comandafacil.com")
    employee = Employee(id=1, name="John Doe", email=email, password_hash="")
    
    assert len(employee.roles) == 0
    
    employee.add_role(tenant, RoleType.WAITER)
    assert len(employee.roles) == 1
    
    role = employee.get_role_for_tenant(tenant)
    assert role is not None
    assert role.role_type == RoleType.WAITER
    assert role.tenant_id == tenant.id
    
    employee.remove_role(tenant)
    assert len(employee.roles) == 0
    with pytest.raises(DomainException):
        employee.get_role_for_tenant(tenant)


def test_session_lifecycle() -> None:
    now = datetime.datetime.now(datetime.timezone.utc)
    future = now + datetime.timedelta(hours=1)
    past = now - datetime.timedelta(hours=1)
    
    session = Session(
        session_id="session_123",
        employee_id=1,
        tenant_id=1,
        expires_at=future,
    )
    assert session.session_id == "session_123"
    assert session.is_expired() is False
    
    expired_session = Session(
        session_id="session_456",
        employee_id=1,
        tenant_id=1,
        expires_at=past,
    )
    assert expired_session.is_expired() is True


def test_employee_permission_strategies() -> None:
    manager = ManagerStrategy()
    waiter = WaiterStrategy()
    cook = CookStrategy()
    cashier = CashierStrategy()
    
    assert manager.permits("CREATE_ORDER") is True
    assert manager.permits("CLOSE_ORDER") is True
    assert manager.permits("PREPARE_ITEM") is True
    assert manager.permits("ADJUST_STOCK") is True
    
    assert waiter.permits("CREATE_ORDER") is True
    assert waiter.permits("PREPARE_ITEM") is False
    assert waiter.permits("ADJUST_STOCK") is False
    
    assert cook.permits("PREPARE_ITEM") is True
    assert cook.permits("CREATE_ORDER") is False
    
    assert cashier.permits("CLOSE_ORDER") is True
    assert cashier.permits("CREATE_ORDER") is False


def test_role_permissions_resolver() -> None:
    from app.auth.domain.employee import RolePermissions
    
    assert isinstance(RolePermissions.resolver(RoleType.MANAGER), ManagerStrategy)
    assert isinstance(RolePermissions.resolver("WAITER"), WaiterStrategy)
    assert isinstance(RolePermissions.resolver("COOK"), CookStrategy)
    assert isinstance(RolePermissions.resolver("CASHIER"), CashierStrategy)
    
    with pytest.raises(ValueError):
        RolePermissions.resolver("INVALID_ROLE")


def test_employee_permits_delegation() -> None:
    # Testing clean OOP delegation: Employee Aggregate Root checks its own permissions
    tenant_1 = Tenant(id=1, name="Franquia 1", plan_type=PlanType.BASIC, is_active=True)
    tenant_2 = Tenant(id=2, name="Franquia 2", plan_type=PlanType.PRO, is_active=True)
    
    email = Email("john@comandafacil.com")
    employee = Employee(id=1, name="John Doe", email=email, password_hash="")
    
    # Assign different roles in different tenants
    employee.add_role(tenant_1, RoleType.WAITER)
    employee.add_role(tenant_2, RoleType.COOK)
    
    # In Tenant 1 (Waiter): permits CREATE_ORDER, but not PREPARE_ITEM
    assert employee.permits("CREATE_ORDER", tenant_1) is True
    assert employee.permits("PREPARE_ITEM", tenant_1) is False
    
    # In Tenant 2 (Cook): permits PREPARE_ITEM, but not CREATE_ORDER
    assert employee.permits("PREPARE_ITEM", tenant_2) is True
    assert employee.permits("CREATE_ORDER", tenant_2) is False
    
    # In Tenant 3 (where they have no role): should return False, no exceptions raised
    tenant_3 = Tenant(id=3, name="Franquia 3", plan_type=PlanType.PLUS, is_active=True)
    assert employee.permits("CREATE_ORDER", tenant_3) is False
