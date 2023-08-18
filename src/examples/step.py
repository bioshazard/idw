# This was developed using llama-cpp-python.server as a fake OpenAI endpoint
# Highly recommended to do it that way so you don't have to wait for it to spin up

from dotenv import load_dotenv
load_dotenv()

from langchain.llms import OpenAI
llm = OpenAI(
    temperature=0,
    openai_api_key="use llama-cpp-python.server with hermes 13b!",
    max_tokens=512
)

from idw.alpaca.tools import useGoogleSearch, useFakeTool
tools = [
    useGoogleSearch(),
    useFakeTool(name="calculator", description="useful for calculation")
]

from idw.alpaca.agent import AlpacaStepAgent
agent = AlpacaStepAgent(llm=llm, tools=tools)
out = agent.query("How old is Brad Pitt's wife?")
print(out)
