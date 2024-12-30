# OVOS Common Query Framework

The **OVOS Common Query Framework** is designed to answer questions by gathering answers from several skills and selecting the best one

## Features

- **Utterance Query Type Detection**: 🧐:  
  If the user utterance does not resemble a question (e.g., no "who", "what", "when" keywords), the system will avoid attempting to answer.
  
- **Skill Availability Check** 🔧:  
  If no common query skills are installed, the system will refrain from attempting to respond, ensuring queries are issued only when appropriate skills are available.

- **Improved Answer Selection** 🤖:  
  A reranker plugin can be integrated to evaluate multiple skill responses and select the most relevant one, ensuring higher-quality answers.

- **Bad Answer Discarding** 🚮:  
  By integrating a reranker with a minimum score threshold (`min_score`), poor or irrelevant answers are discarded, improving the overall accuracy of responses.

- **Timeout for Late Answers** ⏱️:  
  The system will stop waiting for answers after 2 seconds. Any response received after this time will be ignored, ensuring an upper time limit for query handling.

## Configuration


### Reranker (Optional)
Rerankers, also referred to as **MultipleChoiceSolvers**, are optional and need to be explicitly installed. These are used to rank and select the most relevant response from multiple common query skills (e.g., Wolfram Alpha, Wikipedia).

Below is an example configuration to set up a reranker:

```json
"intents": {
    "common_query": {
      "reranker": "ovos-flashrank-reranker-plugin",
      "ovos-flashrank-reranker-plugin": {
        "model": "ms-marco-TinyBERT-L-2-v2"
      }
    }
}
```

### Notes:
- **Reranker Plugin**: A reranker plugin is optional. You need to install it explicitly for the framework to use it.
- **Model Choice**: The example uses the `ovos-flashrank-reranker-plugin` with `ms-marco-TinyBERT-L-2-v2` model, but other plugins/models can be specified depending on your use case and performance requirements.
- **Performance Consideration**: Enabling reranking, particularly on devices with limited resources (e.g., Raspberry Pi), may introduce additional latency (up to 1 second).

## Performance Impact

Be mindful of the performance tradeoffs when enabling rerankers:
- On resource-constrained devices, such as the Raspberry Pi, reranking models may add extra latency.  
- Adjust the settings to match the device’s capabilities and the expected response time.
