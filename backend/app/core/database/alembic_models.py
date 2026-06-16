"""Import all ORM modules so Alembic autogenerate sees Base.metadata."""


def import_all_models() -> None:
    import app.models.user  # noqa: F401
    import app.models.user_feature_snapshot  # noqa: F401
    import app.models.user_ideal_persona  # noqa: F401
    import app.models.user_profile_history  # noqa: F401
    import app.models.user_profile_insight  # noqa: F401
    import app.models.user_token  # noqa: F401
    import app.models.user_video_watch  # noqa: F401
    import app.models.video_analysis  # noqa: F401
