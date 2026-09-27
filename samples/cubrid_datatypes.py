# samples/cubrid_datatypes.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Example: create tables with CUBRID-specific data types.

Install the recommended pure-Python driver with:
    pip install "sqlalchemy-cubrid[pycubrid]"
"""

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine

from sqlalchemy_cubrid import BIGINT, SET, STRING, VARCHAR

# Replace with your CUBRID connection details
engine = create_engine("cubrid+pycubrid://dba:password@localhost:33000/demodb")

metadata = MetaData()

# Table with standard SQLAlchemy types
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100)),
)

# Table with CUBRID-specific types
products = Table(
    "products",
    metadata,
    Column("id", BIGINT, primary_key=True),
    Column("name", VARCHAR(200)),
    Column("description", STRING),
    Column("tags", SET(VARCHAR(50))),
)

# Create tables (SA 2.0 style)
metadata.create_all(engine)

engine.dispose()
