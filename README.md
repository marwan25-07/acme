# Acme

# Local Setup

This project is designed to run entirely locally using Docker Compose. The local environment includes the main FastAPI application, PostgreSQL database, Redis service, and Keycloak authentication server.

## 1. Clone the repository
```bash
git clone <repository-url>
cd <repository-name>
```
## 2. Create your environment file

An `.env.example` file is included in the project. This file provides a template for the sensitive environment variables required to run the application, such as Database credentials, Redis connection details, Keycloak settings, and any LLM provider API keys.


## 3. Start the local services

Run the following command from the project root:
```bash
docker compose up --build
```

This starts the required local services:
- PostgreSQL for structured customer, issue, and action data
- Redis for short-term session state or memory
- FastAPI for the application API and agent endpoint
- Keycloak for local authentication and user management
  
## 4. Configure Keycloak

After the containers are running, open the Keycloak admin console in your browser.

The project includes an acme realm for the application. Each developer must create their own user credentials within the acme realm before using the assistant.

At minimum, create a local test user with:

* First Name: < your-first-name >
* Last Name: < your-last-name >
* Username: < your-test-username >
* Password: < your-test-password >
* Role: <admin | support_user | sales_user>
* Realm: acme

These credentials are used to authenticate against Keycloak and obtain an access token for calling the protected FastAPI endpoints.

# Design of Application

## MCP:
Why is MCP useful in this context?
MCP tools are callable functions that enable LLMs to complete actions through MCP servers like querying databases. MCPs define a standard, secure & repeatable way in completing actions, in the context of the Acme assistant, it enables the assitant to focus on understanding and completing requests rather than defining a new method at each runtime to coummunicate to a databse.  

how it seperates tool definitions from the core agent logic?
MCPs define how tools are implemented to execute an objectibe, while agent logic focuses on how these tools are used together to complete a user  objective. 

## Memory (Redis):
Your documentation should explain your rationale for what you have stored in Redis versus PostgreSQL, and what trade-offs informed that decision.

User conversation history is stored within a redis cache rather than locally during run-time to prevent it from being lost if an instance handling the request was to fail. Alternatively, user conversation history can also be stored within a database to ensure it is not lost in a scenario where the instance fails. However, since conversation history is a persistent data during run-time session, storing in cache enables faster data retrieval than storing in a database, which overall helps in reducing latency. The current set up of the cache in this project stores at a maximum of 10 conversation turns (excluding initial system message) per conversation id. Once this threshold is reach the oldest user-agent interaction is deleted from the cache. I chose this method over than a setting tts expiry for each conversation_history as the method is more reliable for users interacting with an agnet over a prolonged period of time. The reason I did not enable for conversations to remain in cache is due to performance, storing huge data in cache can result in a depreciation in retrieval times from the cache. 

customer look-ups did not need to be cached as customer data presented to the user in their interactions were stored within conversation history, which was cached and therefore the agent could use past conversations to answer questions to the user without needing to call a tool again. This workflow would ultimately help in reducing latency. I did not cache tool calls due to a lack of time, however I would also cache which tools where called and their respective output, I would then pass this over to the agent as context during run time to enable the agent to use this to as context to answer requests rather than running unneccesary tool calls. 

Long-term if the amount of customer data was large, I would consider scheduling a daily flow which caches customers with issues that are currently open and creating tools that focus on filtering data out of the database rather than retrieving the entire database. The former approach helps with reducing retrieval times on data that is most likely to be requested from the user, the latter approach helps with ensuring data output is small enough to be interpretable by the angent and it will help in reducing the amount of input tokens required by the agent to process the data it is being provided. 

## Agent Structure:
Tool availability 

## Evaluation and Observability

The solution includes a small evaluation set under `evals/evaluation_set.jsonl`. The evaluation framework comprises of two evaluation methods: LLM-as-Evaluator and Technical evaluation.
LLM-as-Evaluator approach: Utilises an LLM to evalutate the completeness of acme's response to the test user question.
Technical Evaluation: Utlises traces to evaluate tool calls and whether the agent calls the correct tools to complete the response. 

LLM-as-Evaluator
- Assesses completeness of response

Technical Evaluation
- Assess whether correct tool calls were called
- Whether RBAC was respected by not using tools that exceeds user permissions. 

Evaluation can be run with:

```bash
python evals/run_evals.py


