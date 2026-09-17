# test/test_dogfood_orm.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Real-application ORM dogfood corpus (stabilization Phase 9).

The hand-written unit tests exercise the dialect one construct at a time. Real
applications do not: they drive the ORM through relationships, eager/lazy
loading strategies, multi-clause queries, pagination, transactions, and bulk
operations, all against a live server, and it is the *combination* of these that
tends to surface dialect bugs the single-construct tests miss (a compile path
that only fails when a JOIN meets a GROUP BY, a result-mapping bug that only
appears through a relationship, an eager-load that emits SQL CUBRID rejects).

This module models a small but realistic schema (users 1:N orders, orders N:M
tags) and drives it the way an application would, asserting on the *data* that
comes back rather than on generated SQL. Every test needs a live CUBRID and is
`integration`-marked; the nightly `integration-full` job runs the whole corpus
across all supported CUBRID versions.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Table,
    create_engine,
    func,
    select,
    text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    joinedload,
    mapped_column,
    relationship,
    selectinload,
)

_DEFAULT_URL = "cubrid+pycubrid://dba@localhost:33000/testdb"


def _cubrid_url() -> str:
    return os.environ.get("CUBRID_TEST_URL", _DEFAULT_URL)


def _can_connect() -> bool:
    try:
        engine = create_engine(_cubrid_url())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


_available = _can_connect()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _available,
        reason="CUBRID instance not available (set CUBRID_TEST_URL)",
    ),
]


class Base(DeclarativeBase):
    pass


