import React, { useState, useEffect, useCallback } from 'react';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com';

function App() {
  const [url, setUrl] = useState('');
  const [maxDepth, setMaxDepth] = useState(2);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState(null);
  const [apiInfo, setApiInfo] = useState(null);
  const [knowledgeBaseStatus, setKnowledgeBaseStatus] = useState(null);
  const [detailedStatus, setDetailedStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [syncLoading, setSyncLoading] = useState(false);

  // Define all functions first using useCallback
  const fetchApiInfo = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/`);
      const data = await response.json();
      setApiInfo(data);
    } catch (error) {
      console.error('Error fetching API info:', error);
      setApiInfo({ 
        message: 'NCDHHS PDF Q&A API', 
        version: '4.0.0', 
        status: 'Connected',
        knowledge_base_id: 'EJRS8I2F6J'
      });
    }
  }, []);

  const fetchDetailedStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/detailed-status`);
      const data = await response.json();
      setDetailedStatus(data);
      
      // Also update knowledgeBaseStatus from detailed status data
      if (data.knowledge_base && data.data_source) {
        setKnowledgeBaseStatus({
          knowledge_base: data.knowledge_base,
          data_source: data.data_source,
          recent_ingestion_jobs: data.recent_ingestion_jobs || [],
          s3_bucket: data.s3_status?.bucket || 'ncdhhs-pdf-qa-dev-bedrock-kb-f04187f9'
        });
      }
    } catch (error) {
      console.error('Error fetching detailed status:', error);
      setDetailedStatus(null);
      // Fallback knowledge base status
      setKnowledgeBaseStatus({
        knowledge_base: { id: 'EJRS8I2F6J', status: 'ACTIVE' },
        data_source: { id: 'PGYK8O2WDY', status: 'AVAILABLE' },
        s3_bucket: 'ncdhhs-pdf-qa-dev-bedrock-kb-f04187f9'
      });
    }
  }, []);

  const fetchProcessingStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/processing-status`);
      const data = await response.json();
      setProcessingStatus(data);
      
      if (data.status === 'completed' || data.status === 'failed' || data.status === 'completed_with_warnings') {
        setProcessing(false);
        setTimeout(() => {
          fetchDetailedStatus(); // This will update both detailed status and knowledge base status
        }, 2000);
      }
    } catch (error) {
      console.error('Error fetching processing status:', error);
    }
  }, [fetchDetailedStatus]);

  const handleManualSync = async () => {
    setSyncLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/trigger-sync`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      alert(`Sync started successfully! Job ID: ${data.job_id}`);
      
      // Refresh status after a short delay
      setTimeout(() => {
        fetchDetailedStatus(); // This will update both detailed status and knowledge base status
      }, 2000);
    } catch (error) {
      console.error('Error triggering sync:', error);
      alert('Error starting sync: ' + error.message);
    } finally {
      setSyncLoading(false);
    }
  };

  const handleClearStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/clear-processing-status`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Refresh status
      fetchProcessingStatus();
      fetchDetailedStatus();
    } catch (error) {
      console.error('Error clearing status:', error);
      alert('Error clearing status: ' + error.message);
    }
  };

  // Fetch API information on component mount
  useEffect(() => {
    fetchApiInfo();
    fetchDetailedStatus(); // This will also populate knowledge base status
  }, [fetchApiInfo, fetchDetailedStatus]);

  // Poll processing status when processing is active
  useEffect(() => {
    let interval;
    if (processing) {
      interval = setInterval(fetchProcessingStatus, 2000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [processing, fetchProcessingStatus]);

  const handleProcessPDFs = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;

    setProcessing(true);
    setProcessingStatus(null);

    try {
      // First check if the endpoint exists
      const healthResponse = await fetch(`${API_BASE_URL}/health`);
      if (!healthResponse.ok) {
        throw new Error('Backend service is not available');
      }

      const response = await fetch(`${API_BASE_URL}/process-and-upload-pdfs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: url,
          max_depth: maxDepth,
        }),
      });

      if (response.status === 404) {
        throw new Error('PDF processing endpoint not available. The backend may still be deploying. Please wait a few minutes and try again.');
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Processing started:', data);
    } catch (error) {
      console.error('Error starting PDF processing:', error);
      setProcessing(false);
      
      if (error.message.includes('404') || error.message.includes('not available')) {
        alert('⚠️ PDF Processing Feature Not Ready\n\nThe backend is still deploying the new features. Please:\n1. Wait 2-3 minutes for deployment to complete\n2. Try the Q&A feature instead (it should work)\n3. Refresh the page and try again\n\nError: ' + error.message);
      } else {
        alert('Error starting PDF processing: ' + error.message);
      }
    }
  };

  const handleAskQuestion = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setAnswer('');
    setSources([]);

    try {
      const response = await fetch(`${API_BASE_URL}/ask-question`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          max_results: 5,
        }),
      });

      if (response.status === 404) {
        throw new Error('Q&A endpoint not available. The backend may still be deploying.');
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setAnswer(data.answer);
      setSources(data.sources || []);
    } catch (error) {
      console.error('Error asking question:', error);
      
      if (error.message.includes('404')) {
        setAnswer('⚠️ Q&A Feature Not Ready\n\nThe backend is still deploying. Please wait 2-3 minutes and try again.\n\nIn the meantime, you can check the Knowledge Base status above to see if it shows "ACTIVE".');
      } else {
        setAnswer('Error: ' + error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>NCDHHS PDF Q&A System</h1>
        <p>Powered by AWS Bedrock Knowledge Base</p>
        
        {apiInfo && (
          <div className="api-info">
            <p><strong>Version:</strong> {apiInfo.version}</p>
            <p><strong>Status:</strong> {apiInfo.status}</p>
            <p><strong>Knowledge Base ID:</strong> {apiInfo.knowledge_base_id}</p>
          </div>
        )}
      </header>

      <main className="App-main">
        {/* Knowledge Base Status */}
        {knowledgeBaseStatus && (
          <section className="knowledge-base-status">
            <h2>Knowledge Base Status</h2>
            <div className="status-grid">
              <div className="status-item">
                <strong>Knowledge Base:</strong> {knowledgeBaseStatus.knowledge_base?.status || 'ACTIVE'}
              </div>
              <div className="status-item">
                <strong>Data Source:</strong> {knowledgeBaseStatus.data_source?.status || 'AVAILABLE'}
              </div>
              <div className="status-item">
                <strong>S3 Bucket:</strong> {knowledgeBaseStatus.s3_bucket}
              </div>
              <div className="status-item">
                <strong>Recent Jobs:</strong> {knowledgeBaseStatus.recent_ingestion_jobs?.length || 0}
              </div>
            </div>
          </section>
        )}

        {/* Detailed Status Dashboard */}
        {detailedStatus && (
          <section className="detailed-status">
            <div className="status-header">
              <h2>System Status Dashboard</h2>
              <button 
                onClick={fetchDetailedStatus} 
                className="refresh-btn"
                disabled={loading}
              >
                🔄 Refresh
              </button>
            </div>
            
            {/* Pipeline Status */}
            <div className="pipeline-status">
              <h3>Processing Pipeline</h3>
              <div className="pipeline-steps">
                <div className={`pipeline-step ${detailedStatus.s3_status.document_count > 0 ? 'completed' : 'pending'}`}>
                  <div className="step-number">1</div>
                  <div className="step-content">
                    <h4>📁 S3 Storage</h4>
                    <p><strong>{detailedStatus.s3_status.document_count}</strong> documents uploaded</p>
                    <p className="step-detail">
                      {detailedStatus.s3_status.document_count > 0 
                        ? `${(detailedStatus.s3_status.total_size_bytes / 1024 / 1024).toFixed(2)} MB total`
                        : 'No documents uploaded yet'
                      }
                    </p>
                  </div>
                </div>

                <div className={`pipeline-step ${
                  detailedStatus.sync_status.status === 'synced' ? 'completed' :
                  detailedStatus.sync_status.status === 'syncing' ? 'in-progress' :
                  detailedStatus.sync_status.status === 'failed' ? 'failed' : 'pending'
                }`}>
                  <div className="step-number">2</div>
                  <div className="step-content">
                    <h4>🔄 Knowledge Base Sync</h4>
                    <p><strong>{detailedStatus.sync_status.status.toUpperCase()}</strong></p>
                    <p className="step-detail">{detailedStatus.sync_status.message}</p>
                    {detailedStatus.sync_status.last_sync_time && (
                      <p className="step-time">
                        Last sync: {new Date(detailedStatus.sync_status.last_sync_time).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>

                <div className={`pipeline-step ${
                  detailedStatus.knowledge_base.status === 'ACTIVE' ? 'completed' : 'pending'
                }`}>
                  <div className="step-number">3</div>
                  <div className="step-content">
                    <h4>🧠 AI Ready</h4>
                    <p><strong>{detailedStatus.knowledge_base.status}</strong></p>
                    <p className="step-detail">
                      {detailedStatus.knowledge_base.status === 'ACTIVE' 
                        ? 'Ready to answer questions'
                        : 'Knowledge Base not ready'
                      }
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Ingestion Job Status */}
            {detailedStatus.latest_ingestion_job && (
              <div className="ingestion-status">
                <h3>Latest Ingestion Job</h3>
                <div className="job-details">
                  <div className="job-header">
                    <span className={`job-status ${detailedStatus.latest_ingestion_job.status?.toLowerCase()}`}>
                      {detailedStatus.latest_ingestion_job.status}
                    </span>
                    <span className="job-id">ID: {detailedStatus.latest_ingestion_job.ingestionJobId}</span>
                  </div>
                  
                  {detailedStatus.latest_ingestion_job.statistics && (
                    <div className="job-stats">
                      <div className="stat-item">
                        <strong>Scanned:</strong> {detailedStatus.latest_ingestion_job.statistics.numberOfDocumentsScanned}
                      </div>
                      <div className="stat-item">
                        <strong>Indexed:</strong> {detailedStatus.latest_ingestion_job.statistics.numberOfNewDocumentsIndexed}
                      </div>
                      <div className="stat-item">
                        <strong>Failed:</strong> {detailedStatus.latest_ingestion_job.statistics.numberOfDocumentsFailed}
                      </div>
                    </div>
                  )}
                  
                  <div className="job-times">
                    <p><strong>Started:</strong> {new Date(detailedStatus.latest_ingestion_job.startedAt).toLocaleString()}</p>
                    {detailedStatus.latest_ingestion_job.updatedAt && (
                      <p><strong>Updated:</strong> {new Date(detailedStatus.latest_ingestion_job.updatedAt).toLocaleString()}</p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Manual Sync Button */}
            <div className="manual-sync">
              <button 
                onClick={handleManualSync} 
                disabled={syncLoading || detailedStatus.sync_status.status === 'syncing'}
                className="sync-btn"
              >
                {syncLoading ? '🔄 Starting Sync...' : 
                 detailedStatus.sync_status.status === 'syncing' ? '⏳ Sync in Progress' : 
                 '🚀 Trigger Manual Sync'}
              </button>
              <p className="sync-help">
                Use this if documents were uploaded but Knowledge Base is not in sync
              </p>
            </div>

            {/* Recent Documents */}
            {detailedStatus.s3_status.documents && detailedStatus.s3_status.documents.length > 0 && (
              <div className="recent-documents">
                <h3>Recent Documents in S3</h3>
                <div className="documents-list">
                  {detailedStatus.s3_status.documents.slice(0, 5).map((doc, index) => (
                    <div key={index} className="document-item">
                      <div className="doc-name">{doc.filename}</div>
                      <div className="doc-details">
                        <span className="doc-size">{(doc.size / 1024).toFixed(1)} KB</span>
                        <span className="doc-date">{new Date(doc.last_modified).toLocaleDateString()}</span>
                      </div>
                    </div>
                  ))}
                  {detailedStatus.s3_status.documents.length > 5 && (
                    <p className="more-docs">... and {detailedStatus.s3_status.documents.length - 5} more documents</p>
                  )}
                </div>
              </div>
            )}
          </section>
        )}

        {/* PDF Processing Section */}
        <section className="pdf-processing">
          <h2>Process PDF Documents</h2>
          <form onSubmit={handleProcessPDFs}>
            <div className="form-group">
              <label htmlFor="url">Website URL:</label>
              <input
                type="url"
                id="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com"
                required
                disabled={processing}
              />
            </div>
            <div className="form-group">
              <label htmlFor="maxDepth">Max Depth:</label>
              <select
                id="maxDepth"
                value={maxDepth}
                onChange={(e) => setMaxDepth(parseInt(e.target.value))}
                disabled={processing}
              >
                <option value={1}>1 (Current page only)</option>
                <option value={2}>2 (Current + linked pages)</option>
                <option value={3}>3 (Deep crawl)</option>
              </select>
            </div>
            <button type="submit" disabled={processing}>
              {processing ? 'Processing...' : 'Process PDFs'}
            </button>
          </form>

          {/* Processing Status */}
          {processingStatus && (
            <div className="processing-status">
              <div className="status-header">
                <h3>Processing Status</h3>
                {processingStatus.status === 'completed' && (
                  <button 
                    onClick={handleClearStatus}
                    className="clear-status-btn"
                    title="Clear completed status"
                  >
                    ✕ Clear
                  </button>
                )}
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${processingStatus.progress}%` }}
                ></div>
              </div>
              <p><strong>Status:</strong> {processingStatus.status}</p>
              <p><strong>Progress:</strong> {processingStatus.progress}%</p>
              <p><strong>Message:</strong> {processingStatus.message}</p>
              <p><strong>Processed:</strong> {processingStatus.processed_count} / {processingStatus.total_count}</p>
              {processingStatus.current_url && (
                <p><strong>Current:</strong> {processingStatus.current_url}</p>
              )}
              {processingStatus.errors && processingStatus.errors.length > 0 && (
                <div className="errors">
                  <h4>Errors:</h4>
                  <ul>
                    {processingStatus.errors.map((error, index) => (
                      <li key={index}>{error}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Q&A Section */}
        <section className="qa-section">
          <h2>Ask Questions</h2>
          <form onSubmit={handleAskQuestion}>
            <div className="form-group">
              <label htmlFor="question">Your Question:</label>
              <textarea
                id="question"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="What services does NCDHHS provide?"
                rows={3}
                required
              />
            </div>
            <button type="submit" disabled={loading}>
              {loading ? 'Asking...' : 'Ask Question'}
            </button>
          </form>

          {/* Answer Display */}
          {answer && (
            <div className="answer-section">
              <h3>Answer</h3>
              <div className="answer-content">
                <p>{answer}</p>
              </div>

              {/* Sources */}
              {sources.length > 0 && (
                <div className="sources-section">
                  <h4>Sources</h4>
                  {sources.map((source, index) => (
                    <div key={index} className="source-item">
                      <div className="source-header">
                        <strong>Source {index + 1}</strong>
                        <span className="confidence">
                          Confidence: {((source.score || 0) * 100).toFixed(1)}%
                        </span>
                      </div>
                      <p className="source-uri">{source.uri}</p>
                      <p className="source-excerpt">{source.excerpt}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
