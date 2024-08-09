
import os
import re
from pandas import DataFrame
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
            # chat_history: list = [], 
            context: dict | None = None, 
            allow_llm_to_see_data: bool = False, 
            **kwargs
        ) -> str:
        """
        Generates a SQL query based on the given question, context, and chat history.

        Args:
            question (str): The question to generate a SQL query for.
            context (Context): The context containing related information for SQL generation.
            # chat_history (list): The chat history of the current conversation.
            allow_llm_to_see_data (bool, optional): Whether to allow the LLM to see data. Defaults to False.

        Returns:
            str: The generated SQL query.
        """
        if context is None:
            context = self.get_context(question, **kwargs)
            
        prompt = self.get_sql_prompt(
            initial_prompt=context.get("initial_prompt"),
            question=question,
            question_sql_list=context.get("question_sql_list", []),
            ddl_list=context.get("ddl_list", []),
            doc_list=context.get("doc_list", []),
            # chat_history=chat_history,
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
    
    def generate_followup_questions(self, question: str, sql: str, df: DataFrame | None=None, n_questions: int = 5, **kwargs) -> list:
        system_message = (
            f"You are a helpful data assistant. The user asked the question: '{question}'\n\n"
            f"The SQL query generated for this question was:\n{sql}\n\n"
        )
        if df is not None:
            system_message += (
                f"The following is a pandas DataFrame with the results of the query:\n"
                f"{df.to_markdown()}\n\n"
            )
        else:
            system_message += "However, this SQL query has not been executed yet.\n\n"

        message_log = [
            self.system_message(system_message),
            self.user_message(
                f"Generate a list of {n_questions} follow-up questions that the user might ask to explore this topic further or to refine the SQL query. "
                "Please follow these guidelines:\n"
                "1. Each question should be answerable with a SQL query.\n"
                "2. Focus on questions that modify or extend the original SQL query to dig deeper into the data.\n"
                "3. Avoid questions that require context from this conversation.\n"
                "4. Do not use 'example' type questions.\n"
                "5. Ensure each question has a one-to-one correspondence with a potential SQL query.\n"
                "6. Do not include any explanations, just list the questions.\n"
                "7. Each question will be presented as a clickable button to the user.\n\n"
                "Respond with a numbered list of questions, one per line." +
                self._response_language()
            ),
        ]

        llm_response = self.submit_prompt(message_log, **kwargs)
        numbers_removed = re.sub(r"^\d+\.\s*", "", llm_response, flags=re.MULTILINE)

        return [q for q in  numbers_removed.split("\n") if q.endswith('?')]

    def generate_chat_title(self, chat_history: list) -> str:
        messages = chat_history + \
            [{"role": "user", "content": "Given the following chat history, generate a brief, descriptive title for the conversation."}]
        return self.submit_prompt(prompt=messages, max_tokens=10, temperature=1, frequency_penatly=1)