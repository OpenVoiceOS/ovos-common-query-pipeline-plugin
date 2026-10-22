# OVOS Common Query Framework

The OVOS Common Query Framework answers questions. It gathers answers from several skills and picks the best one.

Common Query is only as fast as the slowest CommonQuerySkill. Latency depends on which skills you install.

## Features

- **Utterance query type detection**: If the user utterance does not resemble a question (for example, it has no "who", "what", or "when"), the system does not try to answer.
- **Skill availability check**: If no common query skills are installed, the system does not try to respond. It issues queries only when a matching skill is available.
- **Answer selection**: A reranker plugin can evaluate multiple skill responses and select the most relevant one.
- **Bad answer discarding**: A reranker with a minimum score threshold (`min_score`) discards poor or irrelevant answers.
- **Timeout for late answers**: The system stops waiting for answers after 2 seconds. It ignores any response that arrives after this time.

## Install

This plugin ships with [ovos-core](https://github.com/OpenVoiceOS/ovos-core) by default. You do not need to install it explicitly.

```bash
pip install ovos-common-query-pipeline-plugin
```

## Configuration

### Reranker (optional)

Rerankers, also called MultipleChoiceSolvers, are optional. Install one explicitly to rank and select the most relevant response from multiple common query skills (for example, Wolfram Alpha or Wikipedia).

This example configures a reranker:

```json
"intents": {
    "common_query": {
        "min_self_confidence": 0.5,
        "min_reranker_score": 0.5,
        "reranker": "ovos-flashrank-reranker-plugin",
        "ovos-flashrank-reranker-plugin": {
          "model": "ms-marco-TinyBERT-L-2-v2"
        }
    }
}
```

Notes:
- A reranker plugin is optional. Install it explicitly for the framework to use it.
- The example uses [ovos-flashrank-reranker-plugin](https://github.com/OpenVoiceOS/ovos-flashrank-reranker-plugin) with the `ms-marco-TinyBERT-L-2-v2` model. Other plugins and models work too, depending on your use case and performance needs.
- Reranking may add latency on resource-constrained devices, such as a Raspberry Pi. Adjust the settings to match the device capabilities and the expected response time.

## Related projects

- [OpenVoiceOS/ovos-core](https://github.com/OpenVoiceOS/ovos-core) — the assistant this plugin ships with
- [OpenVoiceOS/ovos-plugin-manager](https://github.com/OpenVoiceOS/ovos-plugin-manager) — loads this plugin as an `opm.pipeline` entry point
- [OpenVoiceOS/ovos-flashrank-reranker-plugin](https://github.com/OpenVoiceOS/ovos-flashrank-reranker-plugin) — example reranker plugin

## License

Apache-2.0
