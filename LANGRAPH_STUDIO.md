# LangGraph Studio Setup

This project is configured to work with [LangGraph Studio](https://studio.langchain.com/) for visualization and debugging.

## Setup

1. **Install LangSmith CLI** (if you haven't already):
   ```bash
   pip install langsmith
   ```

2. **Configure Environment Variables**:
   
   Copy `.env.example` to `.env` and add your keys:
   ```bash
   cp .env.example .env
   ```
   
   Required variables:
   ```bash
   # LangSmith Configuration
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your_langsmith_api_key_here
   LANGCHAIN_PROJECT=agentic-drug-discovery
   
   # LLM Provider (choose one)
   OPENAI_API_KEY=your_openai_key_here
   # OR
   ANTHROPIC_API_KEY=your_anthropic_key_here
   ```

3. **Get LangSmith API Key**:
   - Sign up at [smith.langchain.com](https://smith.langchain.com/)
   - Go to Settings → API Keys
   - Create a new API key
   - Add it to your `.env` file

## Running with LangGraph Studio

### Option 1: Open in LangGraph Studio Desktop

1. Install [LangGraph Studio Desktop](https://github.com/langchain-ai/langgraph-studio)
2. Open the project directory in Studio
3. The `langgraph.json` configuration will be auto-detected
4. Run the agent and visualize the graph execution

### Option 2: Run with LangGraph CLI

```bash
# Install langgraph-cli
pip install langgraph-cli

# Start the development server
langgraph dev

# Or specify the graph explicitly
langgraph dev --graph src.agents.target_agent:create_agent
```

### Option 3: Deploy to LangGraph Cloud

```bash
# Deploy to LangGraph Cloud
langgraph deploy

# Test the deployed agent
langgraph invoke --deployment-url <your-url> --input '{"disease_query": "Lupus"}'
```

## Project Configuration

The `langgraph.json` file defines:

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./src/agents/target_agent.py:create_agent"
  },
  "env": ".env"
}
```

This tells LangGraph Studio:
- **dependencies**: Install local package
- **graphs**: The main agent graph is in `target_agent.py` via `create_agent()` function
- **env**: Load environment variables from `.env`

## Using the Studio

Once running in LangGraph Studio, you can:

1. **Visualize the Graph**: See the flow: plan → select_tool → execute_search → synthesize
2. **Inspect State**: View the `AgentState` at each step
3. **Debug Decisions**: See LLM prompts and responses for each reasoning step
4. **Trace Execution**: Follow the agent's decision-making process
5. **Test Inputs**: Try different disease queries and see how the agent adapts

## Example Usage in Studio

Input state:
```json
{
  "disease_query": "Systemic Lupus Erythematosus",
  "verbose_reasoning": true
}
```

The Studio will show:
- How the agent creates a research plan
- Which tools it selects and why
- Intermediate analyses after each tool execution
- Evidence synthesis for each protein target
- Final rankings with reasoning

## Tracing in LangSmith

All executions are automatically traced to LangSmith when `LANGCHAIN_TRACING_V2=true`.

View traces at: [smith.langchain.com](https://smith.langchain.com/)

You'll see:
- Full conversation history
- LLM token usage
- Latency metrics
- Error tracking
- State evolution

## Troubleshooting

**Graph not loading?**
- Check that `langgraph.json` is in project root
- Verify the path in `graphs` points to correct function
- Ensure dependencies are installed: `pip install -r requirements.txt`

**Environment variables not loading?**
- Make sure `.env` file exists
- Check variable names match exactly (e.g., `LANGCHAIN_API_KEY` not `LANGSMITH_API_KEY`)
- Try setting them directly: `export LANGCHAIN_API_KEY=...`

**Import errors?**
- Install the local package: `pip install -e .`
- Or add to PYTHONPATH: `export PYTHONPATH="${PYTHONPATH}:$(pwd)"`

## Features Visible in Studio

With this setup, LangGraph Studio will show:

1. **Agent Decision Points**: See when and why the agent chooses tools
2. **State Evolution**: Track how `AgentState` changes through the workflow
3. **LLM Reasoning**: View all prompts and responses
4. **Tool Executions**: Monitor database queries and results
5. **Error Handling**: See retries and fallbacks in action
6. **Performance Metrics**: Timing for each node and LLM call

## Development Workflow

Recommended workflow with Studio:

1. Make code changes to `src/agents/target_agent.py` or tools
2. Studio auto-reloads (if using `langgraph dev`)
3. Test immediately with new disease queries
4. Debug issues by inspecting state and LLM calls
5. Iterate quickly without manual testing

## Going Further

- **Custom Graphs**: Add more graphs in `langgraph.json`
- **Streaming**: Enable streaming output in Studio
- **Human-in-the-Loop**: Add interrupt points for user feedback
- **Evaluation**: Use LangSmith datasets to evaluate different strategies
