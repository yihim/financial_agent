# MoneyLion Assessment Report - LLM Engineer

## To Use the System
1. Ensure you have [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed on your machine.
2. Open the **financial_agent** folder
3. Create a `.env` file with `OPENAI_API_KEY=your_openai_api_key`
4. Open PowerShell (Windows), change the directory to the **financial_agent** folder
5. Execute `docker-compose --build -d` command and wait until all the installations finish
6. Visit [http://localhost:8090](http://localhost:8090) to begin

## Example Use Cases of Using the System
1. Client with single bank and account
   1. Enter `30` as the Client ID
   2. Click `Continue` button
   3. Directed to chat interface
   4. Begin chat

2. Client with multiple banks and accounts
   1. Enter `880` as the Client ID
   2. Click `Continue` button
   3. Enter `274` as the Bank ID
   4. Enter `310` as the Account ID
   5. Directed to chat interface
   6. Begin chat

---

## Time Spent on Creating the System: ~43-55 hours

---

### Drafting Solution: 4-6 hours
```ini
1. Clean the data.csv:
	- Sort based on client_id
	- Format the data type
	- Separate amount to debit and credit
	- Handle missing values for text columns
	- Normalize text columns (lower-cased and removed extra spacing)
	- Normalize column names
2. Convert the cleaned data into a SQLite database
3. Use openai-4o-mini as the main LLM
4. Create multi-agents architecture:
	- Query analyzer
	- Query rewriter
	- Task planner
	- SQL query generator
	- SQL query validator (tool)
	- Response crafter
5. Use langchain and langgraph as the framework
6. Use FastAPI to create the APIs
7. Use Streamit to create a simple user interface
8. Containerize the solution using Docker
```

Initially, I considered using Retrieval-Augmented-Generation (RAG) to index the cleaned data and retrieve it as context for the LLM to respond to queries. However, after thorough consideration, I determined this approach was unsuitable due to the numerous operations required, such as counting, calculating, and referencing different columns—tasks RAG does not excel at. Therefore, using SQL queries to retrieve results from a database proved more reliable.

Creating a reliable solution by relying on a single LLM for all tasks can lead to hallucinations or unexpected results, particularly when the prompt becomes lengthy to accommodate multiple scenarios. For example:

1. Analyzing and classifying queries to respond appropriately (ambiguous, sensitive, general, or valid transactional)
2. Rewriting queries to be context-independent and standalone (for follow-up questions)
3. Generating effective SQL queries from rewritten prompts (considering simple or complex cases) to obtain relevant context from the database
4. Using database results to craft responses that align with rewritten queries

To address these challenges, I implemented a multi-agent architecture that distributes these responsibilities across specialized components. This approach eases the burden on any single LLM, dividing tasks into manageable parts with each agent handling specific responsibilities, resulting in a more robust and maintainable solution.

For this implementation, I created six different agents using LangChain and LangGraph as the framework:

1. **Query analyzer**: Determines if the query is ambiguous, relates to data sensitivity concerns, or represents general conversation. If so, it passes to a dedicated agent for response; otherwise, it forwards to the query rewriter.
2. **Query rewriter**: Transforms the query to be more explicit or creates a standalone, context-independent query for follow-up questions.
3. **Task planner**: Breaks down simple or complex rewritten queries into structured sub-tasks for the SQL query generator to process effectively.
4. **SQL query generator**: Creates a one-line executable SQL query based on the sub-tasks.
5. **SQL query validator (tool)**: Executes the generated SQL query to retrieve results from the SQLite database.
6. **Response crafter**: Formulates a response based on the database results that aligns with the rewritten query.

The final solution is containerized using Docker Compose with services for 'db', 'agents', and 'app'. Each service utilizes FastAPI for integration, with a simple user interface created using Streamlit.

---

### Clean and Convert Data to SQLite Database: 3-4 hours
While exploring the data.csv file, I identified several issues:

1. Multiple client IDs exist, many with multiple bank IDs and account IDs
2. The data lacked proper sorting
3. The 'amt' column contained both negative and positive values
4. The 'txn_date' column wasn't properly formatted as `datetime64[ns]`
5. The 'merchant' column contained null values
6. Text columns weren't normalized and sometimes included extra spacing
7. Column names used abbreviated forms

To address these issues, I implemented the following cleaning procedures:

1. **Sorted the data** based on 'clnt_id', then 'bank_id', and finally 'acc_id'
   - This facilitates easier result evaluation during testing.
2. **Separated the 'amt' column** into 'debit' (negative values) and 'credit' (positive values), with 0 values set to null
   - This simplifies calculations for the agent.
3. **Converted 'txn_date'** to `datetime64[ns]` format
   - This enables more efficient time-based filtering in SQL queries.
4. **Filled null values** in the 'merchant' column with "unknown"
   - This eliminates complications when filtering null values in SQL queries.
5. **Created a normalization function** to convert text to lowercase and remove extra spacing across all text columns
   - This streamlines keyword filtering from user queries.
6. **Renamed abbreviated columns** to more descriptive names
   - This helps agents better understand which columns to reference.

These modifications resulted in a curated dataset saved as `data_curated.csv` and a SQLite database named `transactions.db` with a table called `transactions`.

---

### Create and Test Functions for Database: 6-8 hours
I developed the following key functions:

1. **connect_db**
   - Establishes a connection to the SQLite database
2. **get_table_schema**
   - Retrieves the `transactions` table schema and provides descriptions for each column to pass to agents
3. **execute_sql_query**
   - Serves as a tool for executing agent-generated SQL queries, obtaining results from the database, and returning them in a formatted structure
4. **get_client_with_single_bank_and_account_id**
   - Verifies whether a validated client has multiple banks and/or accounts
   - Guides the user interface integration flow: clients with one bank and account proceed directly to the chat interface, while those with multiple banks/accounts are prompted to provide additional bank and account IDs
5. **validify_client_bank_account_ids**
   - Validates either the client ID alone or all IDs (client, bank, and account) against the database

---

### Prompt Engineering and Test Each Agent Responses: 16-20 hours
I created and refined the following agents:

1. **Query Analyzer**
   - Engineered the system prompt to handle different query types (`ambiguous`, `sensitive`, `general` & `valid_transactional`) and manage follow-up queries with structured output (rewritten query and reasoning)
   - Used agent reasoning to further refine the prompt engineering

2. **Query Rewriter**
   - Developed a system prompt that transforms `valid_transactional` queries into explicit, context-independent formats—crucial for the task planner to effectively break these down into structured sub-tasks
   - Incorporated agent reasoning feedback to continuously improve the prompt

3. **Task Planner**
   - Created a system prompt that decomposes rewritten queries into structured sub-tasks, facilitating more effective SQL query generation compared to passing rewritten queries directly (which sometimes produced non-executable or inaccurate SQL)
   - Included comprehensive examples in the prompt, covering various use cases and operation types
   - Configured the agent to produce structured outputs (`query_understanding`, `execution_plan`, and `expected_output_structure`) that assist the SQL query generator

4. **SQL Query Generator**
   - Developed a system prompt that leverages task planner responses along with defined instructions and use case examples to generate effective, one-line executable SQL queries

5. **SQL Query Validator (tool)**
   - Implemented a tool that executes SQL queries generated by the SQL query generator and returns formatted results from the database

6. **Response Crafter**
   - Engineered a system prompt that produces clear, structured responses in Markdown format based on database results and rewritten queries

<div align="center">
  <h4>Graph Visualization</h4>
  <img src="https://raw.githubusercontent.com/yihim/financial_agent/main/assets/graph_visualization.png" alt="Graph Structure" width="15%" />
</div>

---

### APIs Creation and Test: 5-6 hours
I developed the following API endpoints:

API for **agents**:
1. `/api/chat` - POST (stream)
   - Streams agent/graph responses to the user interface
   - Stores log files (chat session information) in the `logs` folder (in the root directory) with the naming convention `{thread_id}-{client_id}-{bank_id}-{account_id}.json`. These files contain critical debugging information including `user_query`, `bot_response`, `time_taken`, `graph_state_info`, and `openai_info`.

APIs for **db**:
1. `/api/client/{client_id}/bank-account` - GET
   - Implements the `get_client_with_single_bank_and_account_id` function
2. `/api/validify/client-bank-account` - POST
   - Implements the `validify_client_bank_account_ids` function
3. `/api/db/execute-query` - POST
   - Implements the `execute_sql_query` function

---

### User Interface and Test: 5-6 hours
I designed a user interface with the following workflow:

1. **Client ID validation**
    - User enters Client ID
    - User clicks the `Continue` button
    - System validates the entered ID
    - If validation fails, an error message displays
    - If validation succeeds, the system checks whether the client has multiple banks and/or accounts
    - Clients with a single bank and account proceed directly to step 3
    - Clients with multiple banks and/or accounts continue to step 2

2. **Bank ID and Account ID validation**
    - User enters Bank ID and Account ID
    - User clicks the `Continue` button
    - System validates the entered IDs
    - If validation fails, an error message displays
    - If validation succeeds, the system proceeds to step 3

3. **Chat Interface**
    - User submits queries
    - Agent streams responses

This user interface eliminates the need for manually executing code to interact with the financial agent, providing a streamlined experience.

---

### Containerization: 4-5 hours
I used Docker for containerization to eliminate the need for installing multiple packages and resolving dependency issues. This approach provides a simpler, more direct way to deliver the solution while ensuring compatibility across different operating systems.

---