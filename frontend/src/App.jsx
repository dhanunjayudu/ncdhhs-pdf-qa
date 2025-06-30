import React, { useState, useEffect } from 'react';
import { FileText, Download, MessageCircle, Loader2, AlertCircle } from 'lucide-react';
import PDFProcessor from './components/PDFProcessor';
import ChatInterface from './components/ChatInterface';
import DocumentList from './components/DocumentList';

function App() {
  const [documents, setDocuments] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState('process');
  const [processingStatus, setProcessingStatus] = useState('');

  const handleDocumentsProcessed = (processedDocs) => {
    setDocuments(processedDocs);
    setActiveTab('chat');
  };

  const handleProcessingStatus = (status) => {
    setProcessingStatus(status);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <FileText className="h-8 w-8 text-primary-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  NC DHHS Child Welfare Q&A Assistant
                </h1>
                <p className="text-sm text-gray-600">
                  AI-powered document analysis and question answering
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-500">
                {documents.length} documents processed
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            <button
              onClick={() => setActiveTab('process')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'process'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Download className="inline h-4 w-4 mr-2" />
              Process Documents
            </button>
            <button
              onClick={() => setActiveTab('chat')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'chat'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
              disabled={documents.length === 0}
            >
              <MessageCircle className="inline h-4 w-4 mr-2" />
              Ask Questions
            </button>
            <button
              onClick={() => setActiveTab('documents')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'documents'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <FileText className="inline h-4 w-4 mr-2" />
              Documents ({documents.length})
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Processing Status */}
        {isProcessing && (
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center">
              <Loader2 className="h-5 w-5 text-blue-600 animate-spin mr-3" />
              <div>
                <p className="text-blue-800 font-medium">Processing Documents</p>
                <p className="text-blue-600 text-sm">{processingStatus}</p>
              </div>
            </div>
          </div>
        )}

        {/* Tab Content */}
        {activeTab === 'process' && (
          <PDFProcessor
            onDocumentsProcessed={handleDocumentsProcessed}
            onProcessingStatus={handleProcessingStatus}
            setIsProcessing={setIsProcessing}
          />
        )}

        {activeTab === 'chat' && documents.length > 0 && (
          <ChatInterface documents={documents} />
        )}

        {activeTab === 'chat' && documents.length === 0 && (
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No Documents Processed
            </h3>
            <p className="text-gray-600 mb-4">
              Please process some documents first before asking questions.
            </p>
            <button
              onClick={() => setActiveTab('process')}
              className="btn-primary"
            >
              Process Documents
            </button>
          </div>
        )}

        {activeTab === 'documents' && (
          <DocumentList documents={documents} />
        )}
      </main>
    </div>
  );
}

export default App;
