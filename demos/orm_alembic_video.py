"""Record ORM queries and Alembic DDL against a disposable local testdb.

Run from the repository root; this script does not claim recording success.
An existing table is never dropped if create_table fails.
"""

from __future__ import annotations

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, Integer, String, create_engine, inspect, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Demo(Base):
    __tablename__ = "sqlalchemy_cubrid_video_demo"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40))


def main() -> None:
    engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")
    created = False
    try:
        with engine.begin() as connection:
            operations = Operations(MigrationContext.configure(connection))
            operations.create_table(
                Demo.__tablename__,
                Column("id", Integer, primary_key=True),
                Column("name", String(40), nullable=False),
            )
        created = True
        with Session(engine) as session, session.begin():
            session.add(Demo(id=1, name="CUBRID ORM"))
        with Session(engine) as session:
            print("ORM query:", session.scalars(select(Demo.name)).all())
        with engine.begin() as connection:
            operations = Operations(MigrationContext.configure(connection))
            operations.add_column(Demo.__tablename__, Column("note", String(80)))
        print(
            "Alembic migration:",
            [c["name"] for c in inspect(engine).get_columns(Demo.__tablename__)],
        )
    finally:
        try:
            if created:
                with engine.begin() as connection:
                    Operations(MigrationContext.configure(connection)).drop_table(
                        Demo.__tablename__
                    )
        finally:
            engine.dispose()


if __name__ == "__main__":
    main()
