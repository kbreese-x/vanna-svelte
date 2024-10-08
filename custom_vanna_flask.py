from vanna.base import VannaBase
from vanna.flask import Cache, MemoryCache, VannaFlaskAPI
from vanna.flask.auth import AuthInterface, NoAuth
import os
from abc import ABC, abstractmethod
from functools import wraps

import flask
import requests
from flasgger import Swagger
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_sock import Sock

from sagemaker_llm import SageMakerLLM

#TODO: overload routes: load_question
class CustomVannaFlaskApp(VannaFlaskAPI):
    def __init__(
        self,
        vn: SageMakerLLM,
        cache: Cache = MemoryCache(),
        auth: AuthInterface = NoAuth(),
        debug=True,
        allow_llm_to_see_data=False,
        allow_llm_to_run_sql=False,
        logo="https://www.xifin.com/wp-content/themes/xifin/images/xifin-logo--color-blue-gradient.svg",
        title="Welcome to Vanna.AI",
        subtitle="Your AI-powered copilot for SQL queries.",
        show_training_data=True,
        suggested_questions=True,
        sql=True,
        table=False,
        csv_download=False,
        chart=False,
        redraw_chart=True,
        auto_fix_sql=True,
        ask_results_correct=True,
        followup_questions=True,
        summarization=False,
        function_generation=True,
        index_html_path=None,
        assets_folder=None,
        static_folder=None,
    ):
        """
        Expose a Flask app that can be used to interact with a Vanna instance.

        Args:
            vn: The Vanna instance to interact with.
            cache: The cache to use. Defaults to MemoryCache, which uses an in-memory cache. You can also pass in a custom cache that implements the Cache interface.
            auth: The authentication method to use. Defaults to NoAuth, which doesn't require authentication. You can also pass in a custom authentication method that implements the AuthInterface interface.
            debug: Show the debug console. Defaults to True.
            allow_llm_to_see_data: Whether to allow the LLM to see data. Defaults to False.
            #
            logo: The logo to display in the UI. Defaults to the Vanna logo.
            title: The title to display in the UI. Defaults to "Welcome to Vanna.AI".
            subtitle: The subtitle to display in the UI. Defaults to "Your AI-powered copilot for SQL queries.".
            #
            show_training_data: Whether to show the training data in the UI. Defaults to True.
            suggested_questions: Whether to show suggested questions in the UI. Defaults to True.
            sql: Whether to show the SQL input in the UI. Defaults to True.
            table: Whether to show the table output in the UI. Defaults to True.
            csv_download: Whether to allow downloading the table output as a CSV file. Defaults to True.
            chart: Whether to show the chart output in the UI. Defaults to True.
            redraw_chart: Whether to allow redrawing the chart. Defaults to True.
            auto_fix_sql: Whether to allow auto-fixing SQL errors. Defaults to True.
            ask_results_correct: Whether to ask the user if the results are correct. Defaults to True.
            followup_questions: Whether to show followup questions. Defaults to True.
            summarization: Whether to show summarization. Defaults to True.
            index_html_path: Path to the index.html. Defaults to None, which will use the default index.html
            assets_folder: The location where you'd like to serve the static assets from. Defaults to None, which will use hardcoded Python variables.

        Returns:
            None
        """
        super().__init__(vn, cache, auth, debug, allow_llm_to_see_data, chart)

        self.flask_app.view_functions['generate_sql'] = self.requires_auth(self.generate_sql_with_context)
        self.flask_app.view_functions['run_sql'] = self.requires_auth(self.requires_cache(["sql"])(self.run_sql_if_allowed))
        self.flask_app.view_functions['load_question'] = self.requires_auth(self.requires_cache(["question","sql"], optional_fields=["df", "summary", "fig_json", "followup_questions"])(self.load_question))

        # Control the behavior by passing it to config and using config to control svelte client
        # Also override the run_sql route and prevent it from running if allow_llm_to_run_sql is False
        self.allow_llm_to_run_sql = allow_llm_to_run_sql

        self.config["allow_run_sql"] = allow_llm_to_run_sql
        self.config["logo"] = logo
        self.config["title"] = title
        self.config["subtitle"] = subtitle
        self.config["show_training_data"] = show_training_data
        self.config["suggested_questions"] = suggested_questions
        self.config["sql"] = sql
        self.config["table"] = table
        self.config["csv_download"] = csv_download
        self.config["chart"] = chart
        self.config["redraw_chart"] = redraw_chart
        self.config["auto_fix_sql"] = auto_fix_sql
        self.config["ask_results_correct"] = ask_results_correct
        self.config["followup_questions"] = followup_questions
        self.config["summarization"] = summarization
        self.config["function_generation"] = function_generation


        self.index_html_path = index_html_path
        self.assets_folder = assets_folder
        self.static_folder = static_folder
        
        if static_folder:
            self.flask_app.static_folder = static_folder

        @self.flask_app.route("/auth/login", methods=["POST"])
        def login():
            return self.auth.login_handler(flask.request)

        @self.flask_app.route("/auth/callback", methods=["GET"])
        def callback():
            return self.auth.callback_handler(flask.request)

        @self.flask_app.route("/auth/logout", methods=["GET"])
        def logout():
            return self.auth.logout_handler(flask.request)
        
        @self.flask_app.route('/', defaults={'path': ''})
        @self.flask_app.route('/<path:path>')
        def serve(path):
            static_folder_path = os.path.abspath(self.static_folder)
            if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
                return send_from_directory(static_folder_path, path)
            else:
                return send_from_directory(static_folder_path, 'index.html')

        @self.flask_app.route("/api/v0/get_context", methods=["POST"])
        @self.requires_auth
        def get_context(user: any):
            data = request.json
            question = data.get('question')

            context = self.vn.get_context(question)

            return jsonify({
                "type": "context",
                "context": context
            })

        # Proxy the /vanna.svg file to the remote server
        @self.flask_app.route("/vanna.svg")
        def proxy_vanna_svg():
            remote_url = "https://www.xifin.com/favicon.svg"
            response = requests.get(remote_url, stream=True)

            # Check if the request to the remote URL was successful
            if response.status_code == 200:
                excluded_headers = [
                    "content-encoding",
                    "content-length",
                    "transfer-encoding",
                    "connection",
                ]
                headers = [
                    (name, value)
                    for (name, value) in response.raw.headers.items()
                    if name.lower() not in excluded_headers
                ]
                return Response(response.content, response.status_code, headers)
            else:
                return "Error fetching file from remote server", response.status_code
            
        @self.flask_app.route("/api/v0/generate_followup_questions_no_df", methods=["GET"])
        @self.requires_auth
        @self.requires_cache(["question", "sql"])
        def generate_followup_questions_no_df(user: any, id: str, question, sql):
            followup_questions = vn.generate_followup_questions(
                question=question, sql=sql
            )
            if followup_questions is not None and len(followup_questions) > 5:
                followup_questions = followup_questions[:5]

            self.cache.set(id=id, field="followup_questions", value=followup_questions)

            return jsonify(
                {
                    "type": "question_list",
                    "id": id,
                    "questions": followup_questions,
                    "header": "Here are some potential followup questions:",
                }
            )

    # @self.flask_app.route("/api/v0/generate_sql", methods=["GET"])
    def generate_sql_with_context(self, user: any):
        """
        Generate SQL from a question
        ---
        parameters:
            - name: user
            in: query
            - name: question
            in: query
            type: string
            required: true
        responses:
            200:
            schema:
                type: object
                properties:
                type:
                    type: string
                    default: sql
                id:
                    type: string
                text:
                    type: string
        """
        question = flask.request.args.get("question")
        print("THE GENERATE SQL ROUTE IS DEFINITELY BEING OVERRIDDEN")
        if question is None:
            return jsonify({"type": "error", "error": "No question provided"})

        id = self.cache.generate_id(question=question)
        sql = self.vn.generate_sql(question=question, allow_llm_to_see_data=self.allow_llm_to_see_data)
        self.cache.set(id=id, field="question", value=question)
        self.cache.set(id=id, field="sql", value=sql)
        # self.cache.set(id=id, field="context", value=context)

        if self.vn.is_sql_valid(sql=sql):
            return jsonify(
                {
                    "type": "sql",
                    "id": id,
                    "text": sql,
                }
            )
        else:
            return jsonify(
                {
                    "type": "text",
                    "id": id,
                    "text": sql,
                }
            )
    

    # @self.flask_app.route("/api/v0/run_sql", methods=["GET"])
    def run_sql_if_allowed(self, user: any, id: str, sql: str):
        # If we allow server to not write sql
        print('IS ALLOWED TO RUN SQL: ', self.allow_llm_to_run_sql)
        if not self.allow_llm_to_run_sql:
            print("GOT HERE")
            return jsonify({"type": "error", "error": "LLM is not allowed to run SQL queries."})
        
        # We will use this later if we are trying to allow read/write to SQL
        try:
            if not self.vn.run_sql_is_set:
                return jsonify(
                    {
                        "type": "error",
                        "error": "Please connect to a database using vn.connect_to_... in order to run SQL queries.",
                    }
                )

            df = self.vn.run_sql(sql=sql)

            self.cache.set(id=id, field="df", value=df)

            return jsonify(
                {
                    "type": "df",
                    "id": id,
                    "df": df.head(10).to_json(orient='records', date_format='iso'),
                    "should_generate_chart": self.chart and self.vn.should_generate_chart(df),
                }
            )
        except Exception as e:
            return jsonify({"type": "sql_error", "error": str(e)})
        
    def load_question(self, user: any, id: str, question, sql, df, fig_json, summary, followup_questions):
        try:
            print(type(df))
            print(df)
            return jsonify(
                {
                    "type": "question_cache",
                    "id": id,
                    "question": question,
                    "sql": sql,
                    "df": df.head(10).to_json(orient="records", date_format="iso") if df is not None else df,
                    "fig": fig_json,
                    "followup_questions": followup_questions,
                    "summary": summary,
                }
            )
        except Exception as e:
            return jsonify({"type": "error", "error": str(e)})