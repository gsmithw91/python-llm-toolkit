# chatbot.py

import json
import logging
import inspect
from typing import Any, Callable, List, Dict
from ollama import chat, ChatResponse
from tools import SCRAPING_TOOLS
from tool_executor import ToolExecutor

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
        self.executor = ToolExecutor(tools)
        self.messages: List[Dict[str, Any]] = []

    def send(self, user_input: str, progress_callback=None, output_dir='downloads') -> str | None:
        logging.info(f"[RECEIVED USER] {user_input}")
        self.messages.append({"role": "user", "content": user_input})

        try:
            response: ChatResponse = chat(
                model=self.model, messages=self.messages, tools=list(self.executor.tools.values())
            )

            if response.message.tool_calls:
                call = response.message.tool_calls[0]
                fn_name = call.function.name
                args = dict(call.function.arguments)

                if progress_callback:
                    param_str = ', '.join(f"{k}={v!r}" for k, v in args.items())
                    progress_callback(f"Calling tool: `{fn_name}({param_str})`")
                    logging.info(f"[TOOL CALL] {fn_name}({param_str})")

                if 'output_dir' in self.executor.get_signature(fn_name):
                    if 'output_dir' not in args or args['output_dir'] == 'downloads':
                        args['output_dir'] = output_dir

                result = self.executor.execute(fn_name, args)

                self.messages.append(response.message)  # assistant's tool call
                self.messages.append({
                    "role": "tool",
                    "name": fn_name,
                    "content": json.dumps(result)
                })

                response = chat(model=self.model, messages=self.messages, tools=list(self.executor.tools.values()))

            reply = response.message.content
            self.messages.append({"role": "assistant", "content": reply})
            logging.info(f"[BOT REPLY] {reply}")
            return reply

        except Exception as e:
            logging.exception(f"[ERROR] Exception in ChatBot.send: {e}")
            raise
if __name__ == "__main__":
    bot = ChatBot(model="webscraper", tools=SCRAPING_TOOLS)
    print("Chatbot ready! Type your questions (or 'quit' to exit).")
    while True:
        user_in = input("You: ")
        if user_in.strip().lower() == "quit":
            break
        bot_reply = bot.send(user_in)
        print("Bot:", bot_reply)
