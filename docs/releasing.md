# Releasing to PyPI

Releases are published by the workflow
[`.github/workflows/publish.yml`](../.github/workflows/publish.yml) when a tag
`v<version>` is pushed. It uses PyPI's
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/): PyPI accepts
the upload because it comes from that workflow, in this repository, in the
GitHub environment `pypi`. No token or password is stored anywhere.

## Once, before the first release

1. **On GitHub**, in the repository's *Settings › Environments*, create an
   environment named exactly `pypi`. Adding yourself as a required reviewer
   means every release waits for your approval before anything is uploaded.
2. **On PyPI**, in your account's *Publishing* page (the account sidebar,
   not a project's: the project does not exist yet), add a pending publisher
   for GitHub Actions:

   | Field | Value |
   | --- | --- |
   | PyPI project name | `actasum` |
   | Owner | `arfonzeras` |
   | Repository name | `actasum` |
   | Workflow name | `publish.yml` |
   | Environment name | `pypi` |

A pending publisher does not reserve the name: if someone else registers
`actasum` on PyPI before the first upload, it is invalidated. After the first
successful upload it becomes an ordinary trusted publisher.

## Each release

1. Set `version` in `pyproject.toml` and merge it into `main`.
2. Tag that commit and push the tag:

   ```sh
   git tag v0.1.0
   git push origin v0.1.0
   ```

The workflow refuses a tag that is not `v` followed by the version in
`pyproject.toml`. Before uploading it runs the tests, builds the source
distribution and the wheel, checks their metadata with `twine check
--strict`, and installs the wheel in a new environment. A version, once
uploaded to PyPI, cannot be uploaded again, even after deleting it.

## What the packages contain

- The wheel: the `actasum` package and its licence.
- The source distribution: the same, plus the tests (with `tests/synth.py`,
  which they need) and the JSON Schema.

Neither contains election data, findings or specifications. The project's
metadata names the author by GitHub account only, with no e-mail address.
