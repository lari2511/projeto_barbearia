from app.database import init_db, engine
from sqlalchemy import inspect

init_db()
inspector = inspect(engine)
print(inspector.get_table_names())
