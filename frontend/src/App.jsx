import React, { useState, useEffect } from 'react';
import { FileText, Download, MessageCircle, Loader2, AlertCircle, Zap, Brain } from 'lucide-react';
import EnhancedPDFProcessor from './components/EnhancedPDFProcessor';
import EnhancedChatInterface from './components/EnhancedChatInterface';
import DocumentList from './components/DocumentList';

function App() {
  const [documents, setDocuments] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState('process');
  const [processingStatus, setProcessingStatus] = useState('');
  const [systemStatus, setSystemStatus] = useState(null);

  const handleDocumentsProcessed = (processedDocs) => {
    setDocuments(prev => [...prev, ...processedDocs]);
    setActiveTab('chat');
  };

  const handleProcessingStatus = (status) => {
    setProcessingStatus(status);
  };

  // Check system health on load
  useEffect(() => {
    const checkSystemHealth = async () => {
      try {
        const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/health`);
        const data = await response.json();
        setSystemStatus(data);
      } catch (error) {
        console.error('System health check failed:', error);
        setSystemStatus({ status: 'error', message: 'Backend unavailable' });
      }
    };

    checkSystemHealth();
  }, []);

  const tabs = [
    { id: 'process', name: 'Process PDFs', icon: FileText, color: 'blue' },
    { id: 'chat', name: 'Q&A Assistant', icon: MessageCircle, color: 'green', badge: documents.length },
    { id: 'documents', name: 'Documents', icon: Download, color: 'purple', badge: documents.length }
  ];

  const TabButton = ({ tab, isActive, onClick }) => {
    const Icon = tab.icon;
    const colorClasses = {
      blue: isActive ? 'bg-blue-600 text-white' : 'text-blue-600 hover:bg-blue-50',
      green: isActive ? 'bg-green-600 text-white' : 'text-green-600 hover:bg-green-50',
      purple: isActive ? 'bg-purple-600 text-white' : 'text-purple-600 hover:bg-purple-50'
    };

    return (
      <button
        onClick={onClick}
        className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-colors relative ${colorClasses[tab.color]}`}
      >
        <Icon className="w-5 h-5" />
        <span>{tab.name}</span>
        {tab.badge > 0 && (
          <span className={`absolute -top-2 -right-2 w-5 h-5 text-xs rounded-full flex items-center justify-center ${
            isActive ? 'bg-white text-gray-800' : `bg-${tab.color}-600 text-white`
          }`}>
            {tab.badge}
          </span>
        )}
      </button>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2">
                <Brain className="w-8 h-8 text-blue-600" />
                <Zap className="w-6 h-6 text-yellow-500" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">
                  {import.meta.env.VITE_APP_TITLE || 'NCDHHS PDF Q&A Assistant'}
                </h1>
                <p className="text-sm text-gray-500">Enhanced with AWS Bedrock AI</p>
              </div>
            </div>
            
            {/* System Status */}
            <div className="flex items-center space-x-4">
              {systemStatus && (
                <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-sm ${
                  systemStatus.status === 'healthy' 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  <div className={`w-2 h-2 rounded-full ${
                    systemStatus.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                  }`} />
                  <span>{systemStatus.status === 'healthy' ? 'System Online' : 'System Error'}</span>
                </div>
              )}
              
              {systemStatus?.version && (
                <div className="text-xs text-gray-500">
                  v{systemStatus.version}
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Navigation Tabs */}
        <div className="flex space-x-4 mb-8">
          {tabs.map((tab) => (
            <TabButton
              key={tab.id}
              tab={tab}
              isActive={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
            />
          ))}
        </div>

        {/* Processing Status */}
        {processingStatus && (
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center space-x-2">
              <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
              <span className="text-blue-800 font-medium">Status:</span>
              <span className="text-blue-700">{processingStatus}</span>
            </div>
          </div>
        )}

        {/* Tab Content */}
        <div className="bg-white rounded-lg shadow-sm">
          {activeTab === 'process' && (
            <div className="p-6">
              <EnhancedPDFProcessor
                onDocumentsProcessed={handleDocumentsProcessed}
                onProcessingStatus={handleProcessingStatus}
              />
            </div>
          )}

          {activeTab === 'chat' && (
            <div className="h-[600px]">
              <EnhancedChatInterface documents={documents} />
            </div>
          )}

          {activeTab === 'documents' && (
            <div className="p-6">
              <DocumentList documents={documents} />
            </div>
          )}
        </div>

        {/* Features Overview */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center space-x-3 mb-4">
              <Zap className="w-8 h-8 text-yellow-500" />
              <h3 className="text-lg font-semibold">Batch Processing</h3>
            </div>
            <p className="text-gray-600 text-sm">
              Process multiple PDFs efficiently with automatic knowledge base creation and progress tracking.
            </p>
            <div className="mt-3 flex items-center space-x-2 text-xs text-gray-500">
              <span>✅ Batch processing</span>
              <span>✅ Progress tracking</span>
              <span>✅ Auto knowledge base</span>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center space-x-3 mb-4">
              <Brain className="w-8 h-8 text-blue-500" />
              <h3 className="text-lg font-semibold">Bedrock AI</h3>
            </div>
            <p className="text-gray-600 text-sm">
              Enhanced Q&A powered by AWS Bedrock with content guardrails and intelligent document search.
            </p>
            <div className="mt-3 flex items-center space-x-2 text-xs text-gray-500">
              <span>✅ Advanced AI</span>
              <span>✅ Content filtering</span>
              <span>✅ Smart search</span>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center space-x-3 mb-4">
              <FileText className="w-8 h-8 text-green-500" />
              <h3 className="text-lg font-semibold">Document Management</h3>
            </div>
            <p className="text-gray-600 text-sm">
              Automatic document indexing with OpenSearch integration for fast and accurate information retrieval.
            </p>
            <div className="mt-3 flex items-center space-x-2 text-xs text-gray-500">
              <span>✅ Auto indexing</span>
              <span>✅ Fast search</span>
              <span>✅ Source tracking</span>
            </div>
          </div>
        </div>

        {/* Backend Integration Status */}
        {systemStatus && (
          <div className="mt-8 bg-white p-6 rounded-lg shadow-sm border">
            <h3 className="text-lg font-semibold mb-4">System Integration Status</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className={`w-3 h-3 rounded-full mx-auto mb-2 ${
                  systemStatus.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                }`} />
                <div className="text-sm font-medium">Backend API</div>
                <div className="text-xs text-gray-500">
                  {systemStatus.status === 'healthy' ? 'Connected' : 'Disconnected'}
                </div>
              </div>
              
              <div className="text-center">
                <div className="w-3 h-3 rounded-full bg-green-500 mx-auto mb-2" />
                <div className="text-sm font-medium">OpenSearch</div>
                <div className="text-xs text-gray-500">Ready</div>
              </div>
              
              <div className="text-center">
                <div className="w-3 h-3 rounded-full bg-green-500 mx-auto mb-2" />
                <div className="text-sm font-medium">S3 Storage</div>
                <div className="text-xs text-gray-500">Available</div>
              </div>
              
              <div className="text-center">
                <div className="w-3 h-3 rounded-full bg-yellow-500 mx-auto mb-2" />
                <div className="text-sm font-medium">Bedrock Models</div>
                <div className="text-xs text-gray-500">Enable in Console</div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-500">
              © 2024 NCDHHS PDF Q&A Assistant v2.0 - Enhanced with AWS Bedrock
            </div>
            <div className="flex items-center space-x-4 text-sm text-gray-500">
              <span>Powered by:</span>
              <span className="flex items-center space-x-1">
                <Brain className="w-4 h-4" />
                <span>AWS Bedrock</span>
              </span>
              <span>•</span>
              <span>OpenSearch</span>
              <span>•</span>
              <span>React</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
