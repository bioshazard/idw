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

class AlpacaInputStepAgent:
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools

    def query(self, query):
        self.notes = [
            # "Brad Pitt age is 59 as of June 2023",
            # "The square root of 59 is 7.68114"
        ]
        return self.step({ "query": query })
    
    def step(self, action):

        # # Init Step Chain, prompt is built dynamically from parts
        presponse=json.dumps({
            "question": action["query"],
            "observations": self.notes,
            "observationsSummary": "",
        }, indent=2)[:-3]
        prompt = prompts.inputInstruction.partial(response=presponse)
        chain = LLMChain(llm=self.llm, prompt=prompt, verbose=True)

        # # Instruction parts
        instructionParts = []

        # ## Tool list
        instructionParts.append("\n".join([
            "Answer the following questions as best you can. You have access to the following actions:",
            "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools]), 
        ]))

        toolNameList = "|".join([tool.name for tool in self.tools])
        instructionParts.append("\n".join([
            "Respond with only a JSON object as follows:",
            json.dumps({
                "question": "the input question you must answer",
                # "thought": "you should always think about what to do",
                # "thought": "<you should always think about what to do>",
                # "thought": "<WHAT DO THE 'Observations:' IMPLY ABOUT WHAT ACTION TO TAKE?>",
                "observationsSummary": "<summary of observations>",
                "answerKnown": "<DO I KNOW THE FINAL ANSWER YET?>",
                "breakdown": "<WHAT INFO PARTS DO I NEED TO ANSWER?>",
                "thought": "<what is the very next action based on the observations>",
                "action": f'the action to take, should be one of [{toolNameList}]',
                # "actionInput": "the input to the action",
                "actionInput": "<the string literal formatted input to the action>",
            }, indent=2)
        ]))

        # # Input Parts
        inputParts = []
        
        if "query" in action:
            inputParts.append(f'New question: {action["query"]}')
        
        ## Notes
        if len(self.notes) > 0:
            inputParts.append("\n".join([
                "Observations:",
                "\n".join([f"- {note}" for note in self.notes])
            ]))
        else:
            inputParts.append("Notes: None yet! Can't answer until I have notes!")

        # Compile prompt and submit for completion
        completion = presponse + chain.run({
            "instruction": "\n\n".join(instructionParts),
            "input": "\n\n".join(inputParts),
        })
        print(completion)
        llmOutput = json.loads(completion)

        if llmOutput["action"] == "submit":
            return llmOutput["actionInput"]
    
        # failsafe to just send the observation summary
        if llmOutput["answerKnown"] == "yes":
            return llmOutput["observationsSummary"]

        # Run next tool
        toolName = llmOutput["action"]
        toolInput = llmOutput["actionInput"]
        print("Run tool")
        toolOutput = self.runTool(toolName, toolInput)
        # print(toolOutput)
        actionObjectInput = {
            "thought": llmOutput["thought"],
            "action": llmOutput["action"],
            "actionInput": llmOutput["actionInput"],
        }

        # Separate observation processing chain (for now?)
        toolPrompt = prompts.inputInstruction.partial(response="")
        toolChain = LLMChain(llm=self.llm, prompt=toolPrompt, verbose=True)
        observation = toolChain.run({
            "instruction": "\n\n".join([
                # "Concisely summarize this context as an `actionOutput` field to add to the JSON object. Respond with an updated JSON object including the new field and value.",
                # "Respond with an updated JSON object to include a new field `actionOutput` as a laconic answer to the `actionInput` based on the context.",
                # "Respond with only a parsable updated JSON object to include a new field `observation` with the value of the action answer.",
                "Respond with only a valid JSON object updated to include a new field `observation` at the end with an extremely concise single string literal value based on the context.",
            ]),
            "input": "\n\n".join([
                "\n".join([
                    # "JSON Input Object:",
                    # "```",
                    json.dumps(actionObjectInput, indent=2),
                    # "```"
                ]),
                "\n".join([
                    "New Context:",
                    toolOutput
                ])
            ])
        })
        print(observation)
        toolOut = json.loads(observation)

        self.notes.append(": ".join([
            toolInput,
            toolOut["observation"]
        ]))
        return self.step(action)
    
    def runTool(self, toolName, inputText):
        tool = next((tool for tool in self.tools if tool.name == toolName), None)
        if not tool:
            raise Exception(f"'{toolName}' not a valid tool")
        return tool.func(inputText)

