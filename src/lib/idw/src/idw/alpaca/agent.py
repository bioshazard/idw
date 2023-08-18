from langchain.prompts import PromptTemplate

from . import prompts
from .tools import useGoogleSearch, useFakeTool

def responseFormatJson(responseObj):
    import json
    return "\n".join([ "```", "{" + json.dumps(responseObj, indent=2) + "}", "```", ])

# Tools
# TODO: re-org... should be in test.py
tools = [
    useGoogleSearch()
]

# Agent Prompts
promptAgentIngest = PromptTemplate(
    input_variables=["query"],
    template=prompts.instruction.format(
        instruction="\n\n".join([
            "User Query: {query}",
            "Answer the above user query and provide supporting context if applicable.",
            "You have access to the following tools:",
            # move out of template?? ^^ (per above note)
            "\n".join([f"- {tool.name}: {tool.description}" for tool in tools]), 
            "First, decide which of the above named tools to use and what input to provide the tool.",
            "Respond with only a JSON object as follows:",
            prompts.responseFormatJson({
                "thought": "<WHAT DOES THE QUERY IMPLY ABOUT THE TOOL YOU SHOULD PICK>",
                "tool": "<ONLY THE NAME OF THE CHOSEN TOOL FROM THE LIST OR 'None'>",
                "input": "<FORMATTED INPUT TO THE TOOL>"
            })
        ]),
        response="",
    )
)

promptAgentSynthesize = PromptTemplate(
    input_variables=["query", "context"],
    template=prompts.instruction.format(
        instruction="\n\n".join([
            "User Query: {query}",
            "Available context:",
            "\n".join(["```", "{context}", "```", ]),
            "Answer the user query given only the supporting context. If the available context is insufficient, say so.",
            "Response with only a JSON object as follows:",
            prompts.responseFormatJson({
                "thought": "<WHAT DOES THE SUPPORTING IMPLY ABOUT THE ANSWER TO THE USER QUERY>",
                "answer": "<FINAL ANSWER BASED ON SUPPORTING CONTEXT>",
            })
        ]),
        response="",
    )
)

agentPromptsSingle = {
    "ingest": promptAgentIngest,
    "synthesize": promptAgentSynthesize,
}

import json
from langchain import LLMChain
class AlpacaSingleStepAgent:
    
    def __init__(self, llm, prompts, tools):
        self.llm = llm
        self.prompts = prompts
        self.tools = tools
    
    def start(self, query):
        self.query = query # cheating to make accessible in action recurse
        return self.action({ "query": query })
    
    # Prompt Router
    def action(self, action):
        
        if "answer" in action:
            return action["answer"]
        
        if "query" in action:
            # Form and execute chain
            prompt=self.prompts["ingest"]
            chain = LLMChain(llm=self.llm, prompt=prompt, verbose=True)
            result = chain.run(action)
            print(result)
            # Parse resulting JSON
            llmOutput = json.loads(result)
            return self.action(llmOutput)
        
        if "tool" in action:
            toolName = action["tool"]
            inputText = action["input"]
            # Execute tool (TODO: router tool vs completion)
            toolOutput = self.runTool(toolName, inputText)
            print(toolOutput)
            # Synthesize
            prompt=self.prompts["synthesize"]
            chain = LLMChain(llm=self.llm, prompt=prompt, verbose=True)
            action["context"] = toolOutput
            action["query"] = self.query # TODO: unhack
            result = chain.run(action)
            llmOutput = json.loads(result)
            # print(llmOutput)
            return self.action(llmOutput)
    
    def runTool(self, toolName, inputText):
        tool = next((tool for tool in tools if tool.name == toolName), None)
        if not tool:
            raise Exception(f"'{toolName}' not a valid tool")
        return tool.func(inputText)

# Iteration 2: steps legos

"""
step types
- LLM: user input -> tool run
- Tool: tool run -> final answer synthesis, tool run (2) w/ scratchpad
- LLM: final answer sythesis
process output
- choose next template by name
- fill in variables (may be simpler to always replace root level "input" from shell prompts?)
"""

"""
eg, input -> search -> answer


"""


# promptAgentSynthesize = PromptTemplate(
#     input_variables=["query", "context"],
#     template=prompts.instruction.format(
#         instruction="\n\n".join([
#             "User Query: {query}",
#             "Available context:",
#             "\n".join(["```", "{context}", "```", ]),
#             "Answer the user query given only the supporting context. If the available context is insufficient, say so.",
#             "Response with only a JSON object as follows:",
#             prompts.responseFormatJson({
#                 "thought": "<WHAT DOES THE SUPPORTING IMPLY ABOUT THE ANSWER TO THE USER QUERY>",
#                 "answer": "<FINAL ANSWER BASED ON SUPPORTING CONTEXT>",
#             })
#         ]),
#         response="",
#     )
# )


