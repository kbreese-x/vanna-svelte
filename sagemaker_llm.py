
import os
from transformers import AutoTokenizer
from vanna.base import VannaBase
import boto3
import json

class SageMakerLLM(VannaBase):
    def __init__(self, config=None):
        super().__init__(config)
        print(config)
        if config is None:
            raise ValueError("Config must be provided for SageMakerLLM(VannaBase):")
        
        self.endpoint_name = config.get('endpoint_name')
        if not self.endpoint_name:
            raise ValueError("endpoint_name must be provided in the config")
        
        self.region_name = config.get('region_name', 'us-west-2')
        self.model = config.get('model', 'meta-llama/Meta-Llama-3-8B-Instruct')
        self.temperature = config.get('temperature', 0.6)
        self.max_tokens = config.get('max_tokens', 2048)
        self.stop = config.get('stop', ['<|eot_id|>'])
        self.aws_access_key_id = config.get('aws_access_key_id')
        self.aws_secret_access_key = config.get('aws_secret_access_key')
        
        self.smr = boto3.client(
            'sagemaker-runtime', 
            region_name=self.region_name,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        )
        self.tokenizer = AutoTokenizer.from_pretrained(self.model)

    def system_message(self, message: str) -> dict:
        return {"role": "system", "content": message}

    def user_message(self, message: str) -> dict:
        return {"role": "user", "content": message}

    def assistant_message(self, message: str) -> dict:
        return {"role": "assistant", "content": message}

    def str_to_approx_token_count(self, string: str) -> int:
        return len(self.tokenizer.encode(string))

    def submit_prompt(self, prompt, **kwargs) -> str:
        # Define default values
        default_params = {
            'messages': prompt,
            'model': self.model,
            'stop': self.stop,
            'stream': False,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
        }

        # Update default values with explicitly defined kwargs
        for key in ['model', 'stop', 'stream', 'temperature', 'max_tokens']:
            if key in kwargs:
                default_params[key] = kwargs.pop(key)

        # Merge the remaining kwargs
        payload = {**default_params, **kwargs}
        
        response = self.smr.invoke_endpoint(
            EndpointName=self.endpoint_name,
            ContentType='application/json',
            Body=json.dumps(payload),
            CustomAttributes='accept_eula=true'
        )
        
        data = json.loads(response['Body'].read().decode('utf-8'))
        content = data['choices'][0]['message']['content']
        
        return content

    def get_context(self, question: str, **kwargs):
        """
        Retrieves the context needed for generating SQL.
    
        Args:
            question (str): The question to generate a SQL query for.
    
        Returns:
            Context: A Context object containing the retrieved context.
        """
        if self.config is not None:
            initial_prompt = self.config.get("initial_prompt", None)
        else:
            initial_prompt = None
    
        question_sql_list = self.get_similar_question_sql(question, **kwargs)
        ddl_list = self.get_related_ddl(question, **kwargs)
        doc_list = self.get_related_documentation(question, **kwargs)
    
        return {
            "initial_prompt": initial_prompt,
            "question_sql_list": question_sql_list,
            "ddl_list": ddl_list,
            "doc_list": doc_list
        }
 
    def generate_sql(
            self, 
            question: str, 
            chat_history: list = [], 
            context: dict | None = None, 
            allow_llm_to_see_data: bool = False, 
            **kwargs
        ) -> str:
        """
        Generates a SQL query based on the given question, context, and chat history.

        Args:
            question (str): The question to generate a SQL query for.
            context (Context): The context containing related information for SQL generation.
            chat_history (list): The chat history of the current conversation.
            allow_llm_to_see_data (bool, optional): Whether to allow the LLM to see data. Defaults to False.

        Returns:
            str: The generated SQL query.
        """
        if context is None:
            context = self.get_context(question, **kwargs)
        
        prompt = self.get_sql_prompt(
            initial_prompt=context.get("initial_prompt"),
            question_sql_list=context.get("question_sql_list", []),
            ddl_list=context.get("ddl_list", []),
            doc_list=context.get("doc_list", []),
            chat_history=chat_history,
            **kwargs,
        )
        self.log(title="SQL Prompt", message=prompt)
        llm_response = self.submit_prompt(prompt, **kwargs)
        self.log(title="LLM Response", message=llm_response)


        if 'intermediate_sql' in llm_response:
            if not allow_llm_to_see_data:
                return "The LLM is not allowed to see the data in your database. Your question requires database introspection to generate the necessary SQL. Please set allow_llm_to_see_data=True to enable this."

            if allow_llm_to_see_data:
                intermediate_sql = self.extract_sql(llm_response)

                try:
                    self.log(title="Running Intermediate SQL", message=intermediate_sql)
                    df = self.run_sql(intermediate_sql)

                    prompt = self.get_sql_prompt(
                        initial_prompt=context.get("initial_prompt"),
                        question_sql_list=context.get("question_sql_list", []),
                        ddl_list=context.get("ddl_list", []),
                        doc_list=context.get("doc_list", []) + [f"The following is a pandas DataFrame with the results of the intermediate SQL query {intermediate_sql}: \n" + df.to_markdown()],
                        **kwargs,
                    )
                    self.log(title="Final SQL Prompt", message=prompt) # type: ignore
                    llm_response = self.submit_prompt(prompt, **kwargs)
                    self.log(title="LLM Response", message=llm_response)
                except Exception as e:
                    return f"Error running intermediate SQL: {e}"

        return self.extract_sql(llm_response)
    
    def get_sql_prompt(
        self,
        initial_prompt: str | None,
        question_sql_list: list,
        ddl_list: list,
        doc_list: list,
        chat_history: list,
        **kwargs,
    ):
        if initial_prompt is None:
            initial_prompt = f"You are a {self.dialect} expert. " + \
            "Please help to generate a SQL query to answer the question. Your response should ONLY be based on the given context and follow the response guidelines and format instructions. "

        initial_prompt = self.add_ddl_to_prompt(
            initial_prompt, ddl_list, max_tokens=self.max_tokens
        )

        if self.static_documentation != "":
            doc_list.append(self.static_documentation)

        initial_prompt = self.add_documentation_to_prompt(
            initial_prompt, doc_list, max_tokens=self.max_tokens
        )

        initial_prompt += (
            "===Response Guidelines \n"
            "1. If the provided context is sufficient, please generate a valid SQL query without any explanations for the question. \n"
            "2. If the provided context is almost sufficient but requires knowledge of a specific string in a particular column, please generate an intermediate SQL query to find the distinct strings in that column. Prepend the query with a comment saying intermediate_sql \n"
            "3. If the provided context is insufficient, please explain why it can't be generated. \n"
            "4. Please use the most relevant table(s). \n"
            "5. If the question has been asked and answered before, please repeat the answer exactly as it was given before. \n"
            f"6. Ensure that the output SQL is {self.dialect}-compliant and executable, and free of syntax errors. \n"
        )

        message_log = [self.system_message(initial_prompt)]

        for example in question_sql_list:
            if example is None:
                print("example is None")
            else:
                if example is not None and "question" in example and "sql" in example:
                    message_log.append(self.user_message(example["question"]))
                    message_log.append(self.assistant_message(example["sql"]))

        for message in chat_history:
            if message["role"] == "user":
                message_log.append(self.user_message(message["content"]))
            elif message["role"] == "assistant":
                message_log.append(self.assistant_message(message["content"]))

        return message_log

    def generate_chat_title(self, chat_history: list) -> str:
        messages = chat_history + \
            [{"role": "user", "content": "Given the following chat history, generate a brief, descriptive title for the conversation."}]
        return self.submit_prompt(prompt=messages, max_tokens=10, temperature=1, frequency_penatly=1)