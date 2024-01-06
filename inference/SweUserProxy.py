from autogen.agentchat.contrib.math_user_proxy_agent import MathUserProxyAgent
from autogen import UserProxyAgent
from autogen.math_utils import get_answer
import autogen
from typing import Any, Dict, List, Optional, Union, Tuple
from openai import (
    BadRequestError,
)
from functools import partial


class SweUserProxy(UserProxyAgent):
    DEFAULT_REPLY = "Continue. Please keep solving the problem. Once you have arrived at a final answer, please respond with your answer and the phrase \"TERMINATE: The patch is shown above\" at the end of your message. This will signal the end of our conversation."
    PROMPTS = """You will be provided with a partial code base and an issue statement explaining a problem to resolve. You should resolve the problem utilizing the functions you konw for the user to execute. Please note that only the functions you know can be used. 
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses functions, and which step is your own reasoning. Once you have arrived at a final answer, please respond with your answer and the phrase “TERMINATE: The patch is shown above” at the end of your message. This will signal the end of our conversation.
"""
#     PROMPTS = """You are a helpful AI assistant. You will be provided with a partial code base and an issue statement explaining a problem to resolve. 
# Solve tasks using 1. functions you know 2. your coding skills and 3. your language skills. 
# Under the condition that the functions you know can not help you resolve the problem, you should consider solving the problem using python. 
# In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
#     1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
#     2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
# Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses functions you know, which step uses your coding skills and which step uses your language skill.
# When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
# If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
# If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
# When you find one answer, verify the answer carefully. Include verifiable evidence in your response if possible.
# Once you have arrived at a final answer, please respond with your answer in the form of string and the phrase “TERMINATE: The patch is shown above” at the end of your message. This will signal the end of our conversation. 
# You must prepare the final answer with the required format. <patch> your answer </patch>
# """
    def __init__(
            self,
            name: Optional[str] = "MathChatAgent",
            human_input_mode: Optional[str] = "NEVER",
            default_auto_reply: Optional[Union[str, Dict, None]] = DEFAULT_REPLY,
            **kwargs,
    ):
        super().__init__(
            name=name,
            human_input_mode=human_input_mode,
            default_auto_reply=default_auto_reply,
            is_termination_msg=partial(SweUserProxy.is_termination_msg_swebench, self),
            **kwargs,
        )

        # check the order
        # del self._reply_func_list[0]
        # self.register_reply(trigger=autogen.ConversableAgent,
        #                     reply_func=SweUserProxy.is_termination_msg_swebench, position=0)
        del self._reply_func_list[3]
        self.register_reply(trigger=autogen.ConversableAgent,
                            reply_func=MathUserProxyAgent.generate_function_call_reply, position=3)
        
        del self._reply_func_list[4]
        
        self.max_function_call_trial = 3
        
        self.answer = None

    def is_termination_msg_swebench(self, message):
        """Check if a message is a termination message."""
        if isinstance(message, dict):
            message = message.get("content")
            if message is None:
                return False
        if message.rstrip().find("TERMINATE") >= 0:
            print(self.answer)
            self.answer = message
            return True
        
        # if get_answer(message) is not None and get_answer(message) != "":
        #     self.answer = get_answer(message)
        #     return True

    def generate_function_call_reply(
            self,
            messages: Optional[List[Dict]] = None,
            sender: Optional[autogen.ConversableAgent] = None,
            config: Optional[Any] = None,
    ) -> Tuple[bool, Union[Dict, None]]:
        """Generate a reply using function call."""
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        if "function_call" in message:
            is_exec_success, func_return = self.execute_function(
                message["function_call"])
            if is_exec_success:
                self.max_function_call_trial = 3
                return True, func_return
            else:
                if self.max_function_call_trial == 0:
                    error_message = func_return["content"]
                    # self.logs["is_correct"] = 0
                    self.max_function_call_trial = 3
                    return True, "The func is executed failed many times. " + error_message + ". Please directly reply me with TERMINATE. We need to terminate the conversation."
                else:
                    revise_prompt = "You may make a wrong function call (It may due the arguments you provided doesn't fit the function arguments like missing required positional argument). \
                    If you think this error occurs due to you make a wrong function arguments input and you could make it success, please try to call this function again using the correct arguments. \
                    Otherwise, the error may be caused by the function itself. Please directly reply me with TERMINATE. We need to terminate the conversation. "
                    error_message = func_return["content"]
                    return True, "The func is executed failed." + error_message + revise_prompt
        return False, None

    def initiate_chat(
            self,
            recipient,
            query: None,
            silent: Optional[bool] = False,
            **context,
    ):
        self._prepare_chat(recipient, True)
        chat_history = []
        error_message = None
        try:
            prompt = self.PROMPTS + query
            self.send(prompt, recipient, silent=silent)
        except BadRequestError as e:
            error_message = str(e)
            # self.logs["is_correct"] = 0
            print("error information: {}".format(error_message))

        key = list(self.chat_messages.keys())[0]
        chat_messages = self.chat_messages[key]
        for item in chat_messages:
            chat_history.append(item)
        if error_message is not None:
            chat_history.append(error_message)
        recipient.reset()
        # logs_return = copy.deepcopy(self.logs)
        print("--------final_answer--------")
        answer = self.answer
        self._reset()
        print(answer)
        return answer, chat_history
    
    def _reset(self):
        self.answer = None
        self.max_function_call_trial = 3