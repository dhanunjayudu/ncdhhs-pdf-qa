import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Download, 
  Loader2, 
  AlertCircle, 
  CheckCircle, 
  XCircle, 
  Clock,
  Zap,
  BarChart3,
  Upload,
  Database
} from 'lucide-react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const SimplifiedPDFProcessor = ({ onDocumentsProcessed, onProcessingStatus }) => {
  const [url, setUrl] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [maxPdfs, setMaxPdfs] = useState(50);
  const [progress, setProgress] = useState(null);
  const [jobHistory, setJobHistory] = useState([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [processingStep, setProcessingStep] = useState('');
  const [knowledgeBaseStatus, setKnowledgeBaseStatus] = useState(null);
  
  // Poll processing status when processing
  useEffect(() => {
    let interval;
    if (isProcessing) {
      interval = setInterval(async () => {
        try {
          const response = await axios.get(`${API_URL}/processing-status`);
          const status = response.data;
          
          if (status.status !== 'idle') {
            setProgress({
              current: status.processed + status.failed,
              total: status.total,
              percentage: status.total > 0 ? ((status.processed + status.failed) / status.total) * 100 : 0,
              processed: status.processed,
              failed: status.failed,
              status: status.status,
              message: status.message
            });
            
            setProcessingStep(status.message);
            onProcessingStatus(status.message);
            
            if (status.status === 'completed' || status.status === 'failed') {
              setIsProcessing(false);
              if (status.status === 'completed' && status.processed > 0) {
                // Trigger knowledge base sync status check
                checkKnowledgeBaseStatus();
                // Notify parent of successful processing
                onDocumentsProcessed([{ count: status.processed }]);
              }
            }
          }
        } catch (error) {
          console.error('Error polling status:', error);
        }
      }, 2000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isProcessing, onDocumentsProcessed, onProcessingStatus]);

  // Check knowledge base status on mount
  useEffect(() => {
    checkKnowledgeBaseStatus();
  }, []);

  const checkKnowledgeBaseStatus = async () => {
    try {
      const response = await axios.get(`${API_URL}/knowledge-base/status`);
      setKnowledgeBaseStatus(response.data);
    } catch (error) {
      console.error('Error checking knowledge base status:', error);
      setKnowledgeBaseStatus({ status: 'error', message: 'Unable to check status' });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;

    setIsProcessing(true);
    setProgress(null);
    setProcessingStep('Starting PDF extraction...');
    onProcessingStatus('Starting PDF extraction...');

    try {
      // Start the simplified processing
      const response = await axios.post(`${API_URL}/process-and-upload-pdfs`, {
        url: url.trim(),
        max_pdfs: maxPdfs
      });

      // Add to job history
      setJobHistory(prev => [{
        id: Date.now(),
        url: url.trim(),
        status: response.data.status,
        totalPdfs: response.data.total,
        processed: response.data.processed,
        failed: response.data.failed,
        createdAt: new Date().toISOString()
      }, ...prev.slice(0, 4)]); // Keep last 5 jobs

      // If processing completed immediately (small batch)
      if (response.data.status === 'completed') {
        setProgress({
          current: response.data.total,
          total: response.data.total,
          percentage: 100,
          processed: response.data.processed,
          failed: response.data.failed,
          status: 'completed',
          message: response.data.message
        });
        
        setProcessingStep(response.data.message);
        onProcessingStatus(response.data.message);
        setIsProcessing(false);
        
        if (response.data.processed > 0) {
          onDocumentsProcessed([{ count: response.data.processed }]);
          checkKnowledgeBaseStatus();
        }
      }

    } catch (error) {
      console.error('Error processing website:', error);
      setIsProcessing(false);
      setProcessingStep(`Error: ${error.response?.data?.detail || error.message}`);
      onProcessingStatus(`Error: ${error.response?.data?.detail || error.message}`);
      
      setProgress({
        current: 0,
        total: 0,
        percentage: 0,
        processed: 0,
        failed: 0,
        status: 'failed',
        message: error.response?.data?.detail || error.message
      });
    }
  };

  const syncKnowledgeBase = async () => {
    try {
      setProcessingStep('Syncing knowledge base...');
      const response = await axios.post(`${API_URL}/sync-knowledge-base`);
      setProcessingStep(`Knowledge base sync: ${response.data.message}`);
      checkKnowledgeBaseStatus();
    } catch (error) {
      console.error('Error syncing knowledge base:', error);
      setProcessingStep(`Sync error: ${error.response?.data?.detail || error.message}`);
    }
  };

  const ProgressBar = ({ progress }) => {
    if (!progress) return null;

    const getStatusColor = () => {
      if (progress.status === 'completed') return 'bg-green-500';
      if (progress.status === 'failed') return 'bg-red-500';
      if (progress.failed > 0) return 'bg-yellow-500';
      return 'bg-blue-500';
    };

    const getStatusIcon = () => {
      if (progress.status === 'completed') return <CheckCircle className="w-5 h-5 text-green-500" />;
      if (progress.status === 'failed') return <XCircle className="w-5 h-5 text-red-500" />;
      if (progress.failed > 0) return <AlertCircle className="w-5 h-5 text-yellow-500" />;
      return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
    };

    return (
      <div className="mt-4 p-4 bg-gray-50 rounded-lg">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            {getStatusIcon()}
            <span className="font-medium">
              {progress.message || `Processing ${progress.current}/${progress.total} PDFs`}
            </span>
          </div>
          <span className="text-sm text-gray-600">
            {Math.round(progress.percentage)}%
          </span>
        </div>
        
        <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
          <div 
            className={`h-2 rounded-full transition-all duration-300 ${getStatusColor()}`}
            style={{ width: `${progress.percentage}%` }}
          />
        </div>
        
        <div className="flex justify-between text-sm text-gray-600">
          <span>📤 Uploaded: {progress.processed || 0}</span>
          {progress.failed > 0 && <span>❌ Failed: {progress.failed}</span>}
          <span>📄 Total: {progress.total}</span>
        </div>
      </div>
    );
  };

  const KnowledgeBaseStatus = () => {
    if (!knowledgeBaseStatus) return null;

    const getStatusColor = () => {
      switch (knowledgeBaseStatus.status) {
        case 'configured': return 'text-green-600 bg-green-50 border-green-200';
        case 'not_configured': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
        case 'error': return 'text-red-600 bg-red-50 border-red-200';
        default: return 'text-gray-600 bg-gray-50 border-gray-200';
      }
    };

    const getStatusIcon = () => {
      switch (knowledgeBaseStatus.status) {
        case 'configured': return <Database className="w-4 h-4 text-green-600" />;
        case 'not_configured': return <AlertCircle className="w-4 h-4 text-yellow-600" />;
        case 'error': return <XCircle className="w-4 h-4 text-red-600" />;
        default: return <Clock className="w-4 h-4 text-gray-600" />;
      }
    };

    return (
      <div className={`mt-4 p-3 border rounded-lg ${getStatusColor()}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {getStatusIcon()}
            <span className="font-medium">Bedrock Knowledge Base</span>
          </div>
          {knowledgeBaseStatus.status === 'configured' && (
            <button
              onClick={syncKnowledgeBase}
              className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
              disabled={isProcessing}
            >
              Sync Now
            </button>
          )}
        </div>
        <div className="text-sm mt-1">
          {knowledgeBaseStatus.message || 
           (knowledgeBaseStatus.status === 'configured' ? 
            `Ready (${knowledgeBaseStatus.knowledge_base_id})` : 
            'Not configured')}
        </div>
      </div>
    );
  };

  const JobHistoryItem = ({ job }) => (
    <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
      <div className="flex-1">
        <div className="text-sm font-medium truncate">{job.url}</div>
        <div className="text-xs text-gray-500">
          {job.totalPdfs} PDFs • {job.processed} uploaded • {new Date(job.createdAt).toLocaleTimeString()}
        </div>
      </div>
      <div className="flex items-center space-x-2">
        {job.status === 'completed' ? (
          <CheckCircle className="w-4 h-4 text-green-500" />
        ) : job.status === 'failed' ? (
          <XCircle className="w-4 h-4 text-red-500" />
        ) : (
          <Clock className="w-4 h-4 text-yellow-500" />
        )}
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <div className="flex items-center space-x-2 mb-4">
          <Upload className="w-6 h-6 text-blue-600" />
          <h2 className="text-xl font-semibold">Simplified PDF Processor</h2>
          <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">S3 + Bedrock</span>
        </div>

        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="text-sm text-blue-800">
            <strong>How it works:</strong> PDFs are downloaded and uploaded directly to S3, then automatically indexed by Bedrock Knowledge Base for AI-powered Q&A.
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-2">
              Website URL
            </label>
            <input
              type="url"
              id="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
              disabled={isProcessing}
            />
          </div>

          {/* Advanced Options */}
          <div className="border-t pt-4">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center space-x-2 text-sm text-gray-600 hover:text-gray-800"
            >
              <BarChart3 className="w-4 h-4" />
              <span>Advanced Options</span>
            </button>

            {showAdvanced && (
              <div className="mt-4 space-y-4 p-4 bg-gray-50 rounded-lg">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Max PDFs to Process
                  </label>
                  <input
                    type="number"
                    value={maxPdfs}
                    onChange={(e) => setMaxPdfs(parseInt(e.target.value))}
                    min="1"
                    max="100"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                    disabled={isProcessing}
                  />
                </div>

                <div className="text-xs text-gray-500">
                  💡 PDFs are uploaded to S3 with timestamps to avoid conflicts. Bedrock Knowledge Base automatically indexes new documents.
                </div>
              </div>
            )}
          </div>

          <div className="flex space-x-3">
            <button
              type="submit"
              disabled={isProcessing || !url.trim()}
              className="flex-1 flex items-center justify-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  <span>Process & Upload to S3</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Progress Display */}
        <ProgressBar progress={progress} />

        {/* Knowledge Base Status */}
        <KnowledgeBaseStatus />

        {/* Processing Step */}
        {processingStep && (
          <div className="mt-4 p-3 bg-gray-100 rounded-lg">
            <div className="text-sm text-gray-700">
              <strong>Status:</strong> {processingStep}
            </div>
          </div>
        )}
      </div>

      {/* Job History */}
      {jobHistory.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="text-lg font-semibold mb-4 flex items-center space-x-2">
            <Clock className="w-5 h-5" />
            <span>Recent Jobs</span>
          </h3>
          <div className="space-y-2">
            {jobHistory.map((job) => (
              <JobHistoryItem key={job.id} job={job} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SimplifiedPDFProcessor;
