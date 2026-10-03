# Run from repository root against a disposable local testdb.
# The MP4 is intentionally unpublished until this recording executes successfully.
Output docs/assets/videos/orm-demo.mp4
Set FontSize 18
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"
Set Shell bash
Set Framerate 24

Type@50ms 'python -m pip install -e ".[pycubrid]" alembic'
Enter
Sleep 5s
Type@50ms 'python demos/orm_alembic_video.py'
Enter
Sleep 10s
