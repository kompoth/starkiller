# Development

## Installing plugin in development

Build wheels and install them with a script:

```bash
uv build
./scripts/install.sh
```

The script takes the latest version from `dist/` (created by `uv build`) and injects it into `pylsp` environment.

## Publishing

```bash
UV_PUBLISH_TOKEN=<pypi token> ./script/publish.sh patch
```

This will  do the following:
1. Increment the version in `pyproject.toml`, commit this change and tag it.
2. Build the package distribution.
3. Publish it to the PyPI.
