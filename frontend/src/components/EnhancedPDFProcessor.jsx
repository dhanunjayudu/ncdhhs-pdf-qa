import React, { useState, useEffect, useRef } from 'react';
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
  Pause,
  Play,
  X
} from 'lucide-react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const EnhancedPDFProcessor = ({ onDocumentsProcessed, onProcessingStatus }) => {
  const [url, setUrl] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingMode, setProcessingMode] = useState('batch');
  const [maxPdfs, setMaxPdfs] = useState(50);
  const [progress, setProgress] = useState(null);
  const [jobHistory, setJobHistory] = useState([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [currentStep, setCurrentStep] = useState('');
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;

    setIsProcessing(true);
    setProgress(null);
    setCurrentStep('Extracting PDF links...');
    onProcessingStatus('Starting PDF extraction...');

    try {
      // Step 1: Extract PDF links
      const linksResponse = await axios.post(`${API_URL}/extract-pdf-links`, {
        url: url.trim()
      });

      const pdfLinks = linksResponse.data.pdf_links || [];
      const pdfCount = pdfLinks.length;
      
      if (pdfCount === 0) {
        throw new Error('No PDF files found on the website');
      }

      setCurrentStep(`Found ${pdfCount} PDFs. Processing...`);
      onProcessingStatus(`Found ${pdfCount} PDF files. Starting processing...`);

      // Limit PDFs if requested
      const linksToProcess = maxPdfs && pdfCount > maxPdfs ? pdfLinks.slice(0, maxPdfs) : pdfLinks;
      
      setProgress({
        current: 0,
        total: linksToProcess.length,
        percentage: 0,
        processed: 0,
        failed: 0,
        status: 'processing'
      });

      // Step 2: Process PDFs in batch
      const batchResponse = await axios.post(`${API_URL}/process-pdf-batch`, {
        pdf_urls: linksToProcess
      });

      const processedDocs = batchResponse.data.processed_documents || [];
      const successCount = processedDocs.filter(doc => doc.status === 'success').length;
      const failedCount = processedDocs.length - successCount;

      setProgress({
        current: processedDocs.length,
        total: linksToProcess.length,
        percentage: 100,
        processed: successCount,
        failed: failedCount,
        status: 'completed'
      });

      setCurrentStep(`Processing completed: ${successCount} successful, ${failedCount} failed`);
      onProcessingStatus(`Processing completed: ${successCount} successful, ${failedCount} failed`);

      // Step 3: Create knowledge base if we have successful documents
      if (successCount > 0) {
        setCurrentStep('Creating knowledge base...');
        onProcessingStatus('Creating knowledge base...');

        try {
          await axios.post(`${API_URL}/create-knowledge-base`, {
            documents: processedDocs.filter(doc => doc.status === 'success')
          });
          
          setCurrentStep('Knowledge base created successfully');
          onProcessingStatus('Knowledge base created successfully');
        } catch (kbError) {
          console.warn('Knowledge base creation failed:', kbError);
          setCurrentStep('Documents processed (knowledge base creation failed)');
          onProcessingStatus('Documents processed (knowledge base creation failed)');
        }

        // Pass successful documents to parent
        onDocumentsProcessed(processedDocs.filter(doc => doc.status === 'success'));
      }

      // Add to job history
      setJobHistory(prev => [{
        id: Date.now(),
        url: url.trim(),
        status: 'completed',
        totalPdfs: linksToProcess.length,
        processed: successCount,
        failed: failedCount,
        createdAt: new Date().toISOString(),
        processingMode: processingMode
      }, ...prev.slice(0, 4)]); // Keep last 5 jobs

    } catch (error) {
      console.error('Error processing website:', error);
      setCurrentStep(`Error: ${error.message}`);
      onProcessingStatus(`Error: ${error.response?.data?.detail || error.message}`);
      
      setProgress({
        current: 0,
        total: 0,
        percentage: 0,
        processed: 0,
        failed: 0,
        status: 'failed'
      });
    } finally {
      setIsProcessing(false);
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
              {currentStep || `Processing ${progress.current}/${progress.total} PDFs`}
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
          <span>✅ Processed: {progress.processed || 0}</span>
          {progress.failed > 0 && <span>❌ Failed: {progress.failed}</span>}
          <span>📄 Total: {progress.total}</span>
        </div>
      </div>
    );
  };

  const JobHistoryItem = ({ job }) => (
    <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
      <div className="flex-1">
        <div className="text-sm font-medium truncate">{job.url}</div>
        <div className="text-xs text-gray-500">
          {job.totalPdfs} PDFs • {job.processed} processed • {new Date(job.createdAt).toLocaleTimeString()}
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
          <FileText className="w-6 h-6 text-blue-600" />
          <h2 className="text-xl font-semibold">Enhanced PDF Processor</h2>
          <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">v2.0</span>
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
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Processing Mode
                    </label>
                    <select
                      value={processingMode}
                      onChange={(e) => setProcessingMode(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                      disabled={isProcessing}
                    >
                      <option value="batch">📦 Batch Processing (Recommended)</option>
                      <option value="sequential">🔄 Sequential Processing</option>
                    </select>
                  </div>

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
                </div>

                <div className="text-xs text-gray-500">
                  💡 Batch processing handles multiple PDFs efficiently and creates a knowledge base automatically
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
                  <Zap className="w-4 h-4" />
                  <span>Process Website</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Progress Display */}
        <ProgressBar progress={progress} />
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

export default EnhancedPDFProcessor;