class AlpacaStepAgent:
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools

    def query(self, query):
        self.notes = []
        # self.facts = ["Brad Pitt is 70"]
        return self.step({ "query": query })
    
    def step(self, action):

        # Init Step Chain, prompt is built dynamically from parts
        instructionBlankResponse = prompts.instruction.partial(response="")
        chain = LLMChain(llm=self.llm, prompt=instructionBlankResponse, verbose=True)

        # Prompt parts
        promptParts = []

        promptParts.append("Have a conversation with a human, answering the following questions as best you can.")

        # if "toolResponse" in action:
        #     promptParts.append("\n".join([
        #         "Latest Tool Output:",
        #         json.dumps(action["toolResponse"], indent=2)
        #     ]))
        
        # Tool list
        promptParts.append("\n".join([
            "You have access to the following tools:",
            "\n".join([f"- {tool.name}: {tool.description}" for tool in tools]), 
        ]))
        
        ## Notes
        if len(self.notes) > 0:
            promptParts.append("\n".join([
                "Notes:",
                "\n".join([f"- {note}" for note in self.notes])
            ]))
        else:
            promptParts.append("Notes: None yet! Can't answer until I have notes!")

        # # Final Response Instruction
        # promptParts.append("\n".join([
        #     "If the answer is in the notes, respond with only a JSON object as follows:",
        #     json.dumps({
        #         "thought": "<WHAT DO THE NOTES IMPLY ABOUT THE ANSWER TO THE USER QUERY>",
        #         "answer": "<FINAL ANSWER BASED ON SUPPORTING CONTEXT>",
        #     }, indent=2)
        # ]))

        # # Tool Response Instruction
        # promptParts.append("\n".join([
        #     "If the user query can be answered from the 'Notes:' above, answer the query.",
        #     "If the user query CAN NOT be answered from the 'Notes:' above, decide which of the above named tools to use next and what input to provide the tool. Respond with only a JSON object as follows:",
        #     json.dumps({
        #         "thought": "<WHAT DOES THE QUERY IMPLY ABOUT THE TOOL YOU SHOULD PICK>",
        #         "tool": "<ONLY THE NAME OF THE CHOSEN TOOL FROM THE LIST OR 'None'>",
        #         "input": "<FORMATTED INPUT TO THE TOOL>"
        #     }, indent=2)
        # ]))

        # Tool Response Instruction
        # promptParts.append("\n".join([
        #     "Respond with only a JSON object as follows:",
        #     json.dumps({
        #         "solvedByNotes": "<'TRUE' or 'FALSE'>",
        #         "guess": "<BEST GUESS FINAL ANSWER AT THIS TIME>",
        #         "thought": "<WHAT SHOULD I DO NEXT GIVEN THE 'Notes:' AND 'Tools:'?>",
        #         # "nextStep": "<'TOOL' or 'ANSWER'>",
        #         # "known": "<DOES THE ABOVE THOUGHT FIELD PROVIDE AN ANSWER?>",
        #         "tool": "<ONLY THE NAME OF THE CHOSEN TOOL FROM THE LIST>",
        #         "input": "<FORMATTED INPUT TO THE TOOL>",
        #         # "answer": "<THE ANSWER FROM 'Notes:' IF AVAILABLE>",
        #     }, indent=2)
        # ]))
        
        if "query" in action:
            promptParts.append(f'User Query: {action["query"]}')

        promptParts.append("\n".join([
            "Respond with only a JSON object as follows:",
            json.dumps({
                "thought": "<'TRUE' or 'FALSE'>",
                "guess": "<BEST GUESS FINAL ANSWER AT THIS TIME>",
                "thought": "<WHAT SHOULD I DO NEXT GIVEN THE 'Notes:' AND 'Tools:'?>",
                # "nextStep": "<'TOOL' or 'ANSWER'>",
                # "known": "<DOES THE ABOVE THOUGHT FIELD PROVIDE AN ANSWER?>",
                "tool": "<ONLY THE NAME OF THE CHOSEN TOOL FROM THE LIST>",
                "input": "<FORMATTED INPUT TO THE TOOL>",
                # "answer": "<THE ANSWER FROM 'Notes:' IF AVAILABLE>",
            }, indent=2)
        ]))

        # Compile prompt and submit for completion
        prompt = "\n\n".join(promptParts)
        completion = chain.run(prompt)
        print(completion)
        llmOutput = json.loads(completion)

        if llmOutput['solvedByNotes'] == 'TRUE':
            print("GUESS:", llmOutput['guess'])
            return llmOutput['guess']

        # Run next tool?
        if "tool" in llmOutput:
            toolName = llmOutput["tool"]
            toolInput = llmOutput["input"]
            print("Run Tool")
            toolOutput = self.runTool(toolName, toolInput)
            print(toolOutput)
            toolResponse = {
                "tool": toolName,
                "input": toolInput,
                "output": toolOutput
            }
            observation = chain.run("\n\n".join([
                f"User Query: {action['query']}",
                "\n".join([
                    "Tool Output:",
                    "```",
                    json.dumps(toolResponse, indent=2),
                    "```"
                ]),
                "What note should be taken from the tool output to help answer the user query?",
                "DO NOT INFER BEYOND THE DIRECT INTENT OF THE TOOL INPUT/OUTPUT."
            ]))
            print(observation)

            self.notes.append(observation)
            return self.step(action)
        
        return 'ERROR'
        # return llmOutput
    
    def runTool(self, toolName, inputText):
        tool = next((tool for tool in tools if tool.name == toolName), None)
        if not tool:
            raise Exception(f"'{toolName}' not a valid tool")
        return tool.func(inputText)
        