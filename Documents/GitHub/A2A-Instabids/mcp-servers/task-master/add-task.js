#!/usr/bin/env node

import { execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

// Get the directory name
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path to the task-master.js bin file
const binPath = path.join(__dirname, 'node_modules', 'task-master-ai', 'bin', 'task-master.js');

// Task details from command line arguments
const title = process.argv[2] || 'Implement A2A Protocol';
const description = process.argv[3] || 'Implement the A2A protocol for agent-to-agent communication in the InstaBids platform.';
const priority = process.argv[4] || 'high';

console.log(`Adding Task Master task: ${title}`);

try {
  // Change to the project root directory
  const projectRoot = path.join(__dirname, '..', '..');
  process.chdir(projectRoot);
  console.log(`Changed directory to: ${process.cwd()}`);
  
  // Execute the task-master add-task command
  const command = `node "${binPath}" add-task --title "${title}" --description "${description}" --priority ${priority}`;
  console.log(`Executing command: ${command}`);
  
  const result = execSync(command, {
    encoding: 'utf8',
    env: {
      ...process.env,
      ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY || 'your_anthropic_api_key_here',
      PERPLEXITY_API_KEY: process.env.PERPLEXITY_API_KEY || 'your_perplexity_api_key_here',
      MODEL: process.env.MODEL || 'claude-3-haiku-20240307',
      PERPLEXITY_MODEL: process.env.PERPLEXITY_MODEL || 'sonar-small-online',
      MAX_TOKENS: process.env.MAX_TOKENS || '64000',
      TEMPERATURE: process.env.TEMPERATURE || '0.2',
      DEFAULT_SUBTASKS: process.env.DEFAULT_SUBTASKS || '5',
      DEFAULT_PRIORITY: process.env.DEFAULT_PRIORITY || 'medium'
    }
  });
  
  console.log('Task added successfully:');
  console.log(result);
} catch (error) {
  console.error('Error adding task:', error.message);
  if (error.stdout) console.log('stdout:', error.stdout);
  if (error.stderr) console.log('stderr:', error.stderr);
  process.exit(1);
}
