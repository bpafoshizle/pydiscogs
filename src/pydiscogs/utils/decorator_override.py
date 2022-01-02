from functools import wraps

def pydiscog_slash_command(**kwargs):
    def decorator(func):
        print("!!!!!!!!!!!!DECORATOR!!!!!!!!!!!!")
        @wraps(func)
        def wrapper(self, ctx, *args, **kwargs):
            print("!!!!!!!!!!!!WRAPPER!!!!!!!!!!!!")
            # decorate the function with the original decorator, pass guild_ids
            return self.bot.slash_command(guild_ids=self.guild_ids, **kwargs)(func)(self, ctx, *args, **kwargs)
        return wrapper
    return decorator
