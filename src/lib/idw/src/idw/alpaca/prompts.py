# Alpaca Format Shells
# NOTE: {response} will usually be empty, can be useful as a primer

from langchain.prompts import PromptTemplate

instruction = PromptTemplate(
    input_variables=["instruction", "response"],
    template="\n".join([
        "### Instruction:", "{instruction}",
        "### Response:", "{response}"
    ])
)

inputInstruction = PromptTemplate(
    input_variables=["instruction", "input", "response"],
    template="\n".join([
        "### Instruction:", "{instruction}",
        "### Input:", "{input}",
        "### Response:", "{response}"
    ])
)

def responseFormatJson(responseObj):
    import json
    return "\n".join([ "```", "{" + json.dumps(responseObj, indent=2) + "}", "```", ])