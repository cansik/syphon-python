# CI and releases

The build workflow checks pushes and pull requests. It builds a universal wheel from the source
archive, checks Ruff and documentation, and uses four routine test jobs covering the oldest and
newest supported Python versions, free-threaded Python, Apple Silicon, and Intel. Release validation
and manual full runs use ten test jobs for broader Python coverage. Both tiers test the installed
wheel with and without optional dependencies; native tests run on selected entries, and the full
Apple Silicon Python 3.14 entry also checks a clean source build. Metal tests skip when a runner has
no Metal device; a passing job with those skips does not validate GPU transfers.

To publish, run **Publish release** manually on the default branch and select PyPI, GitHub Releases,
or both. With neither selected, it only builds and validates. All validation jobs must pass before
publication. The version in `pyproject.toml` determines the release tag (`v0.3.0` for this version).
Use a new version for each release; existing releases and packages are not overwritten.

Before the first PyPI publication, configure a GitHub trusted publisher on PyPI for owner `cansik`,
repository `syphon-python`, workflow `publish.yml`, and environment `pypi`. Create that GitHub
environment and configure any desired reviewer protection. Publication uses OIDC and needs no
PyPI API token. See the [PyPI trusted publishing guide](https://docs.pypi.org/trusted-publishers/adding-a-publisher/).

For documentation hosting, select **GitHub Actions** as the repository's Pages source. The
**Publish documentation** workflow runs manually or on pushed `v*` tags. Tags created by the
release workflow's `GITHUB_TOKEN` do not trigger another workflow, so run documentation publication
manually after those releases.