order_tag = Table(
    "dogfood_order_tag",
    Base.metadata,
    Column("order_id", ForeignKey("dogfood_orders.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("dogfood_tags.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "dogfood_users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    orders: Mapped[list[Order]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Order(Base):
    __tablename__ = "dogfood_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("dogfood_users.id", ondelete="CASCADE"))
    amount: Mapped[int] = mapped_column()
    user: Mapped[User] = relationship(back_populates="orders")
    tags: Mapped[list[Tag]] = relationship(secondary=order_tag, back_populates="orders")


class Tag(Base):
    __tablename__ = "dogfood_tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(50))
    orders: Mapped[list[Order]] = relationship(secondary=order_tag, back_populates="tags")


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(_cubrid_url(), echo=False)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def seeded(engine):
    """Reset to a known dataset before each test: 3 users, orders, tags."""
    with Session(engine) as session:
        session.execute(text("DELETE FROM dogfood_order_tag"))
        session.execute(text("DELETE FROM dogfood_orders"))
        session.execute(text("DELETE FROM dogfood_users"))
        session.execute(text("DELETE FROM dogfood_tags"))
        session.commit()

    with Session(engine) as session:
        priority = Tag(label="priority")
        gift = Tag(label="gift")
        alice = User(
            name="alice",
            orders=[Order(amount=100, tags=[priority]), Order(amount=250)],
        )
        bob = User(name="bob", orders=[Order(amount=50, tags=[priority, gift])])
        carol = User(name="carol", orders=[])
        session.add_all([alice, bob, carol, priority, gift])
        session.commit()
    yield engine


# ---------------------------------------------------------------------------
# Relationship loading strategies
# ---------------------------------------------------------------------------


class TestRelationshipLoading:
    def test_lazy_load_collection(self, seeded):
        with Session(seeded) as session:
            alice = session.scalars(select(User).where(User.name == "alice")).one()
            assert sorted(o.amount for o in alice.orders) == [100, 250]

    def test_selectin_eager_load(self, seeded):
        with Session(seeded) as session:
            users = session.scalars(
                select(User).options(selectinload(User.orders)).order_by(User.name)
            ).all()
            counts = {u.name: len(u.orders) for u in users}
            assert counts == {"alice": 2, "bob": 1, "carol": 0}

    def test_joined_eager_load(self, seeded):
        with Session(seeded) as session:
            bob = (
                session.scalars(
                    select(User).options(joinedload(User.orders)).where(User.name == "bob")
                )
                .unique()
                .one()
            )
            assert [o.amount for o in bob.orders] == [50]

    def test_many_to_many_load(self, seeded):
        with Session(seeded) as session:
            priority = session.scalars(select(Tag).where(Tag.label == "priority")).one()
            amounts = sorted(o.amount for o in priority.orders)
            assert amounts == [50, 100]

    def test_back_populates_navigation(self, seeded):
        with Session(seeded) as session:
            order = session.scalars(select(Order).where(Order.amount == 250)).one()
            assert order.user.name == "alice"


# ---------------------------------------------------------------------------
# Complex queries
# ---------------------------------------------------------------------------


class TestComplexQueries:
    def test_join_filter(self, seeded):
        with Session(seeded) as session:
            rows = session.execute(
                select(User.name, Order.amount)
                .join(Order, Order.user_id == User.id)
                .where(Order.amount >= 100)
                .order_by(Order.amount)
            ).all()
            assert rows == [("alice", 100), ("alice", 250)]

    def test_group_by_having(self, seeded):
        with Session(seeded) as session:
            rows = session.execute(
                select(User.name, func.sum(Order.amount).label("total"))
                .join(Order, Order.user_id == User.id)
                .group_by(User.name)
                .having(func.sum(Order.amount) > 100)
                .order_by(User.name)
            ).all()
            assert rows == [("alice", 350)]

    def test_aggregate_scalar(self, seeded):
        with Session(seeded) as session:
            total = session.scalar(select(func.sum(Order.amount)))
            assert total == 400
            count = session.scalar(select(func.count()).select_from(Order))
            assert count == 3

    def test_correlated_subquery(self, seeded):
        with Session(seeded) as session:
            avg_amount = select(func.avg(Order.amount)).scalar_subquery()
            rows = session.scalars(
                select(Order.amount).where(Order.amount > avg_amount).order_by(Order.amount)
            ).all()
            assert rows == [250]

    def test_pagination_limit_offset(self, seeded):
        with Session(seeded) as session:
            page = session.scalars(
                select(Order.amount).order_by(Order.amount).limit(2).offset(1)
            ).all()
            assert page == [100, 250]

    def test_left_outer_join_includes_orderless_user(self, seeded):
        with Session(seeded) as session:
            rows = session.execute(
                select(User.name, func.count(Order.id))
                .outerjoin(Order, Order.user_id == User.id)
                .group_by(User.name)
                .order_by(User.name)
            ).all()
            assert rows == [("alice", 2), ("bob", 1), ("carol", 0)]


# ---------------------------------------------------------------------------
# Transactions and mutations
# ---------------------------------------------------------------------------


class TestTransactionsAndMutations:
    def test_rollback_discards_changes(self, seeded):
        with Session(seeded) as session:
            session.add(User(name="temp"))
            session.flush()
            session.rollback()
        with Session(seeded) as session:
            names = session.scalars(select(User.name)).all()
            assert "temp" not in names

    def test_commit_persists_across_sessions(self, seeded):
        with Session(seeded) as session:
            session.add(User(name="dave"))
            session.commit()
        with Session(seeded) as session:
            dave = session.scalars(select(User).where(User.name == "dave")).one()
            assert dave.id is not None

    def test_bulk_update(self, seeded):
        with Session(seeded) as session:
            session.execute(
                Order.__table__.update().where(Order.amount < 100).values(amount=Order.amount + 5)
            )
            session.commit()
        with Session(seeded) as session:
            assert session.scalar(select(func.min(Order.amount))) == 55

    def test_cascade_delete_orphans_orders(self, seeded):
        with Session(seeded) as session:
            alice = session.scalars(select(User).where(User.name == "alice")).one()
            session.delete(alice)
            session.commit()
        with Session(seeded) as session:
            remaining = session.scalars(select(Order.amount).order_by(Order.amount)).all()
            assert remaining == [50]

    def test_autoincrement_pk_populated_after_flush(self, seeded):
        with Session(seeded) as session:
            u = User(name="erin")
            session.add(u)
            session.flush()
            assert isinstance(u.id, int) and u.id > 0
            session.rollback()
