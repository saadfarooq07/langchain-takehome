# Real-time Log Analysis Component

A streamlined log analysis interface powered by LangGraph for real-time streaming analysis.

## Features

### ⚡ **Real-time Streaming**
- Live analysis with progressive results
- Stop analysis mid-stream
- Thread-based sessions
- LangGraph integration

### 📁 **File Support**
- Upload `.log` and `.txt` files
- Drag & drop interface  
- Large file handling
- Text paste alternative

### 📊 **Rich Results Display**
- **Issues**: Categorized by severity (critical, high, medium, low)
- **Suggestions**: Actionable recommendations
- **Explanations**: Detailed context and insights
- **Diagnostic Commands**: Ready-to-run shell commands
- **Documentation**: Relevant reference links

### 🔄 **Stream Management**
- Live status updates
- Thread ID tracking
- Error handling with retry
- Clean state management

## Usage

```tsx
// Upload file or paste log content
// Click "Start Analysis"  
// Watch results appear progressively
// Stop anytime if needed
```

## Component Structure

```
LogAnalysis/
├── Header with Live Analysis badge
├── Input Form
│   ├── File Upload
│   ├── Text Input
│   └── Analysis Controls
├── Stream Status
└── Results Display
    ├── Issues
    ├── Suggestions
    ├── Explanations
    ├── Diagnostic Commands
    └── Documentation References
```

## Integration

### Props
```tsx
interface LogAnalysisProps {
  apiUrl?: string;      // Default: 'http://localhost:2024'
  assistantId?: string; // Default: 'log_analyzer'
  authToken?: string;   // Optional auth token
}
```

### LangGraph Integration
- **Endpoint**: Configurable LangGraph server URL
- **Assistant**: Configurable assistant/graph ID
- **Authentication**: Optional Bearer token support
- **Streaming**: Real-time bidirectional communication

## State Management

- **Form State**: Input content, files
- **Stream State**: LangGraph SDK for real-time analysis
- **Thread State**: Session management with thread IDs
- **Results State**: Progressive result accumulation

## Error Handling

- Stream connection errors with retry
- File upload validation
- Network interruption recovery
- User-friendly error messages

## Performance

- **Progressive Loading**: Results appear as generated
- **Efficient Streaming**: Low latency updates
- **Memory Optimized**: Efficient state management
- **File Handling**: Supports large log files

## Example Integration

```tsx
import LogAnalysis from './components/LogAnalysis';

function App() {
  return (
    <LogAnalysis
      apiUrl="http://localhost:2024"
      assistantId="log_analyzer"
    />
  );
}
```

## Stream Flow

1. User inputs log content (file upload or text paste)
2. Component submits to LangGraph with thread management
3. Real-time results stream back progressively
4. Users can stop analysis anytime
5. Complete results displayed with rich formatting

## UI Features

- **Live Indicators**: Shows analysis progress
- **Stop Control**: Interrupt analysis anytime  
- **Thread Tracking**: Session continuity
- **File Support**: Seamless file upload
- **Responsive Design**: Works on all screen sizes

## Dependencies

- `@langchain/langgraph-sdk/react` - Streaming integration
- `shadcn/ui` components - UI elements
- `lucide-react` - Icons
- React 18+ - Hooks and modern features
