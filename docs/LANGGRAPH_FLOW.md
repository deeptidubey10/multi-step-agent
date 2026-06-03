# LangGraph Workflow Diagram

## Agent Execution Flow

```mermaid
graph TD
    START([User Request]) --> PLANNER["<b>PLANNER NODE</b><br/>Decompose request<br/>into task steps"]
    
    PLANNER -->|Output: steps[]| EXECUTOR["<b>EXECUTOR NODE</b><br/>Execute current step<br/>current_step_index++"]
    
    EXECUTOR -->|Check step result| ROUTER{"<b>CONDITIONAL ROUTER</b><br/>Route after execution"}
    
    ROUTER -->|Step failed &<br/>replans < 3| ERROR["<b>ERROR HANDLER</b><br/>Fetch schema context<br/>replans++<br/>reset step index"]
    ERROR -->|Replan with<br/>error context| PLANNER
    
    ROUTER -->|Step is email_send| APPROVAL["<b>APPROVAL NODE</b><br/>Human review<br/>Email preview"]
    APPROVAL -->|Human approves| EXECUTOR
    
    ROUTER -->|More steps<br/>remain| EXECUTOR
    
    ROUTER -->|All steps done| AGGREGATOR["<b>AGGREGATOR NODE</b><br/>Compile results<br/>into final report"]
    
    AGGREGATOR --> END([Final Report])
    
    ROUTER -->|Step failed &<br/>replans >= 3| AGGREGATOR
    
    style START fill:#e1f5ff
    style PLANNER fill:#fff3e0
    style EXECUTOR fill:#f3e5f5
    style ERROR fill:#ffebee
    style APPROVAL fill:#e8f5e9
    style AGGREGATOR fill:#e0f2f1
    style END fill:#c8e6c9
    style ROUTER fill:#fffde7
```

---

## State Machine Diagram

```mermaid
stateDiagram-v2
    [*] --> Planner
    
    Planner: 🧠 Planning Phase
    Planner: - Analyze user request
    Planner: - Generate task plan
    Planner: - Output: steps[]
    
    Executor: ⚙️ Execution Phase
    Executor: - Get current step
    Executor: - Run tool
    Executor: - Increment index
    Executor: - Return result
    
    ErrorHandler: 🔧 Error Recovery
    ErrorHandler: - Fetch schema
    ErrorHandler: - Increment replans
    ErrorHandler: - Reset step index
    
    Approval: 👤 Human Gate
    Approval: - Show preview
    Approval: - Wait approval
    
    Aggregator: 📊 Compilation
    Aggregator: - Merge results
    Aggregator: - Generate report
    
    Done: ✅ Complete
    Done: - Return final output
    
    Planner --> Executor
    Executor --> ErrorCheck
    
    ErrorCheck: Check execution result
    ErrorCheck --> StepFailed: Failed & retries < 3
    ErrorCheck --> EmailStep: Tool == email_send
    ErrorCheck --> MoreSteps: More steps remain
    ErrorCheck --> AllDone: All steps done
    
    StepFailed --> ErrorHandler
    ErrorHandler --> Planner
    
    EmailStep --> Approval
    Approval --> Executor
    
    MoreSteps --> Executor
    AllDone --> Aggregator
    
    Aggregator --> Done
    
    [*] --> Planner
    Done --> [*]
```

---

## Step Execution Flow (Detailed)

```mermaid
graph LR
    A["step_id: 1<br/>tool: db_query<br/>parameters: {query}"] -->|execute| B["SQLTool.execute_query"]
    B -->|success| C["step_results.append<br/>success=True<br/>output=data"]
    B -->|error| D["step_results.append<br/>success=False<br/>error=msg"]
    
    C --> E["current_step_index++"]
    D --> E
    
    E --> F["State mutations<br/>accumulate via Annotated"]
    
    style A fill:#e3f2fd
    style B fill:#f3e5f5
    style C fill:#e8f5e9
    style D fill:#ffebee
    style F fill:#fff3e0
```

---

## State Schema (Pydantic Model)

