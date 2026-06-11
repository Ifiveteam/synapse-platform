"""Import all ORM modules so Alembic autogenerate sees Base.metadata."""


def import_all_models() -> None:
    import app.models.video_vector  # noqa: F401
