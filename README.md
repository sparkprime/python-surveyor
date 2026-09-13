# python-surveyor

A scanner for code that finds potential issues.
It is intentionally **recall-only**: every hit is a *candidate* with just enough
context attached for a human (or an LLM agent) to make the judgement call. The
tool never decides whether a hit is a real problem and never fixes anything.

## Install

```bash
uv pip install -e ".[dev]"
```

## Usage

```bash
python-surveyor --help
```
