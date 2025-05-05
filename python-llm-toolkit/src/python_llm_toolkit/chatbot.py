# chatbot.py

import json
import logging
import inspect
from typing import Any, Callable, List, Dict
from ollama import chat, ChatResponse
from tools import TOOLS

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Tool names that require an output directory
TOOLS_NEED_OUTPUT_DIR = {"download_file", "download_files_by_type", "scrape", "focused_scrape_files_by_terms"}

class ChatBot:
    def __init__(self, model: str, tools: List[Callable[..., Any]]):
        self.model = model
        self.tools = tools
        self.messages: List[Dict[str, Any]] = []

    def send(self, user_input: str, progress_callback=None, output_dir='downloads') -> str:
        logging.info(f"[RECEIVED USER] {user_input}")
        self.messages.append({"role": "user", "content": user_input})

        try:
            response: ChatResponse = chat(
                model=self.model,
                messages=self.messages,
                tools=self.tools
            )

            if response.message.tool_calls:
                call = response.message.tool_calls[0]
                fn_name = call.function.name
                try:
                    args = json.loads(call.function.arguments)
                except Exception as e:
                    logging.error(f"Failed to parse arguments for tool {fn_name}: {e}")
                    args = {}

                py_fn = next((fn for fn in self.tools if fn.__name__ == fn_name), None)
                if not py_fn:
                    raise ValueError(f"Tool function '{fn_name}' not found.")

                sig = inspect.signature(py_fn).parameters
                kwargs = {}

                if 'progress_callback' in sig:
                    if progress_callback:
                        def wrapped_callback(msg):
                            progress_callback(f"[{fn_name}] {msg}")
                        kwargs['progress_callback'] = wrapped_callback

                if 'output_dir' in sig and fn_name in TOOLS_NEED_OUTPUT_DIR:
                    if 'output_dir' not in args or args['output_dir'] in ('downloads', '/path/to/downloads'):
                        args['output_dir'] = output_dir
                        if progress_callback:
                            progress_callback(f"Using output directory: {output_dir}")

                if progress_callback:
                    param_str = ', '.join(f"{k}={v!r}" for k, v in args.items())
                    progress_callback(f"Calling tool: `{fn_name}({param_str})`")

                logging.info(f"[TOOL CALL] {fn_name}({args})")
                result = py_fn(**args, **kwargs)
                logging.info(f"[TOOL RESULT] {fn_name}: {result}")

                self.messages.append(response.message)
                self.messages.append({
                    "role": "tool",
                    "name": fn_name,
                    "content": json.dumps(result)
                })

                response = chat(model=self.model, messages=self.messages, tools=self.tools)

            reply = response.message.content
            self.messages.append({"role": "assistant", "content": reply})
            logging.info(f"[BOT REPLY] {reply}")
            return reply

        except Exception as e:
            logging.exception(f"[ERROR] Exception in ChatBot.send: {e}")
            return f"Error: {str(e)}"

if __name__ == "__main__":
    bot = ChatBot(model="webscraper", tools=TOOLS)
    print("Chatbot ready! Type your questions (or 'quit' to exit).")
    while True:
        user_in = input("You: ")
        if user_in.strip().lower() == "quit":
            break
        bot_reply = bot.send(user_in)
        print("Bot:", bot_reply)

