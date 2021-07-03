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