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


## Specifying Depedency from Git in setup.cfg

Now that I am switching over to official pypi version of pycord, I didn't want to lose this syntax for posterity, since it was difficult to find and figure out. Will come in useful again I am sure.

```yaml
install_requires =
    py_cord @ git+https://github.com/Pycord-Development/pycord@master
    bs4==0.0.1
    pytz==2021.1
    twitchio>=2.0.2
    asyncpraw==7.5.0
    gfycat==0.2.2
    pyaml-env==1.1.3
```

## Specifying dependency from git in requirements.txt

This one is more common than the need to do this in the setup.cfg, but preserving it here in any case.
`git+https://github.com/Pycord-Development/pycord@master#egg=py_cord`


## AI Dev Notes

Curl Ollama endpoint on another local host:

```bash
curl http://bpapc.lan:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Why is the sky blue?",
  "stream": false
}'
```

## Run Superlinter Locally (once they get an arm container image, this would work...)
```bash
docker run \
  -e LOG_LEVEL=DEBUG \
  -e RUN_LOCAL=true \
  -v .:/tmp/lint \
  --rm \
  ghcr.io/super-linter/super-linter:latest
```

## Sync requirements.txt from uv: 

`uv pip compile pyproject.toml -o requirements.txt`