class AlpacaInputStepBreakdownAgent:
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools

    # def query(self, query):
    #     self.notes = [
    #         # "Brad Pitt age is 59 as of June 2023",
    #         # "The square root of 59 is 7.68114"
    #     ]
    #     return self.step({ "query": query })
    def query(self, query):
        # Break the question down
        self.query = query
        self.tasksPending = self.decompose(query)
        # self.tasksPending.append(query)
        self.tasksResolved = []
        # print(self.tasks)
        # Answer each sub-item with tools
        return self.resolve()

    def decompose(self, query):
        prompt = prompts.inputInstruction
        chain = LLMChain(llm=self.llm, prompt=prompt, verbose=True)

        format = json.dumps([
            "<an introductory task>",
            "<... zero or more additional tasks>",
        ], indent=2)

        instructionParts = []
        instructionParts.append("\n".join([
            # "of of" gives better results sometimes? lol
            "Decompose the question into a list of of tasks to research the answer.",
            "Respond only with a JSON object in this format:",
            format
        ]))

        # Input
        inputParts = []
        inputParts.append(f"New Question: {query}")
        # Completion
        presponse = format[0] # prime with first char
        completion = presponse + chain.run({
            "instruction": "\n\n".join(instructionParts),
            "input": "\n\n".join(inputParts),
            "response": presponse,
        })
        print(completion)
        return json.loads(completion)

    def resolve(self):
        prompt = prompts.inputInstruction
        chain = LLMChain(llm=self.llm, prompt=prompt, verbose=True)
        # Instruction
        instructionParts = []
        ## Tools
        if len(self.tasksPending) > 0:
            instructionParts.append("\n".join([
                " ".join([
                    "Resolve the unanswered tasks as best you can.",
                    "You have access to the following actions:"
                ]),
                "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools]), 
            ]))
        else:
            instructionParts.append("Answer the final question given the resolved task insights.")
        ## Response Format
        toolNameList = "|".join([tool.name for tool in self.tools])
        instructionParts.append("\n".join([
            "Respond with only a JSON object as follows:",
            json.dumps({
                "nextTask": "the next pending task you must resolve",
                "thought": "<I should always think about what to do next>",
                # "thought": "<what is the very next action based on the observations>",
                "action": f'the action to take, should be one of [{toolNameList}]',
                # "actionInput": "the input to the action",
                "actionInput": "<the string literal formatted input to the action>",
            }, indent=2)
        ]))
        # Input
        inputParts = []
        ## Tasks
            
        if len(self.tasksResolved) == 0:
            inputParts.append("Resolved Tasks: None")
        else:
            inputParts.append("\n".join([
                "Resolved Tasks:",
                "\n".join([f"- {task}" for task in self.tasksResolved])
            ]))
            
        if len(self.tasksPending) == 0:
            inputParts.append("Pending Tasks: None")
        else:
            inputParts.append("\n".join([
                "Pending Tasks:",
                "\n".join([f"- {task}" for task in self.tasksPending])
            ]))
            
        if len(self.tasksPending) > 0:
            inputParts.append(" ".join([
                "Next Task:",
                self.tasksPending[0]
            ]))
        
        # Add user question if no pending tasks
        if len(self.tasksPending) == 0:
            inputParts.append(f"Final Question: {self.query}")


        ## Scratchpad
        # TODO

        # Completion
        completion = chain.run({
            "instruction": "\n\n".join(instructionParts),
            "input": "\n\n".join(inputParts),
            "response": "",
        })
        print(completion)
        response = json.loads(completion)

        # Process tool selection
        # Run next tool
        toolThought = response["thought"]
        toolName = response["action"]
        toolInput = response["actionInput"]

        if toolName == "submit":
            # print(toolInput)
            return toolInput


        toolOutput = self.runTool(toolName, toolInput)
        # Process output as answer to latest task
        observation = chain.run({
            "instruction": "\n\n".join([
                # "Determine the answer to the task from the context.",
                "Determine the answer to the task from the tool output. Answer in as few words as possible to state just the fact.",
            ]),
            "input": "\n\n".join([
                f"Thought: {toolThought}",
                f"Tool: {toolName}",
                f"Input: {toolInput}",
                "\n".join([
                    "Output:",
                    "```",
                    toolOutput,
                    "```",
                ])
            ]),
            "response": ""
        })
        nextTask = self.tasksPending.pop(0)
        self.tasksResolved.append({
            "task": nextTask,
            "answer": observation
        })
        return self.resolve()


        # # print(toolOutput)
        # actionObjectInput = {
        #     "thought": llmOutput["thought"],
        #     "action": llmOutput["action"],
        #     "actionInput": llmOutput["actionInput"],
        # }

        # # Separate observation processing chain (for now?)
        # toolPrompt = prompts.inputInstruction.partial(response="")
        # toolChain = LLMChain(llm=self.llm, prompt=toolPrompt, verbose=True)
        # observation = toolChain.run({
        #     "instruction": "\n\n".join([
        #         # "Concisely summarize this context as an `actionOutput` field to add to the JSON object. Respond with an updated JSON object including the new field and value.",
        #         # "Respond with an updated JSON object to include a new field `actionOutput` as a laconic answer to the `actionInput` based on the context.",
        #         # "Respond with only a parsable updated JSON object to include a new field `observation` with the value of the action answer.",
        #         "Respond with only a valid JSON object updated to include a new field `observation` at the end with an extremely concise single string literal value based on the context.",
        #     ]),
        #     "input": "\n\n".join([
        #         "\n".join([
        #             # "JSON Input Object:",
        #             # "```",
        #             json.dumps(actionObjectInput, indent=2),
        #             # "```"
        #         ]),
        #         "\n".join([
        #             "New Context:",
        #             toolOutput
        #         ])
        #     ])
        # })
        # print(observation)
        # toolOut = json.loads(observation)

        # self.notes.append(": ".join([
        #     toolInput,
        #     toolOut["observation"]
        # ]))
        # return self.step(action)


    
    # we arent worried about decomposition here, done above
    def zeroshot(self, query):
        # Prep chain
        presponse=""
        promptJSON = prompts.inputInstruction.partial(response=presponse)
        chain = LLMChain(llm=self.llm, prompt=promptJSON, verbose=True)
        # Instruction
        instructionParts = []
        # Tools
        instructionParts.append("\n".join([
            " ".join([
                "Answer the following questions as best you can.",
                "You have access to the following actions:"
            ]),
            "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools]), 
        ]))
        ## Format
        toolList = [tool.name for tool in self.tools]
        instructionParts.append("\n".join([
            "Use the following format:",
            json.dumps({
                "question": "the input question you must answer",
                "questionDecomp": "comma separated list of all sub questions implied",
                "next": "which of the parts should I act on next?",
                "action": f'the action to take, should be one of [{"|".join(toolList)}]',
                "actionInput": "the input to the action"
            }, indent=2)
        ]))

        # Input
        inputParts = []
        inputParts.append(f"New Question: {action['query']}")
        # Completion
        completion = presponse + chain.run({
            "instruction": "\n\n".join(instructionParts),
            "input": "\n\n".join(inputParts)
        })
        print(completion)

        
        

    
    def step(self, action):
        # Prime response to start with curly brace. We want JSON outputs.
        # presponse="{"
        presponse=""
        promptJSON = prompts.inputInstruction.partial(response=presponse)
        chain = LLMChain(llm=self.llm, prompt=promptJSON, verbose=True)
        # Instruction
        instructionParts = []
        ## Tools
        instructionParts.append("\n".join([
            " ".join([
                "Answer the following questions as best you can.",
                "You have access to the following actions:"
            ]),
            "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools]), 
        ]))
        ## Format
        # toolList = [tool.name for tool in self.tools]
        # instructionParts.append("\n".join([
        #     "Use the following format:",
        #     json.dumps({
        #         "question": "the input question you must answer",
        #         "questionDecomp": "comma separated list of all sub questions implied",
        #         "next": "which of the parts should I act on next?",
        #         "action": f'the action to take, should be one of [{"|".join(toolList)}]',
        #         "actionInput": "the input to the action"
        #     }, indent=2)
        # ]))
        # DEBUG
        # instructionParts = []
        # instructionParts.append("\n".join([
        #     "Decompose the question into simpler questions.",
        #     "Respond only with a JSON object in this format:",
        #     json.dumps([
        #         "<An introductory question>",
        #         "<... include zero or more follow up questions as needed to be comprehensive>",
        #     ], indent=2)
        # ]))
        # DEBUG2
        instructionParts = []
        instructionParts.append("\n".join([
            # "of of" gives better results sometimes? lol
            "Decompose the question into a list of of tasks to research the answer.",
            "Respond only with a JSON object in this format:",
            json.dumps([
                "<an introductory task>",
                "<... zero or more additional tasks>",
            ], indent=2)
        ]))

        # Input
        inputParts = []
        inputParts.append(f"New Question: {action['query']}")
        # Completion
        completion = presponse + chain.run({
            "instruction": "\n\n".join(instructionParts),
            "input": "\n\n".join(inputParts)
        })
        print(completion)

    def step2(self, action):

        # # Init Step Chain, prompt is built dynamically from parts
        presponse=json.dumps({
            "question": action["query"],
            "observations": self.notes,
            "observationsSummary": "",
        }, indent=2)[:-3]
        prompt = prompts.inputInstruction.partial(response=presponse)
        chain = LLMChain(llm=self.llm, prompt=prompt, verbose=True)

        # # Instruction parts
        instructionParts = []

        # ## Tool list
        instructionParts.append("\n".join([
            "Answer the following questions as best you can. You have access to the following actions:",
            "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools]), 
        ]))

        toolNameList = "|".join([tool.name for tool in self.tools])
        instructionParts.append("\n".join([
            "Respond with only a JSON object as follows:",
            json.dumps({
                "question": "the input question you must answer",
                # "thought": "you should always think about what to do",
                # "thought": "<you should always think about what to do>",
                # "thought": "<WHAT DO THE 'Observations:' IMPLY ABOUT WHAT ACTION TO TAKE?>",
                "observationsSummary": "<summary of observations>",
                "answerKnown": "<DO I KNOW THE FINAL ANSWER YET?>",
                "breakdown": "<WHAT INFO PARTS DO I NEED TO ANSWER?>",
                "thought": "<what is the very next action based on the observations>",
                "action": f'the action to take, should be one of [{toolNameList}]',
                # "actionInput": "the input to the action",
                "actionInput": "<the string literal formatted input to the action>",
            }, indent=2)
        ]))

        # # Input Parts
        inputParts = []
        
        if "query" in action:
            inputParts.append(f'New question: {action["query"]}')
        
        ## Notes
        if len(self.notes) > 0:
            inputParts.append("\n".join([
                "Observations:",
                "\n".join([f"- {note}" for note in self.notes])
            ]))
        else:
            inputParts.append("Notes: None yet! Can't answer until I have notes!")

        # Compile prompt and submit for completion
        completion = presponse + chain.run({
            "instruction": "\n\n".join(instructionParts),
            "input": "\n\n".join(inputParts),
        })
        print(completion)
        llmOutput = json.loads(completion)

        if llmOutput["action"] == "submit":
            return llmOutput["actionInput"]
    
        # failsafe to just send the observation summary
        if llmOutput["answerKnown"] == "yes":
            return llmOutput["observationsSummary"]

        # Run next tool
        toolName = llmOutput["action"]
        toolInput = llmOutput["actionInput"]
        print("Run tool")
        toolOutput = self.runTool(toolName, toolInput)
        # print(toolOutput)
        actionObjectInput = {
            "thought": llmOutput["thought"],
            "action": llmOutput["action"],
            "actionInput": llmOutput["actionInput"],
        }

        # Separate observation processing chain (for now?)
        toolPrompt = prompts.inputInstruction.partial(response="")
        toolChain = LLMChain(llm=self.llm, prompt=toolPrompt, verbose=True)
        observation = toolChain.run({
            "instruction": "\n\n".join([
                # "Concisely summarize this context as an `actionOutput` field to add to the JSON object. Respond with an updated JSON object including the new field and value.",
                # "Respond with an updated JSON object to include a new field `actionOutput` as a laconic answer to the `actionInput` based on the context.",
                # "Respond with only a parsable updated JSON object to include a new field `observation` with the value of the action answer.",
                "Respond with only a valid JSON object updated to include a new field `observation` at the end with an extremely concise single string literal value based on the context.",
            ]),
            "input": "\n\n".join([
                "\n".join([
                    # "JSON Input Object:",
                    # "```",
                    json.dumps(actionObjectInput, indent=2),
                    # "```"
                ]),
                "\n".join([
                    "New Context:",
                    toolOutput
                ])
            ])
        })
        print(observation)
        toolOut = json.loads(observation)

        self.notes.append(": ".join([
            toolInput,
            toolOut["observation"]
        ]))
        return self.step(action)
    
    def runTool(self, toolName, inputText):
        tool = next((tool for tool in self.tools if tool.name == toolName), None)
        if not tool:
            raise Exception(f"'{toolName}' not a valid tool")
        return tool.func(inputText)
