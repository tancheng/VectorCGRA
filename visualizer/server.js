const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 8765;

app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

// API to list available trace files
app.get('/api/traces', (req, res) => {
  const traceDir = path.join(__dirname, '..', 'trace_output');
  if (!fs.existsSync(traceDir)) {
    return res.json([]);
  }
  const files = fs.readdirSync(traceDir)
    .filter(f => f.endsWith('.jsonl'))
    .map(f => ({
      name: f,
      path: path.join(traceDir, f),
      size: fs.statSync(path.join(traceDir, f)).size,
    }));
  res.json(files);
});

// API to load a trace file
app.get('/api/trace/:filename', (req, res) => {
  const traceDir = path.join(__dirname, '..', 'trace_output');
  const filepath = path.join(traceDir, req.params.filename);

  if (!fs.existsSync(filepath)) {
    return res.status(404).json({ error: 'File not found' });
  }

  const content = fs.readFileSync(filepath, 'utf-8');
  const lines = content.trim().split('\n');
  const cycles = lines.map((line, idx) => {
    try {
      return JSON.parse(line);
    } catch (e) {
      return { cycle: idx, error: 'Parse error' };
    }
  });

  res.json({
    filename: req.params.filename,
    totalCycles: cycles.length,
    cycles: cycles,
  });
});

// API to load a custom file path
app.post('/api/load', (req, res) => {
  const filepath = req.body.filepath;
  if (!filepath || !fs.existsSync(filepath)) {
    return res.status(404).json({ error: 'File not found' });
  }

  const content = fs.readFileSync(filepath, 'utf-8');
  const lines = content.trim().split('\n');
  const cycles = lines.map((line, idx) => {
    try {
      return JSON.parse(line);
    } catch (e) {
      return { cycle: idx, error: 'Parse error' };
    }
  });

  res.json({
    filename: path.basename(filepath),
    totalCycles: cycles.length,
    cycles: cycles,
  });
});

app.listen(PORT, () => {
  console.log(`CGRA Visualizer running at http://localhost:${PORT}`);
});
