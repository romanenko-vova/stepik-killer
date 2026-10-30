from sqlalchemy.orm import declarative_base

# отдельно от database.py: alembic и модели импортируют Base без создания engine
Base = declarative_base()
