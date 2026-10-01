# hopper-documentation-openai

Incremental conversation records for Codex, with a separate writer and native
hooks for compaction and resumption. Default writer: **GPT-6 Luna, xhigh**.

- [English package](hopper-documentation-openai-en/README.md)
- [Pacote em português](hopper-documentation-openai-pt-br/README.md)
- [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [License](LICENSE)

Both languages share the same Python code and skill identity. Install one
language. The root marketplace selects Portuguese. Each language package also
has its own marketplace. CLI and desktop use the account's native installation.

## Install

Download one package and `SHA256SUMS` from the [release](https://github.com/jonathanpah/hopper-documentation-openai/releases).
Verify its checksum, extract it into a permanent directory, then run:

```sh
codex plugin marketplace add /absolute/path/to/extracted-package
codex plugin add hopper-documentation-openai@hopper-documentation-openai
```

Alternatively, the repository marketplace selects Portuguese:

```sh
codex plugin marketplace add jonathanpah/hopper-documentation-openai --ref v0.1.0
codex plugin add hopper-documentation-openai@hopper-documentation-openai
```

Review both hook definitions through `/hooks` before trusting them. Enable the
native hooks feature if your host has it disabled. Installing does not grant
hook trust. A new session loads the installed skill; this procedure does not
restart existing conversations.

Invoke `$hopper-documentation-openai:hopper-documentation-openai` to record a
conversation. Records go to `docs-by-hopper-documentation-openai` in its working
directory. Requires Python 3.9+ and authenticated Codex with the app-server and
hook interfaces described in the package. No additional API key or Python packages.
