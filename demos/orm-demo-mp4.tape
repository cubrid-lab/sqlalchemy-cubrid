# sqlalchemy-cubrid — ORM demo (MP4 for docs site)
Output docs/assets/videos/orm-demo.mp4
Set FontSize 18
Set Width 800
Set Height 450
Set Theme "Catppuccin Mocha"
Set Shell bash
Set Framerate 24

Type@50ms 'pip install "sqlalchemy-cubrid[pycubrid]"'
Enter
Sleep 3s

Type@50ms "python3"
Enter
Sleep 1s

Type@30ms "from sqlalchemy import create_engine, text"
Enter
Sleep 300ms

Type@30ms 'engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")'
Enter
Sleep 500ms

Type@30ms 'with engine.connect() as conn:'
Enter
Sleep 200ms

Type@30ms '    result = conn.execute(text("SELECT 1 + 1 AS answer"))'
Enter
Sleep 200ms

Type@30ms '    print(f"Result: {result.scalar()}")'
Enter
Sleep 1s

Type@30ms 'print("SQLAlchemy 2.0 + CUBRID — full ORM support")'
Enter
Sleep 1s

Ctrl+D
