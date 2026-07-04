import { spawn } from 'child_process';
import path from 'path';

export async function getAISignals(): Promise<any[]> {
  return new Promise((resolve, reject) => {
    const pythonPath = path.join(__dirname, '../../../ai-service/ai_service.py');
    const python = spawn('python', [pythonPath]);
    
    let output = '';
    
    python.stdout.on('data', (data) => {
      output += data.toString();
    });
    
    python.on('close', (code) => {
      if (code === 0) {
        try {
          const jsonMatch = output.match(/\[.*\]/s);
          if (jsonMatch) {
            resolve(JSON.parse(jsonMatch[0]));
          } else {
            resolve([]);
          }
        } catch (e) {
          resolve([]);
        }
      } else {
        reject(new Error(`Python process exited with code ${code}`));
      }
    });
  });
}