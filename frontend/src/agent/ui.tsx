import React from 'react';
import { useStreamContext } from '@langchain/langgraph-sdk/react-ui';

// Simple UI for LangGraph Studio
export default function AgentUI() {
  const { messages } = useStreamContext();
  
  return (
    <div style={{ padding: '20px', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      <h1 style={{ fontSize: '24px', marginBottom: '20px' }}>Log Analyzer Agent</h1>
      
      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ fontSize: '18px', marginBottom: '10px' }}>Messages</h2>
        {messages.map((msg, idx) => (
          <div key={idx} style={{ 
            padding: '10px', 
            marginBottom: '10px', 
            backgroundColor: '#f5f5f5',
            borderRadius: '4px',
            border: '1px solid #ddd'
          }}>
            <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>
              {msg.type || 'Message'}
            </div>
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
              {typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content, null, 2)}
            </pre>
          </div>
        ))}
      </div>
      
      <div style={{ 
        padding: '10px', 
        backgroundColor: '#e8f5e9',
        borderRadius: '4px',
        border: '1px solid #4caf50'
      }}>
        <p>✅ Enhanced Analysis is enabled</p>
        <p>Use the Studio interface to submit logs for analysis.</p>
      </div>
    </div>
  );
}