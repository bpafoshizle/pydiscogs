# pydiscogs

A collection of shared cogs to be used to implement features across discord bots

## Steps to set up virtual environment

Create a virtual environment folder called 'env'

- `python3 -m venv env`
- `source env/bin/activate`
- `python3 -m pip install --upgrade pip`
- `python3 -m pip install --upgrade build`
- `python3 -m pip install --upgrade twine`

## Steps to build and upload to pypi

Should be run in virtual environment

- `python3 -m build`
- `python3 -m twine upload --repository testpypi dist/* --verbose`
- `pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple pydiscogs-bpafoshizle==[VERSION]`

## Importing

The name of the module to import is completely independent of the name of your package on pypi. The import name is ultimately derived from the name of the folder in which you house your source when you run the `python -m build` command.

## Testing

Run the following from the top level directory.

`python -m unittest discover -v -s src`

This will test an individual file.

`python -m unittest discover -v src -p 'test_stocks.py'`


### Development WIP ###
```python
twitch_client = twitchio.Client.from_client_credentials(
            client_id=os.getenv("TWITCH_BOT_CLIENT_ID"),
            client_secret=os.getenv("TWITCH_BOT_CLIENT_SECRET"),
        )

twitch_eventsub_client = eventsub.EventSubClient(
            client=twitch_client,
            webhook_secret=os.getenv("TWITCH_WEBHOOK_SECRET"),
            callback_route="https://bpafoshizle.com/webhooks/callback"
        )
        
users = asyncio.run(twitch_client.fetch_users(join_channels))
# [<User id=108647345 name=bpafoshizle display_name=bpafoshizle type=UserTypeEnum.none>, <User id=235807313 name=ephenry84 display_name=ephenry84 type=UserTypeEnum.none>, <User id=168197731 name=elzblazin display_name=elzblazin type=UserTypeEnum.none>, <User id=643319849 name=kuhouseii display_name=KuhouseII type=UserTypeEnum.none>, <User id=653518175 name=fwm_bot display_name=FWM_Bot type=UserTypeEnum.none>]
response = asyncio.run(twitch_eventsub_client.subscribe_channel_stream_start(108647345))
```