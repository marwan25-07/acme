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
**Why is MCP useful in this context?**

MCP tools are callable functions that enable LLMs to complete actions through MCP servers like querying databases. MCPs define a standard, secure & repeatable way in completing actions, in the context of the Acme assistant, it enables the assitant to focus on understanding and completing requests rather than defining a new method at each runtime to coummunicate to its database.  

**How it seperates tool definitions from the core agent logic?**

MCPs define how tools are implemented to execute an objectibe, while agent logic focuses on how these tools are used together to complete a user  objective. 

## Memory (Redis):
Your documentation should explain your rationale for what you have stored in Redis versus PostgreSQL, and what trade-offs informed that decision

User conversation history is stored in Redis rather than held locally in application memory. This prevents conversation state from being lost if the application instance handling a request fails or is replaced. Although conversation history could also be stored in PostgreSQL to provide stronger durability, Redis was chosen for short-term session state because it provides faster read and write access, which helps reduce latency during interactions with the agent.

In the current implementation, Redis stores a maximum of 10 conversation turns per conversation ID, excluding the initial system message. Once this limit is reached, the oldest user-agent interaction is removed from the cache. This approach was chosen instead of applying a fixed time-to-live expiry to each conversation history entry because it gives users a more consistent experience during prolonged interactions. A user can continue a session without losing important recent context simply because a time limit has expired.

The decision not to store unlimited conversation history in Redis was based on performance and cost trade-offs. Redis is well suited to fast access of small, frequently used data, but storing large amounts of conversation history can increase memory usage and reduce retrieval efficiency. Limiting the cache to recent turns keeps the context relevant, controls memory usage, and reduces the number of input tokens passed to the agent.

Customer data is stored in PostgreSQL rather than Redis because it represents structured business data that should remain durable, consistent, and queryable. PostgreSQL is better suited for this type of long-term data storage because it supports reliable persistence, relational queries, and stronger consistency guarantees. Customer look-ups were not cached separately in the current implementation because any customer information already retrieved during a conversation is included in the cached conversation history. This allows the agent to refer back to recently discussed customer information without always needing to call a tool again, reducing unnecessary latency.

However, PostgreSQL remains the source of truth for customer data. This avoids the risk of relying on stale customer information from the cache when accurate or up-to-date data is required. Where freshness is important, the agent should query the database rather than rely only on previously cached context.

Tool calls and tool outputs were not cached in the current version due to time constraints. In a future version, caching tool outputs could reduce repeated calls and improve response speed. The trade-off is that cached tool outputs may become outdated, so cache invalidation rules, expiry policies, or freshness checks would need to be introduced. For example, outputs from tools that retrieve static or rarely changing data could be cached for longer, while outputs involving live customer status or open issues would require shorter expiry times or direct database look-ups.

Long term, if the volume of customer data increases, I would  redesign database tools to filter and retrieve only the required customer records rather than returning the entire dataset. This would reduce retrieval times and make the returned data easier for the agent to interpret, as well as reduce the number of input tokens consumed in the agent’s reasoning process.

## System Architecture:
<img width="auto" height="650" alt="image" src="https://github.com/user-attachments/assets/6dda9e62-3345-4bbc-91d8-db5ff2cc45ec" />

## Agent Architecture

The Acme assistant uses an agent-based architecture where the LLM is responsible for reasoning about the user's request and deciding which tools to invoke. Rather than hard-coding responses, the agent is provided with a set of available tools and uses these dynamically to retrieve customer information, inspect open issues, summarise issue history, and recommend next actions.

### Role-Aware Dynamic System Prompt

A key part of the architecture is the use of a dynamic system prompt. The system prompt is generated at runtime using information from the authenticated user's session, including their user role and permissions. When a user authenticates through Keycloak, their role is extracted from the access token and passed into the agent context. This role is then used to build a system prompt that is relevant to that user's responsibilities and access level. For example, a support user may receive instructions focused on issue investigation, issue notes, and recommended next actions, while an operations user may receive broader workflow guidance. This avoids giving every user the same generic prompt and helps keep the agent focused on the workflows that are relevant to the authenticated user.

