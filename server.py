from vanna.vannadb import VannaDB_VectorStore
from sagemaker_llm import SageMakerLLM
from custom_vanna_flask import CustomVannaFlaskApp
from dotenv import load_dotenv
import os

load_dotenv()

llama_config = {
    "endpoint_name": "xifin-chat-llama3-8b-instruct-endpoint",
    "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
    "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
}

class MyVanna(VannaDB_VectorStore, SageMakerLLM):
    def __init__(self, config=None):
        MY_VANNA_MODEL = 'vanna_dev'
        VannaDB_VectorStore.__init__(
            self,
            vanna_model=MY_VANNA_MODEL, 
            vanna_api_key=os.getenv("VANNA_API_KEY"),  # type: ignore
            config=config
        )
        SageMakerLLM.__init__(self, config=llama_config)


vn = MyVanna()
vn.connect_to_sqlite("https://vanna.ai/Chinook.sqlite")

CustomVannaFlaskApp(
    vn=vn,
    logo="https://www.xifin.com/wp-content/themes/xifin/images/xifin-logo--color-blue-gradient.svg",
    title="XiQuery",
    subtitle="Turn natural language into SQL",
    allow_llm_to_see_data=True,
    index_html_path="index.html",
    assets_folder="assets",
    static_folder="static"
).run()
