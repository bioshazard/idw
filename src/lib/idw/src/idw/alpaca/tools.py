from langchain.agents import Tool

def useGoogleSearch(name="search", description="useful for when you need to answer questions about current events"):
    from langchain.utilities import GoogleSearchAPIWrapper
    search = GoogleSearchAPIWrapper()
    return Tool(
      name=name,
      description=description,
      func=search.run,
    )

def useFakeTool(name="faketool", description="useful to fake a new tool", output="test"):
    def fakeout(str):
        return output
    return Tool(
        name=name,
        description=description,
        func=fakeout,
    )
