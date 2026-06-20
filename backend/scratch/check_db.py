import asyncio

from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth.infrastructure.orm_models import TenantORM

DATABASE_URL = (
    "postgresql+asyncpg://comandafacil:change_me_in_production@localhost:5432/comandafacil"
)
MONGO_URL = "mongodb://comandafacil:change_me_in_production@localhost:27017/comandafacil_read?authSource=admin"


async def check() -> None:
    print("Connecting to Postgres...")
    engine = create_async_engine(DATABASE_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # Count tenants
        count_stmt = select(func.count(TenantORM.id))
        count_result = await session.execute(count_stmt)
        total_tenants = count_result.scalar()
        print(f"Total tenants in Postgres: {total_tenants}")

        # Get first 5 tenants
        tenants_stmt = select(TenantORM).limit(5)
        tenants_result = await session.execute(tenants_stmt)
        tenants = tenants_result.scalars().all()
        print("First 5 tenants in Postgres:")
        for t in tenants:
            print(
                f"  Tenant(id={t.id}, name={t.name!r}, plan_type={t.plan_type!r}, is_active={t.is_active})"
            )

        # Get last 5 tenants
        tenants_stmt_last = select(TenantORM).order_by(TenantORM.id.desc()).limit(5)
        tenants_result_last = await session.execute(tenants_stmt_last)
        tenants_last = tenants_result_last.scalars().all()
        print("Last 5 tenants in Postgres:")
        for t in tenants_last:
            print(
                f"  Tenant(id={t.id}, name={t.name!r}, plan_type={t.plan_type!r}, is_active={t.is_active})"
            )

    await engine.dispose()

    print("\nConnecting to MongoDB...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["comandafacil_read"]

    orders_count = await db["orders_read"].count_documents({})
    print(f"Total documents in orders_read: {orders_count}")

    # Inspect some documents in orders_read
    cursor = db["orders_read"].find({}).limit(5)
    orders = await cursor.to_list(length=5)
    print("First 5 orders in MongoDB orders_read:")
    for o in orders:
        print(
            f"  Order(order_id={o.get('order_id')}, tenant_id={o.get('tenant_id')!r}, total={o.get('total')})"
        )

    # Group by tenant_id in Mongo
    pipeline = [
        {
            "$group": {
                "_id": "$tenant_id",
                "total_revenue": {"$sum": "$total"},
                "count": {"$sum": 1},
            }
        },
    ]
    agg_cursor = db["orders_read"].aggregate(pipeline)
    agg_results = await agg_cursor.to_list(length=None)
    print("Aggregation by tenant_id in orders_read:")
    for res in agg_results:
        print(
            f"  Tenant ID: {res.get('_id')!r}, count: {res.get('count')}, total_revenue: {res.get('total_revenue')}"
        )

    client.close()


if __name__ == "__main__":
    asyncio.run(check())
