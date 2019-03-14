import os
from .models import DeclarativeBase
from sqlalchemy import create_engine


def create_db():

    db_user = os.getenv("DB_USER",'postgres')
    db_password = os.getenv("DB_PASSWORD", 'password')
    db_host = os.getenv("DB_HOST", 'localhost')
    db_port = os.getenv("DB_PORT", '5432')

    db_url = 'postgresql://{}:{}@{}:{}/catalog'.format(db_user, db_password, db_host, db_port)

    db = create_engine(db_url)
    db.execute('CREATE SEQUENCE IF NOT EXISTS news_id_seq START 1;')
    DeclarativeBase.metadata.create_all(db)


if __name__ == '__main__':
    print('creating databases')
    create_db()
    print('databases created')