```mermaid
graph TD
    AS["<b>AgentState</b><br/>─────────────"] 
    AS --> UR["user_request: str<br/>Original user prompt"]
    AS --> STEPS["steps: list<br/>Planned task steps"]
    AS --> CSI["current_step_index: int<br/>Which step to execute next"]
    AS --> SR["step_results: list (Annotated[+])<br/>All execution results<br/>(accumulates via operator.add)"]
    AS --> ERR["errors: list (Annotated[+])<br/>Error messages<br/>(accumulates)"]
    AS --> RC["replanning_count: int<br/>How many times replanned"]
    AS --> COMPLETE["is_complete: bool<br/>Task finished?"]
    AS --> OUTPUT["final_output: str<br/>Final report"]
    
    style AS fill:#fff9c4
    style SR fill:#ffecb3
    style ERR fill:#ffccbc
```

---

## Conditional Routing Logic

```mermaid
graph TD
    CHECK{"Last Step<br/>Succeeded?"}
    
    CHECK -->|NO| RETRY_CHECK{"Replans<br/>< 3?"}
    RETRY_CHECK -->|YES| ERROR_NODE["→ error_handler<br/>Get schema<br/>Replan"]
    RETRY_CHECK -->|NO| DONE_NODE["→ aggregator<br/>Give up"]
    
    CHECK -->|YES| EMAIL_CHECK{"Tool ==<br/>email_send?"}
    EMAIL_CHECK -->|YES| APPROVAL_NODE["→ approval<br/>Human review"]
    EMAIL_CHECK -->|NO| MORE_CHECK{"More steps<br/>remain?"}
    
    MORE_CHECK -->|YES| CONTINUE_NODE["→ executor<br/>Next step"]
    MORE_CHECK -->|NO| DONE_NODE
    
    ERROR_NODE -.->|Replan loop| PLANNER["planner_node"]
    APPROVAL_NODE -.->|Resume| EXECUTOR["executor_node"]
    CONTINUE_NODE -.->|Execute| EXECUTOR
    DONE_NODE -.->|Finalize| AGGREGATOR["aggregator_node"]
    
    style CHECK fill:#fff176
    style RETRY_CHECK fill:#fff176
    style EMAIL_CHECK fill:#fff176
    style MORE_CHECK fill:#fff176
```

---

## Example: Agent Processing the Demo Request

```mermaid
sequenceDiagram
    participant User
    participant Planner
    participant Executor
    participant SQLTool
    participant ErrorHandler
    participant Aggregator
    
    User->>Planner: "Find top 3 failing<br/>products in North Q3"
    Planner->>Planner: Analyze request
    Planner-->>Executor: Plan: [Step 1: Query sales,<br/>Step 2: Query logs,<br/>Step 3: Analyze,<br/>Step 4: Draft email]
    
    Executor->>SQLTool: Step 1: SELECT FROM sales<br/>WHERE region='North'<br/>AND quarter='Q3 2026'
    SQLTool-->>Executor: ✓ Returns 3 products
    
    Executor->>SQLTool: Step 2: SELECT FROM product_logs<br/>WHERE product_id IN (...)
    SQLTool-->>Executor: ✓ Returns log entries
    
    Executor->>Executor: Step 3: Python analysis<br/>Synthesize findings
    Executor-->>Executor: ✓ Summary ready
    
    Executor->>Executor: Step 4: Generate email
    Executor-->>ErrorHandler: Ready to send
    ErrorHandler-->>User: [APPROVAL] Review email?
    User-->>Executor: Approved
    
    Executor->>Aggregator: All steps complete
    Aggregator->>Aggregator: Compile final report
    Aggregator-->>User: 📊 Final Report:<br/>- Product H: -67%<br/>- Product G: -64%<br/>- Product F: -64%
```

---

## Key Concepts

| Concept | Purpose | Example |
|---------|---------|---------|
| **StateGraph** | Define nodes & edges | `graph = StateGraph(AgentState)` |
| **Nodes** | Processing steps | `planner_node()`, `executor_node()` |
| **Edges** | Deterministic transitions | `graph.add_edge("planner", "executor")` |
| **Conditional Edges** | Dynamic routing | `graph.add_conditional_edges("executor", router_fn, {...})` |
| **Annotated[list, add]** | Accumulating state | `step_results` appends, never replaces |
| **Checkpointing** | Resumable execution | Save state → resume later |
| **Interrupt** | Human-in-the-loop | Pause before `email_send` |

