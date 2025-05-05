# tool_executor.py


from typing import Callable, Any, List, Dict 
import inspect 
import logging 


logger = logging.getLogger(__name__)

class ToolExecutor:
    """

    Executes a collection of callable tools by name, handles dynamic arguent matching, and supports logging or augmentation for tracing execution.

    """

    def __init__(self, tools: List[Callable[..., Any]]):
        """
        Initialize the executor witha list of tool functions.

        Args:
            tools (List[Callable[...,Any]])


        """
        self.tools = {fn.__name__: fn for fn in tools}


    def has_tool(self, name: str) -> bool:
        """Check if a tool  with the given name is registered"""
        return name in self.tools

    def list_tools(self) -> List[str]:
        """Return a list of all available tool names"""

    def get_signature(self,name: str)-> Dict[str,inspect.Parameter]:
        """
        Return the signature of a registered tool. 

        Args:
            name(str): Name of the tool. 

        Returns:
            Dict[str, inspect.Parameter]: Parameter info for introspection or validation
        """

        if name not in self.tools:
            raise ValueError(f"Tool '{name}' is not registered")
        return inspect.signature(self.tools[name]).parameters 

    def execute(self, name: str, args: Dict[str, Any]) -> Any:
        """
        Call a tool by name with provided arguemnts 

        Args: 
            name(str): Name of the registered tool function. 
            args(Dict[str,Any]): Keyword arguments for the tool. 

        Returns: 
            Any: Result of the tool execution.
        """

        if name not in self.tools:
            raise ValueError(f"Tool '{name}' is not available")

        fn = self.tools[name]
        sig = inspect.signature(fn)

        accepted_args =  {
                k: v for k, v in args.items() if k in sig.parameters
        }

        try:
            logger.info(f"Executing tool: {name} with args: {accepted_args}")
            return fn(**accepted_args)

        except Exception as e:
            logger.exception(f"Error during execution of tool '{name}': {e}")
            raise