### Permission-Based Tool Access

The tools exposed to the agent are also dependent on the user's role and permissions. Tools are not simply made available to every user at runtime. Instead, the application checks the authenticated user's permissions and only enables the tools that the user is allowed to access. For example, a user with read-only permissions may be allowed to retrieve customer profiles and view open issues, but they may not be given access to tools that create issue notes or update next actions. This means restricted tools are not exposed to the agent during that run, reducing the risk of the agent attempting actions the user is not authorised to perform.This provides an additional layer of security because access control is enforced before the agent runs, rather than relying only on prompt instructions.

## Evaluation and Observability
The evaluation framework uses two complementary approaches: **LLM-as-Evaluator** and **Technical Evaluation**. Together, these assess both the quality of ACME’s final response and the correctness of the agent’s underlying behaviour. A previous eval file run was added to provide an example of the tests implemented [here](https://github.com/marwan25-07/acme/blob/main/evals/evaluations/eval_results.jsonl).

#### 1. LLM-as-Evaluator

The LLM-as-Evaluator assesses the quality and reliability of ACME’s response for each test case. It evaluates:

- **Response quality**: whether ACME’s response fully answers the test question.
- **Grounding**: whether the response is supported by the tool outputs or database results available to the agent.

The evaluator returns a structured judgement, including a response quality score, a grounding result, and explanatory reasoning for the judgement.

Response quality is scored as follows:

| Label | Score | Description |
|---|---:|---|
| `complete` | 3 | The response fully answers the test question with no important missing information. |
| `partial` | 1 | The response answers part of the question, but misses important details or is too vague. |
| `incomplete` | 0 | The response does not answer the question, is irrelevant, or fails to provide useful help. |

Grounding is scored as a boolean:

| Field | Value | Description |
|---|---|---|
| `grounded_in_tool_outputs` | `true` | The response is supported by the tool outputs or database results. |
| `grounded_in_tool_outputs` | `false` | The response contains unsupported, invented, or contradictory information. |

#### 2. Technical Evaluation

The technical evaluation uses trace data generated during each agent run to assess whether the agent behaved correctly at the system level. It evaluates:

- **Tool selection**: whether the agent called the expected tool or tools for the test query.
- **RBAC compliance**: whether the agent respected role-based access control by only calling tools available to the user’s role.

Technical checks are scored as pass/fail booleans:

| Check | Pass condition |
|---|---|
| Tool selection | All expected tools were called, with no unauthorised or unexpected tool usage depending on the strictness of the test. |
| RBAC compliance | The agent only called tools permitted for the user’s role. |

#### Overall Scoring

Each evaluation case produces both component-level scores and an overall result.

The overall score is calculated from four components:

| Component | Max Score |
|---|---:|
| RBAC compliance passed | 1 |
| Response grounded in tool outputs | 1 |
| Response quality | 3 |
| **Total** | **5** |

### Tradeoffs Made
Due to time constraints, the technical evaluation currently relies on locally stored trace files to inspect agent behaviour, including tool calls and RBAC compliance.

In a production setting, traces would not normally be read directly from local storage. A more scalable approach would be to persist the relevant evaluation artefacts, such as tool calls, tool outputs, and trace metadata, in a cache or lightweight datastore with a time-to-live expiry. This would make retrieval more efficient, reduce reliance on local files, and avoid retaining evaluation data longer than necessary.

This approach was chosen as a pragmatic tradeoff to complete the technical evaluation within the available time while still providing reliable visibility into the agent’s execution path.

## Run Evaluation 

Evaluation can be run with:

```bash
py -m evals/run_evals
```

## AI Usage Note

AI tools were used during the development of this prototype to support debugging and repetitive implementation tasks. For example, AI assistance was used to help apply the logging framework I had already designed across the customer tools file and to troubleshoot implementation issues during development.

The core architecture, design principles, security approach, and technical trade-offs were designed by me. AI-generated suggestions or code were reviewed, adapted where necessary, and tested before being included in the final project.

