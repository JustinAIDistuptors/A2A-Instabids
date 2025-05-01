#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError
} from '@modelcontextprotocol/sdk/types.js';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';
import dotenv from 'dotenv';
import { execSync } from 'child_process';

// Load environment variables
dotenv.config();

// Constants
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Get package.json version
const packagePath = path.join(__dirname, 'package.json');
const packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf8'));

class TaskMasterMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: 'Task Master MCP Server',
        version: packageJson.version,
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    // Error handling
    this.server.onerror = (error) => console.error('[MCP Error]', error);
    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });

    this.setupToolHandlers();
  }

  setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'initialize_project',
          description: 'Initialize a new Task Master project in the current directory',
          inputSchema: {
            type: 'object',
            properties: {
              projectName: {
                type: 'string',
                description: 'Name of the project',
              },
              description: {
                type: 'string',
                description: 'Description of the project',
              }
            },
            required: ['projectName'],
          },
        },
        {
          name: 'parse_prd',
          description: 'Parse a PRD document and generate tasks',
          inputSchema: {
            type: 'object',
            properties: {
              prdPath: {
                type: 'string',
                description: 'Path to the PRD document',
              },
              prdContent: {
                type: 'string',
                description: 'Content of the PRD document',
              }
            },
            required: ['prdPath'],
          },
        },
        {
          name: 'list_tasks',
          description: 'List all tasks in the project',
          inputSchema: {
            type: 'object',
            properties: {
              status: {
                type: 'string',
                description: 'Filter tasks by status (todo, in-progress, done, all)',
                enum: ['todo', 'in-progress', 'done', 'all'],
              }
            },
          },
        },
        {
          name: 'get_task',
          description: 'Get details of a specific task',
          inputSchema: {
            type: 'object',
            properties: {
              taskId: {
                type: 'string',
                description: 'ID of the task to retrieve',
              }
            },
            required: ['taskId'],
          },
        },
        {
          name: 'next_task',
          description: 'Get the next task to work on',
          inputSchema: {
            type: 'object',
            properties: {},
          },
        },
        {
          name: 'add_task',
          description: 'Add a new task to the project',
          inputSchema: {
            type: 'object',
            properties: {
              title: {
                type: 'string',
                description: 'Title of the task',
              },
              description: {
                type: 'string',
                description: 'Description of the task',
              },
              priority: {
                type: 'string',
                description: 'Priority of the task (low, medium, high)',
                enum: ['low', 'medium', 'high'],
              },
              status: {
                type: 'string',
                description: 'Status of the task (todo, in-progress, done)',
                enum: ['todo', 'in-progress', 'done'],
              }
            },
            required: ['title'],
          },
        },
        {
          name: 'update_task',
          description: 'Update an existing task',
          inputSchema: {
            type: 'object',
            properties: {
              taskId: {
                type: 'string',
                description: 'ID of the task to update',
              },
              title: {
                type: 'string',
                description: 'New title of the task',
              },
              description: {
                type: 'string',
                description: 'New description of the task',
              },
              priority: {
                type: 'string',
                description: 'New priority of the task (low, medium, high)',
                enum: ['low', 'medium', 'high'],
              },
              status: {
                type: 'string',
                description: 'New status of the task (todo, in-progress, done)',
                enum: ['todo', 'in-progress', 'done'],
              }
            },
            required: ['taskId'],
          },
        },
        {
          name: 'remove_task',
          description: 'Remove a task from the project',
          inputSchema: {
            type: 'object',
            properties: {
              taskId: {
                type: 'string',
                description: 'ID of the task to remove',
              }
            },
            required: ['taskId'],
          },
        },
        {
          name: 'expand_task',
          description: 'Expand a task into subtasks',
          inputSchema: {
            type: 'object',
            properties: {
              taskId: {
                type: 'string',
                description: 'ID of the task to expand',
              },
              numSubtasks: {
                type: 'number',
                description: 'Number of subtasks to generate',
              }
            },
            required: ['taskId'],
          },
        }
      ],
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      try {
        const { name, arguments: args } = request.params;
        
        // Execute the appropriate task-master-ai command based on the tool name
        switch (name) {
          case 'initialize_project':
            return this.executeTaskMasterCommand(['init'], args);
          
          case 'parse_prd':
            return this.executeTaskMasterCommand(['parse-prd', args.prdPath], args);
          
          case 'list_tasks':
            return this.executeTaskMasterCommand(['list'], args);
          
          case 'get_task':
            return this.executeTaskMasterCommand(['show', args.taskId], args);
          
          case 'next_task':
            return this.executeTaskMasterCommand(['next'], args);
          
          case 'add_task':
            const addTaskArgs = ['add-task'];
            if (args.title) addTaskArgs.push('--title', args.title);
            if (args.description) addTaskArgs.push('--description', args.description);
            if (args.priority) addTaskArgs.push('--priority', args.priority);
            if (args.status) addTaskArgs.push('--status', args.status);
            return this.executeTaskMasterCommand(addTaskArgs, args);
          
          case 'update_task':
            const updateTaskArgs = ['update', args.taskId];
            if (args.title) updateTaskArgs.push('--title', args.title);
            if (args.description) updateTaskArgs.push('--description', args.description);
            if (args.priority) updateTaskArgs.push('--priority', args.priority);
            if (args.status) updateTaskArgs.push('--status', args.status);
            return this.executeTaskMasterCommand(updateTaskArgs, args);
          
          case 'remove_task':
            return this.executeTaskMasterCommand(['remove', args.taskId], args);
          
          case 'expand_task':
            const expandTaskArgs = ['expand', args.taskId];
            if (args.numSubtasks) expandTaskArgs.push('--num', args.numSubtasks.toString());
            return this.executeTaskMasterCommand(expandTaskArgs, args);
          
          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${name}`
            );
        }
      } catch (error) {
        console.error(`Error executing tool ${request.params.name}:`, error);
        return {
          content: [
            {
              type: 'text',
              text: `Error: ${error.message}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  executeTaskMasterCommand(commandArgs, args) {
    try {
      // Import the task-master-ai package directly
      const taskMasterPath = path.join(__dirname, 'node_modules', 'task-master-ai');
      
      // Create a mock response for initialization
      if (commandArgs[0] === 'init') {
        return {
          content: [
            {
              type: 'text',
              text: `Task Master initialization would be interactive. To initialize a Task Master project, please run the following command in your terminal:
              
cd "${path.join(__dirname, '..', '..')}"
node "${path.join(__dirname, 'node_modules', 'task-master-ai', 'bin', 'task-master.js')}" init --name "A2A-Instabids" --yes

This will set up Task Master for your A2A-Instabids project with default settings.

Alternatively, you can run our helper script:

cd "${path.join(__dirname)}"
node init-project.js

This script will handle the initialization process automatically.`,
            },
          ],
        };
      }
      
      // For other commands, try to execute them directly
      const command = `node "${path.join(__dirname, 'node_modules', 'task-master-ai', 'bin', 'task-master.js')}" ${commandArgs.join(' ')}`;
      console.log(`Executing command: ${command}`);
      
      // Set the current working directory to the project root
      const projectRoot = path.join(__dirname, '..', '..');
      
      const result = execSync(command, {
        encoding: 'utf8',
        cwd: projectRoot,
        env: {
          ...process.env,
          ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY || '',
          PERPLEXITY_API_KEY: process.env.PERPLEXITY_API_KEY || '',
          MODEL: process.env.MODEL || 'claude-3-haiku-20240307',
          PERPLEXITY_MODEL: process.env.PERPLEXITY_MODEL || 'sonar-small-online',
          MAX_TOKENS: process.env.MAX_TOKENS || '64000',
          TEMPERATURE: process.env.TEMPERATURE || '0.2',
          DEFAULT_SUBTASKS: process.env.DEFAULT_SUBTASKS || '5',
          DEFAULT_PRIORITY: process.env.DEFAULT_PRIORITY || 'medium'
        }
      });
      
      return {
        content: [
          {
            type: 'text',
            text: result,
          },
        ],
      };
    } catch (error) {
      console.error('Error executing task-master command:', error);
      return {
        content: [
          {
            type: 'text',
            text: `Error executing task-master command: ${error.message}\n${error.stdout || ''}\n${error.stderr || ''}`,
          },
        ],
        isError: true,
      };
    }
  }

  async start() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Task Master MCP server running on stdio');
  }
}

const server = new TaskMasterMCPServer();
server.start().catch(console.error);
