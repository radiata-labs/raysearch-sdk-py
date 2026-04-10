rm -rf dist/**
python setup.py sdist bdist_wheel
uv run twine upload dist/*