import React, { useState, useRef, useEffect } from 'react';
import { 
  MessageCircle, 
  Send, 
  Loader2, 
  AlertTriangle, 
  Shield, 
  Brain,
  Clock,
  CheckCircle,
  XCircle,
  Sparkles
} from 'lucide-react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const EnhancedChatInterface = ({ documents }) => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'system',
      content: 'Hello! I\'m your NCDHHS PDF Q&A Assistant powered by AWS Bedrock. I can help you find information from the processed documents. Ask me anything!',
      timestamp: new Date()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [useGuardrails, setUseGuardrails] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [backendStatus, setBackendStatus] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Check backend status on mount
  useEffect(() => {
    const checkBackendStatus = async () => {
      try {
        const response = await axios.get(`${API_URL}/health`);
        setBackendStatus(response.data);
      } catch (error) {
        console.error('Backend health check failed:', error);
        setBackendStatus({ status: 'error', message: 'Backend unavailable' });
      }
    };

    checkBackendStatus();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      // Use the current backend endpoint for Q&A
      const response = await axios.post(`${API_URL}/ask-question`, {
        question: userMessage.content,
        use_guardrails: useGuardrails,
        max_results: 5
      });

      const assistantMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: response.data.answer,
        timestamp: new Date(),
        metadata: {
          sources: response.data.sources || [],
          confidence: response.data.confidence,
          guardrails_applied: response.data.guardrails_applied || useGuardrails,
          model: response.data.model || 'bedrock-model',
          processing_time: response.data.processing_time,
          documents_searched: response.data.documents_searched || documents.length
        }
      };

      setMessages(prev => [...prev, assistantMessage]);

    } catch (error) {
      console.error('Error getting response:', error);
      
      let errorContent = 'Sorry, I encountered an error while processing your question. Please try again.';
      
      if (error.response?.status === 503) {
        errorContent = 'The AI service is currently unavailable. Please check if Bedrock models are enabled in your AWS console.';
      } else if (error.response?.data?.detail) {
        errorContent = `Error: ${error.response.data.detail}`;
      }
      
      const errorMessage = {
        id: Date.now() + 1,
        type: 'error',
        content: errorContent,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const MessageBubble = ({ message }) => {
    const isUser = message.type === 'user';
    const isSystem = message.type === 'system';
    const isError = message.type === 'error';

    return (
      <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
        <div className={`max-w-3xl px-4 py-3 rounded-lg ${
          isUser 
            ? 'bg-blue-600 text-white' 
            : isError 
            ? 'bg-red-50 border border-red-200 text-red-800'
            : isSystem
            ? 'bg-gray-100 text-gray-800'
            : 'bg-white border border-gray-200 text-gray-800'
        }`}>
          {/* Message Header */}
          {!isUser && (
            <div className="flex items-center space-x-2 mb-2">
              {isError ? (
                <XCircle className="w-4 h-4 text-red-500" />
              ) : isSystem ? (
                <MessageCircle className="w-4 h-4 text-gray-500" />
              ) : (
                <div className="flex items-center space-x-1">
                  <Brain className="w-4 h-4 text-blue-500" />
                  <Sparkles className="w-3 h-3 text-yellow-500" />
                </div>
              )}
              <span className="text-xs font-medium">
                {isError ? 'Error' : isSystem ? 'System' : 'AI Assistant'}
              </span>
              {message.metadata?.guardrails_applied && (
                <Shield className="w-3 h-3 text-green-500" title="Content filtered by guardrails" />
              )}
            </div>
          )}

          {/* Message Content */}
          <div className="whitespace-pre-wrap">{message.content}</div>

          {/* Message Metadata */}
          {message.metadata && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="flex flex-wrap gap-2 text-xs">
                {message.metadata.model && (
                  <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full">
                    {message.metadata.model}
                  </span>
                )}
                {message.metadata.documents_searched && (
                  <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full">
                    {message.metadata.documents_searched} docs searched
                  </span>
                )}
                {message.metadata.confidence && (
                  <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full">
                    {Math.round(message.metadata.confidence * 100)}% confidence
                  </span>
                )}
                {message.metadata.processing_time && (
                  <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded-full flex items-center space-x-1">
                    <Clock className="w-3 h-3" />
                    <span>{message.metadata.processing_time}ms</span>
                  </span>
                )}
              </div>

              {/* Sources */}
              {message.metadata.sources && message.metadata.sources.length > 0 && (
                <div className="mt-2">
                  <div className="text-xs font-medium text-gray-600 mb-1">Sources:</div>
                  <div className="space-y-1">
                    {message.metadata.sources.map((source, index) => (
                      <div key={index} className="text-xs bg-gray-50 p-2 rounded border-l-2 border-blue-300">
                        <div className="font-medium">{source.title || `Document ${index + 1}`}</div>
                        <div className="text-gray-600 truncate">{source.content}</div>
                        {source.score && (
                          <div className="text-gray-500">Relevance: {Math.round(source.score * 100)}%</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Timestamp */}
          <div className={`text-xs mt-2 ${isUser ? 'text-blue-200' : 'text-gray-500'}`}>
            {message.timestamp.toLocaleTimeString()}
          </div>
        </div>
      </div>
    );
  };

  const QuickActions = () => {
    const quickQuestions = [
      "What are the main topics covered in these documents?",
      "Can you summarize the key policies mentioned?",
      "What are the contact details provided?",
      "Are there any deadlines or important dates?",
      "What services are available?"
    ];

    return (
      <div className="mb-4">
        <div className="text-sm text-gray-600 mb-2">Quick questions:</div>
        <div className="flex flex-wrap gap-2">
          {quickQuestions.map((question, index) => (
            <button
              key={index}
              onClick={() => setInputMessage(question)}
              className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-full transition-colors"
              disabled={isLoading}
            >
              {question}
            </button>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-sm border">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center space-x-2">
          <MessageCircle className="w-6 h-6 text-blue-600" />
          <h2 className="text-xl font-semibold">Enhanced Q&A Assistant</h2>
          <div className="flex items-center space-x-1">
            <Brain className="w-4 h-4 text-blue-500" />
            <span className="text-xs text-gray-500">Powered by Bedrock</span>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          {backendStatus && (
            <div className={`flex items-center space-x-1 px-2 py-1 rounded-full text-xs ${
              backendStatus.status === 'healthy' 
                ? 'bg-green-100 text-green-800' 
                : 'bg-red-100 text-red-800'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                backendStatus.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
              }`} />
              <span>{backendStatus.status === 'healthy' ? 'Online' : 'Offline'}</span>
            </div>
          )}
          
          {useGuardrails && (
            <div className="flex items-center space-x-1 px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">
              <Shield className="w-3 h-3" />
              <span>Protected</span>
            </div>
          )}
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            Settings
          </button>
        </div>
      </div>

      {/* Advanced Settings */}
      {showAdvanced && (
        <div className="p-4 bg-gray-50 border-b">
          <div className="flex items-center space-x-4">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={useGuardrails}
                onChange={(e) => setUseGuardrails(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm">Enable Content Guardrails</span>
            </label>
            <div className="text-xs text-gray-500">
              Filters inappropriate content and PII data
            </div>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {documents.length === 0 && (
          <div className="text-center py-8">
            <AlertTriangle className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
            <p className="text-gray-600">No documents processed yet. Please process some PDFs first.</p>
          </div>
        )}

        {documents.length > 0 && messages.length === 1 && (
          <QuickActions />
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isLoading && (
          <div className="flex justify-start mb-4">
            <div className="bg-gray-100 px-4 py-3 rounded-lg flex items-center space-x-2">
              <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
              <span className="text-gray-600">AI is thinking...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t">
        <form onSubmit={handleSubmit} className="flex space-x-2">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder={documents.length > 0 ? "Ask a question about the documents..." : "Process some documents first..."}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading || documents.length === 0}
          />
          <button
            type="submit"
            disabled={isLoading || !inputMessage.trim() || documents.length === 0}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </form>

        {/* Status */}
        <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
          <span>{documents.length} documents available</span>
          <div className="flex items-center space-x-2">
            {backendStatus?.version && (
              <span>Backend v{backendStatus.version}</span>
            )}
            {useGuardrails && (
              <div className="flex items-center space-x-1">
                <Shield className="w-3 h-3 text-green-500" />
                <span>Protected</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default EnhancedChatInterface;
