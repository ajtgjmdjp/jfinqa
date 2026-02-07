# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Benchmark framework: `Question`, `Table`, `QAPair` data models (FinQA-compatible)
- Three subtasks: numerical reasoning, consistency checking, temporal reasoning
- Evaluation engine with exact match and numerical match modes
- Japanese financial number normalization (kanji multipliers, fullwidth digits, triangle negative)
- HuggingFace `datasets` integration
- Click CLI (`evaluate`, `inspect`)
- lm-evaluation-harness YAML task configs
- 5 sample questions as development fixtures
