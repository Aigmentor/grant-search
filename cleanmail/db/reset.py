from alembic.config import Config
from alembic import command
from cleanmail.db.models import Base
from cleanmail.db.database import engine, get_session


def reset():

    # Drop all tables
    Base.metadata.drop_all(engine)

    # Recreate all tables
    Base.metadata.create_all(engine)

    # Create a session
    session = get_session()

    # Commit the changes
    session.commit()

    # Close the session
    session.close()

    alembic_cfg = Config("alembic.ini")

    # Stamp the database with the latest revision
    command.stamp(alembic_cfg, "head")
    print("Database reset complete!")


if __name__ == "__main__":
    reset()
