# Development

## Installing plugin to debug

Build wheels and install them with a shortcut script:

```bash
./scripts/install_plugin.sh
```

## Publishing

Increment the package version, build the distribution and publish the latest version:

```bash
bump-my-version bump patch 
uv build
UV_PUBLISH_TOKEN=<pypi token> uv publish
```
