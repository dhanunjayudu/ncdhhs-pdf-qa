import React, { useState } from 'react';
import { FileText, Search, ExternalLink, Calendar, Hash } from 'lucide-react';

const DocumentList = ({ documents }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('title');

  const filteredDocuments = documents
    .filter(doc => 
      doc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      doc.content?.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      switch (sortBy) {
        case 'title':
          return a.title.localeCompare(b.title);
        case 'pages':
          return (b.pages || 0) - (a.pages || 0);
        case 'size':
          return (b.content?.length || 0) - (a.content?.length || 0);
        default:
          return 0;
      }
    });

  const formatFileSize = (content) => {
    if (!content) return 'N/A';
    const bytes = content.length;
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + ' KB';
    return Math.round(bytes / (1024 * 1024)) + ' MB';
  };

  const truncateContent = (content, maxLength = 200) => {
    if (!content || content.length <= maxLength) return content;
    return content.substring(0, maxLength) + '...';
  };

  return (
    <div className="space-y-6">
      {/* Header and Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Document Library</h2>
          <p className="text-gray-600">
            {filteredDocuments.length} of {documents.length} documents
          </p>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 w-full sm:w-64"
            />
          </div>
          
          {/* Sort */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="title">Sort by Title</option>
            <option value="pages">Sort by Pages</option>
            <option value="size">Sort by Size</option>
          </select>
        </div>
      </div>

      {/* Document Grid */}
      {filteredDocuments.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredDocuments.map((doc, index) => (
            <div key={index} className="card hover:shadow-lg transition-shadow duration-200">
              {/* Document Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-primary-100 rounded-lg">
                    <FileText className="h-6 w-6 text-primary-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold text-gray-900 truncate">
                      {doc.title}
                    </h3>
                  </div>
                </div>
                
                {doc.url && (
                  <a
                    href={doc.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-gray-400 hover:text-primary-600 transition-colors"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                )}
              </div>

              {/* Document Stats */}
              <div className="flex items-center space-x-4 mb-4 text-sm text-gray-600">
                <div className="flex items-center space-x-1">
                  <Hash className="h-4 w-4" />
                  <span>{doc.pages || 'N/A'} pages</span>
                </div>
                <div className="flex items-center space-x-1">
                  <FileText className="h-4 w-4" />
                  <span>{formatFileSize(doc.content)}</span>
                </div>
              </div>

              {/* Document Preview */}
              {doc.content && (
                <div className="mb-4">
                  <p className="text-sm text-gray-700 leading-relaxed">
                    {truncateContent(doc.content)}
                  </p>
                </div>
              )}

              {/* Processing Info */}
              {doc.processedAt && (
                <div className="flex items-center space-x-1 text-xs text-gray-500">
                  <Calendar className="h-3 w-3" />
                  <span>
                    Processed {new Date(doc.processedAt).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {searchTerm ? 'No documents found' : 'No documents available'}
          </h3>
          <p className="text-gray-600">
            {searchTerm 
              ? `No documents match "${searchTerm}". Try a different search term.`
              : 'Process some documents first to see them here.'
            }
          </p>
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="mt-4 btn-secondary"
            >
              Clear Search
            </button>
          )}
        </div>
      )}

      {/* Summary Stats */}
      {documents.length > 0 && (
        <div className="card bg-gray-50">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Library Statistics
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-primary-600">
                {documents.length}
              </div>
              <div className="text-sm text-gray-600">Total Documents</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-primary-600">
                {documents.reduce((sum, doc) => sum + (doc.pages || 0), 0)}
              </div>
              <div className="text-sm text-gray-600">Total Pages</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-primary-600">
                {Math.round(documents.reduce((sum, doc) => sum + (doc.content?.length || 0), 0) / 1000)}K
              </div>
              <div className="text-sm text-gray-600">Characters</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-primary-600">
                {formatFileSize(documents.reduce((sum, doc) => sum + (doc.content?.length || 0), 0))}
              </div>
              <div className="text-sm text-gray-600">Total Size</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentList;
