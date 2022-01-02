# I attempted this method and I don't think it's ideal because the decorator first pass executes the decorator function, but you have to make a call
# to the decorated function in the __init__ constructor to then execute the inner portion, which actually adds the command to the list. However, even when 
# going through all that, which is not ideal, it then for some reason fails to pass the ctx to the decorated function. 

from functools import wraps

def pydiscog_slash_command(**kwargs):
    def decorator(func):
        print("!!!!!!!!!!!!DECORATOR!!!!!!!!!!!!")
        @wraps(func)
        def wrapper(self, ctx, *args, **kwargs):
            print("!!!!!!!!!!!!WRAPPER!!!!!!!!!!!!")
            # decorate the function with the original decorator, pass guild_ids
            return self.bot.slash_command(guild_ids=self.guild_ids, **kwargs)(func)
        return wrapper
    return decorator
