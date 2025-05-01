import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get the directory name
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Check if task-master-ai is installed
const nodeModulesPath = path.join(__dirname, 'node_modules');
const taskMasterPath = path.join(nodeModulesPath, 'task-master-ai');
const binPath = path.join(taskMasterPath, 'bin', 'task-master.js');

console.log('Checking Task Master installation...');
console.log('Node modules path:', nodeModulesPath);
console.log('Task Master path:', taskMasterPath);
console.log('Bin path:', binPath);

// Check if directories and files exist
console.log('Node modules exists:', fs.existsSync(nodeModulesPath));
console.log('Task Master exists:', fs.existsSync(taskMasterPath));
console.log('Bin file exists:', fs.existsSync(binPath));

// If the bin file exists, print its content
if (fs.existsSync(binPath)) {
  console.log('Bin file content:');
  console.log(fs.readFileSync(binPath, 'utf8').slice(0, 500) + '...');
}

// List all files in the task-master-ai directory
if (fs.existsSync(taskMasterPath)) {
  console.log('Files in task-master-ai directory:');
  fs.readdirSync(taskMasterPath).forEach(file => {
    console.log('- ' + file);
  });
  
  // Check if bin directory exists and list its contents
  const binDir = path.join(taskMasterPath, 'bin');
  if (fs.existsSync(binDir)) {
    console.log('Files in bin directory:');
    fs.readdirSync(binDir).forEach(file => {
      console.log('- ' + file);
    });
  }
}
