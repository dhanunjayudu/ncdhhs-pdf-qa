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
  const [processingMode, setProcessingMode] = useState('async');
  const [maxPdfs, setMaxPdfs] = useState(50);
  const [currentJob, setCurrentJob] = useState(null);
  const [progress, setProgress] = useState(null);
  const [websocket, setWebsocket] = useState(null);
  const [jobHistory, setJobHistory] = useState([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  const wsRef = useRef(null);

  // WebSocket connection for real-time updates
  const connectWebSocket = (jobId) => {
    const wsUrl = `${API_URL.replace('http', 'ws')}/ws/progress/${jobId}`;
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      setWebsocket(ws);
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('WebSocket message:', data);
      
      if (data.type) {
        // Handle different message types
        switch (data.type) {
          case 'started':
            setProgress({
              current: 0,
              total: data.total,
              percentage: 0,
              message: data.message,
              status: 'processing'
            });
            break;
          case 'progress':
            setProgress({
              current: data.current,
              total: data.total,
              percentage: data.percentage,
              message: data.message,
              processed: data.processed,
              failed: data.failed,
              latest_result: data.latest_result
            });
            break;
          case 'completed':
            setProgress({
              current: data.total,
              total: data.total,
              percentage: 100,
              message: data.message,
              processed: data.processed,
              failed: data.failed,
              status: 'completed'
            });
            setIsProcessing(false);
            break;
        }
      } else {
        // Handle regular status updates
        setProgress({
          current: data.processed + data.failed,
          total: data.total,
          percentage: data.percentage,
          processed: data.processed,
          failed: data.failed,
          status: data.status
        });
        
        if (data.status === 'completed' || data.status === 'completed_with_errors') {
          setIsProcessing(false);
        }
      }
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setWebsocket(null);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    wsRef.current = ws;
    return ws;
  };

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Poll job status for non-WebSocket updates
  const pollJobStatus = async (jobId) => {
    try {
      const response = await axios.get(`${API_URL}/job-status/${jobId}`);
      const jobData = response.data;
      
      setProgress({
        current: jobData.progress.processed + jobData.progress.failed,
        total: jobData.progress.total,
        percentage: jobData.progress.percentage,
        processed: jobData.progress.processed,
        failed: jobData.progress.failed,
        status: jobData.status
      });
      
      if (jobData.status === 'completed' || jobData.status === 'completed_with_errors') {
        setIsProcessing(false);
        if (jobData.results && jobData.results.length > 0) {
          onDocumentsProcessed(jobData.results.filter(r => r.status === 'success'));
        }
        return false; // Stop polling
      }
      
      return true; // Continue polling
    } catch (error) {
      console.error('Error polling job status:', error);
      return false;
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;

    setIsProcessing(true);
    setProgress(null);
    setCurrentJob(null);
    onProcessingStatus('Starting PDF extraction...');

    try {
      // First, extract PDF links to show count
      const linksResponse = await axios.post(`${API_URL}/extract-pdf-links`, {
        url: url.trim()
      });

      const pdfCount = linksResponse.data.count;
      onProcessingStatus(`Found ${pdfCount} PDF files. Starting processing...`);

      // Start processing
      const response = await axios.post(`${API_URL}/process-website-async`, {
        url: url.trim(),
        max_pdfs: maxPdfs,
        processing_mode: processingMode
      });

      const jobData = response.data;
      setCurrentJob(jobData);

      // Add to job history
      setJobHistory(prev => [{
        id: jobData.job_id,
        url: url.trim(),
        status: jobData.status,
        totalPdfs: jobData.total_pdfs || pdfCount,
        createdAt: new Date().toISOString(),
        processingMode: jobData.processing_mode
      }, ...prev.slice(0, 4)]); // Keep last 5 jobs

      if (jobData.processing_mode === 'sync') {
        // Handle synchronous response
        setProgress({
          current: jobData.results?.length || 0,
          total: jobData.total_pdfs || pdfCount,
          percentage: 100,
          processed: jobData.processed || 0,
          failed: jobData.failed || 0,
          status: 'completed'
        });
        setIsProcessing(false);
        
        if (jobData.results) {
          onDocumentsProcessed(jobData.results.filter(r => r.status === 'success'));
        }
      } else {
        // Handle asynchronous response
        onProcessingStatus(`Processing ${jobData.total_pdfs} PDFs asynchronously...`);
        
        // Connect WebSocket for real-time updates
        connectWebSocket(jobData.job_id);
        
        // Fallback polling in case WebSocket fails
        const pollInterval = setInterval(async () => {
          const shouldContinue = await pollJobStatus(jobData.job_id);
          if (!shouldContinue) {
            clearInterval(pollInterval);
          }
        }, 3000);
      }

    } catch (error) {
      console.error('Error processing website:', error);
      setIsProcessing(false);
      onProcessingStatus(`Error: ${error.response?.data?.detail || error.message}`);
    }
  };

  const cancelJob = async () => {
    if (currentJob?.job_id) {
      try {
        await axios.delete(`${API_URL}/job/${currentJob.job_id}`);
        setIsProcessing(false);
        setProgress(null);
        setCurrentJob(null);
        onProcessingStatus('Job cancelled');
        
        if (wsRef.current) {
          wsRef.current.close();
        }
      } catch (error) {
        console.error('Error cancelling job:', error);
      }
    }
  };

  const ProgressBar = ({ progress }) => {
    if (!progress) return null;

    const getStatusColor = () => {
      if (progress.status === 'completed') return 'bg-green-500';
      if (progress.failed > 0) return 'bg-yellow-500';
      return 'bg-blue-500';
    };

    const getStatusIcon = () => {
      if (progress.status === 'completed') return <CheckCircle className="w-5 h-5 text-green-500" />;
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
          <span>✅ Processed: {progress.processed || 0}</span>
          {progress.failed > 0 && <span>❌ Failed: {progress.failed}</span>}
          <span>📄 Total: {progress.total}</span>
        </div>
        
        {progress.latest_result && (
          <div className="mt-2 text-xs text-gray-500">
            Latest: {progress.latest_result.url?.split('/').pop()}
          </div>
        )}
      </div>
    );
  };

  const JobHistoryItem = ({ job }) => (
    <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
      <div className="flex-1">
        <div className="text-sm font-medium truncate">{job.url}</div>
        <div className="text-xs text-gray-500">
          {job.totalPdfs} PDFs • {job.processingMode} • {new Date(job.createdAt).toLocaleTimeString()}
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
                      <option value="async">🚀 Async (Recommended for large batches)</option>
                      <option value="sync">⚡ Sync (For small batches &lt;5 PDFs)</option>
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
                  💡 Async mode provides real-time progress updates and handles large batches efficiently
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

            {isProcessing && (
              <button
                type="button"
                onClick={cancelJob}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 flex items-center space-x-2"
              >
                <X className="w-4 h-4" />
                <span>Cancel</span>
              </button>
            )}
          </div>
        </form>

        {/* Progress Display */}
        <ProgressBar progress={progress} />

        {/* Current Job Info */}
        {currentJob && (
          <div className="mt-4 p-3 bg-blue-50 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">Job ID: {currentJob.job_id}</div>
                <div className="text-xs text-gray-600">
                  Mode: {currentJob.processing_mode} • 
                  {currentJob.estimated_time_minutes && ` Est. ${currentJob.estimated_time_minutes} min`}
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm font-medium">{currentJob.total_pdfs} PDFs</div>
                <div className="text-xs text-gray-600">{currentJob.status}</div>
              </div>
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

export default EnhancedPDFProcessor;
