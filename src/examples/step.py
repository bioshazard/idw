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
    useFakeTool(name="calculator", description="useful for calculation", output="7.68114"),
    useFakeTool(name="submit", description="once all tasks are resolved, submit the final answer", output=35)
]

from idw.alpaca.agent import AlpacaStepAgent, AlpacaInputStepAgent, AlpacaInputStepBreakdownAgent
agent = AlpacaInputStepBreakdownAgent(llm=llm, tools=tools)
# out = agent.query(input("> "))
# out = agent.query("What is the square root of brad pitt's age?")
out = agent.query("who is CEO of the company that tuned hermes 13b?")
# out = agent.query("what happened to project veritas after james left?")
# out = agent.query("Who was James O'Keefe and what was his role in Project Veritas?")
# out = agent.query("summarize project defuse")

print(out)


# template_with_history = """### Instruction:
# Answer the following questions as best you can. You have access to the following tools:

# {tools}

# Use the following format:

# Question: the input question you must answer
# Thought: you should always think about what to do
# Action: the action to take, should be one of [{tool_names}]
# Action Input: the input to the action
# Observation: the result of the action
# ... (this Thought/Action/Action Input/Observation can repeat N times)
# Thought: Finally I know the answer... here it is
# Final Answer: the final answer to the original input question

# ### Input:
# Previous conversation history:
# {history}

# New question: {input}
# {agent_scratchpad}

# ### Response:
# """