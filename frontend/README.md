# NC DHHS PDF Q&A Assistant - Frontend

This is the React frontend for the NC DHHS PDF Q&A Assistant application. It provides a user interface for processing PDF documents and asking questions about their content.

## Features

- **Document Processing**: Extract and process PDF documents from NC DHHS websites
- **Q&A Interface**: Ask questions about processed documents using AI
- **Document Management**: View and manage processed documents
- **Real-time Processing Status**: Track document processing progress

## Environment Configuration

### Environment Variables

- `VITE_API_URL`: Backend API URL (currently: http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com)
- `VITE_APP_TITLE`: Application title
- `VITE_AWS_REGION`: AWS region for the backend services

## Development

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

```bash
npm install
```

### Running Locally

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### Building for Production

```bash
npm run build
```

### Deployment

This application is configured for deployment on AWS Amplify. The `amplify.yml` file contains the build configuration.

## API Integration

The frontend integrates with the following backend endpoints:

- `POST /extract-pdf-links` - Extract PDF links from a website
- `POST /process-pdf-batch` - Process PDF documents in batches
- `POST /create-knowledge-base` - Create knowledge base from processed documents
- `POST /ask-question` - Ask questions about processed documents
- `GET /documents` - List processed documents
- `GET /health` - Health check

## Technology Stack

- **React 19** - UI framework
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **Axios** - HTTP client
- **Lucide React** - Icons
- **Headless UI** - Accessible UI components
