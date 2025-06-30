import React, { useState } from 'react';
import { Download, Globe, FileText, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const PDFProcessor = ({ onDocumentsProcessed, onProcessingStatus, setIsProcessing }) => {
  const [websiteUrl, setWebsiteUrl] = useState('https://policies.ncdhhs.gov/divisional-n-z/social-services/child-welfare-services/cws-policies-manuals/');
  const [processedDocs, setProcessedDocs] = useState([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleProcessWebsite = async () => {
    if (!websiteUrl.trim()) {
      setError('Please enter a valid website URL');
      return;
    }

    setIsLoading(true);
    setIsProcessing(true);
    setError('');
    setProcessedDocs([]);
    
    try {
      onProcessingStatus('Extracting PDF links from website...');
      
      // Step 1: Extract PDF links
      const linksResponse = await axios.post(`${API_BASE_URL}/extract-pdf-links`, {
        url: websiteUrl
      });
      
      const pdfLinks = linksResponse.data.pdf_links;
      onProcessingStatus(`Found ${pdfLinks.length} PDF documents. Starting download and processing...`);
      
      // Step 2: Process PDFs in batches
      const batchSize = 3; // Process 3 PDFs at a time to avoid overwhelming the server
      const allProcessedDocs = [];
      
      for (let i = 0; i < pdfLinks.length; i += batchSize) {
        const batch = pdfLinks.slice(i, i + batchSize);
        onProcessingStatus(`Processing batch ${Math.floor(i/batchSize) + 1}/${Math.ceil(pdfLinks.length/batchSize)} (${batch.length} documents)...`);
        
        try {
          const batchResponse = await axios.post(`${API_BASE_URL}/process-pdf-batch`, {
            pdf_links: batch
          });
          
          const batchResults = batchResponse.data.results;
          allProcessedDocs.push(...batchResults.filter(doc => doc.success));
          
          // Update UI with current progress
          setProcessedDocs([...allProcessedDocs]);
          
        } catch (batchError) {
          console.error(`Error processing batch ${Math.floor(i/batchSize) + 1}:`, batchError);
          // Continue with next batch even if one fails
        }
      }
      
      onProcessingStatus(`Processing complete! Successfully processed ${allProcessedDocs.length} documents.`);
      
      // Step 3: Create knowledge base
      if (allProcessedDocs.length > 0) {
        onProcessingStatus('Creating knowledge base for Q&A...');
        await axios.post(`${API_BASE_URL}/create-knowledge-base`, {
          documents: allProcessedDocs
        });
      }
      
      setProcessedDocs(allProcessedDocs);
      onDocumentsProcessed(allProcessedDocs);
      
    } catch (error) {
      console.error('Error processing website:', error);
      setError(error.response?.data?.detail || 'Failed to process website. Please try again.');
    } finally {
      setIsLoading(false);
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Website URL Input */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Process PDF Documents from Website
        </h2>
        
        <div className="space-y-4">
          <div>
            <label htmlFor="website-url" className="block text-sm font-medium text-gray-700 mb-2">
              Website URL
            </label>
            <div className="flex space-x-3">
              <div className="flex-1 relative">
                <Globe className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  id="website-url"
                  type="url"
                  value={websiteUrl}
                  onChange={(e) => setWebsiteUrl(e.target.value)}
                  placeholder="https://policies.ncdhhs.gov/..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  disabled={isLoading}
                />
              </div>
              <button
                onClick={handleProcessWebsite}
                disabled={isLoading || !websiteUrl.trim()}
                className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                <span>{isLoading ? 'Processing...' : 'Process Website'}</span>
              </button>
            </div>
          </div>
          
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center">
                <XCircle className="h-5 w-5 text-red-600 mr-3" />
                <p className="text-red-800">{error}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Processing Results */}
      {processedDocs.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Processing Results ({processedDocs.length} documents)
          </h3>
          
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {processedDocs.map((doc, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {doc.title}
                    </p>
                    <p className="text-xs text-gray-500">
                      {doc.pages} pages • {Math.round(doc.content?.length / 1000)}k characters
                    </p>
                  </div>
                </div>
                <FileText className="h-4 w-4 text-gray-400" />
              </div>
            ))}
          </div>
          
          {processedDocs.length > 0 && (
            <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center">
                <CheckCircle className="h-5 w-5 text-green-600 mr-3" />
                <div>
                  <p className="text-green-800 font-medium">
                    Documents processed successfully!
                  </p>
                  <p className="text-green-600 text-sm">
                    You can now ask questions about the processed documents.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Instructions */}
      <div className="card bg-blue-50 border border-blue-200">
        <h3 className="text-lg font-semibold text-blue-900 mb-3">
          How it works
        </h3>
        <div className="space-y-2 text-sm text-blue-800">
          <div className="flex items-start space-x-2">
            <span className="font-medium">1.</span>
            <span>Enter the NC DHHS website URL containing PDF documents</span>
          </div>
          <div className="flex items-start space-x-2">
            <span className="font-medium">2.</span>
            <span>The system will automatically find and download all PDF files</span>
          </div>
          <div className="flex items-start space-x-2">
            <span className="font-medium">3.</span>
            <span>PDFs are processed and indexed using AWS Bedrock</span>
          </div>
          <div className="flex items-start space-x-2">
            <span className="font-medium">4.</span>
            <span>Ask questions about the content using natural language</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PDFProcessor;
