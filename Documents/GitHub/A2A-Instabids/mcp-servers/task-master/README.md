# Task Master MCP Server

This is an MCP (Model Context Protocol) server implementation for [Task Master](https://github.com/eyaltoledano/claude-task-master), a task management system for AI-driven development with Claude.

## Overview

The Task Master MCP server provides a set of tools that allow AI assistants to interact with Task Master functionality, including:

- Initializing projects
- Parsing PRD documents
- Managing tasks (add, update, remove)
- Expanding tasks into subtasks
- Listing and filtering tasks
- Getting task details

## Installation

The server is already installed and configured in this repository. It uses the `task-master-ai` npm package to provide its functionality.

## Configuration

The server is configured in the `cline_mcp_settings.json` file with the following settings:

```json
{
  "github.com/eyaltoledano/claude-task-master": {
    "command": "node",
    "args": [
      "c:/Users/Not John Or Justin/Documents/GitHub/A2A-Instabids/mcp-servers/task-master/server.js"
    ],
    "env": {
      "ANTHROPIC_API_KEY": "your_anthropic_api_key_here",
      "PERPLEXITY_API_KEY": "your_perplexity_api_key_here",
      "MODEL": "claude-3-haiku-20240307",
      "PERPLEXITY_MODEL": "sonar-small-online",
      "MAX_TOKENS": "64000",
      "TEMPERATURE": "0.2",
      "DEFAULT_SUBTASKS": "5",
      "DEFAULT_PRIORITY": "medium"
    },
    "disabled": false,
    "autoApprove": [
      "initialize_project",
      "list_tasks",
      "next_task",
      "get_task"
    ]
  }
}
```

## Environment Variables

The server uses the following environment variables, which can be configured in the `.env` file:

- `ANTHROPIC_API_KEY`: Your Anthropic API key for Claude
- `PERPLEXITY_API_KEY`: Your Perplexity API key (optional)
- `MODEL`: The Claude model to use (default: claude-3-haiku-20240307)
- `PERPLEXITY_MODEL`: The Perplexity model to use (default: sonar-small-online)
- `MAX_TOKENS`: Maximum tokens for API calls (default: 64000)
- `TEMPERATURE`: Temperature for API calls (default: 0.2)
- `DEFAULT_SUBTASKS`: Default number of subtasks to generate (default: 5)
- `DEFAULT_PRIORITY`: Default priority for tasks (default: medium)

## Available Tools

The server provides the following tools:

### initialize_project

Initialize a new Task Master project in the current directory.

```json
{
  "projectName": "A2A-Instabids",
  "description": "Optional project description"
}
```

### parse_prd

Parse a PRD document and generate tasks.

```json
{
  "prdPath": "path/to/prd.md",
  "prdContent": "Optional PRD content if path is not available"
}
```

### list_tasks

List all tasks in the project.

```json
{
  "status": "todo" // Optional: Filter by status (todo, in-progress, done, all)
}
```

### get_task

Get details of a specific task.

```json
{
  "taskId": "task-1"
}
```

### next_task

Get the next task to work on.

```json
{}
```

### add_task

Add a new task to the project.

```json
{
  "title": "Implement A2A Protocol",
  "description": "Implement the A2A protocol for agent-to-agent communication",
  "priority": "high", // Optional: low, medium, high
  "status": "todo" // Optional: todo, in-progress, done
}
```

### update_task

Update an existing task.

```json
{
  "taskId": "task-1",
  "title": "New title", // Optional
  "description": "New description", // Optional
  "priority": "medium", // Optional: low, medium, high
  "status": "in-progress" // Optional: todo, in-progress, done
}
```

### remove_task

Remove a task from the project.

```json
{
  "taskId": "task-1"
}
```

### expand_task

Expand a task into subtasks.

```json
{
  "taskId": "task-1",
  "numSubtasks": 5 // Optional: Number of subtasks to generate
}
```

## Helper Scripts

The repository includes several helper scripts to interact with Task Master directly:

- `init-project.js`: Initialize a Task Master project
- `add-task.js`: Add a task to the project
- `list-tasks.js`: List tasks in the project
- `check-install.js`: Check if Task Master is installed correctly

## Usage in A2A-Instabids

This MCP server can be used by AI assistants to manage tasks for the A2A-Instabids project. It provides a structured way to track and organize development tasks, making it easier to manage the project's progress.

## Note on Interactive Commands

Some Task Master commands (like `init`) are interactive and require user input. For these commands, the MCP server provides instructions on how to run them directly in the terminal.
