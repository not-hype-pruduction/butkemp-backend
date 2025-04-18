def register_all_handlers(dp):
    """Регистрирует все обработчики"""
    from handlers.common import register_handlers as register_common
    from handlers.assistant import register_handlers as register_assistant
    from handlers.career_test import register_handlers as register_test
    from handlers.career_guidance import register_handlers as register_guidance
    from handlers.recipe import register_handlers as register_recipe

    # Регистрация обработчиков
    register_common(dp)
    register_assistant(dp)
    register_test(dp)
    register_guidance(dp)
    register_recipe(dp)