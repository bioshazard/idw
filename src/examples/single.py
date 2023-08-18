# This test.py was developed using llama-cpp-python.server as a fake OpenAI endpoint
# Highly recommended to do it that way so you don't have to wait for it to spin up

from dotenv import load_dotenv
load_dotenv()

from langchain.llms import OpenAI
llm = OpenAI(
    temperature=0,
    openai_api_key="use llama-cpp-python.server with hermes 13b!",
    max_tokens=512
)

from idw.alpaca.agent import AlpacaSingleStepAgent, agentPromptsSingle, tools
agent = AlpacaSingleStepAgent(llm=llm, prompts=agentPromptsSingle, tools=tools)
out = agent.start("What is the capital of France?")
print(out)
