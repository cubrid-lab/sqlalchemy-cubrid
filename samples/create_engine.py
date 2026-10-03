# samples/create_engine.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Basic example: create an engine and execute a query.

Install the recommended pure-Python driver with:
    pip install "sqlalchemy-cubrid[pycubrid]"
"""

from sqlalchemy import create_engine, text

# Replace with your CUBRID connection details
engine = create_engine("cubrid+pycubrid://dba:password@localhost:33000/demodb")

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1 + 1 AS answer"))
    for row in result:
        print(row)

engine.dispose()
