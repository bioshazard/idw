# LangChain Agent with Llama

This repo contains (so far) a few scratch attempts at a reliable QA agent w/ search using Hermes 13b Llama 2. I will add to it as I go and welcome issues/PRs/ideas.

## Quick Start

Very rough draft so far, but you can symlink the `idw` python library and try an example pretty simply:

```bash
# run a llama-cpp-python.server with hermes 13b llama2 ggml 6k
pip install -e src/lib/idw
cd src/examples
cp -v env.dist .env
# ^ be sure to configure your .env
python src/examples/test.py
```
