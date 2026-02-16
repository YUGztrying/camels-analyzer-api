import { Component } from 'react';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <p>An unexpected error occurred while rendering the results.</p>
          <details style={{ marginTop: '1rem', color: '#666' }}>
            <summary>Error details</summary>
            <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem' }}>
              {this.state.error?.message || 'Unknown error'}
            </pre>
          </details>
          <button onClick={this.handleReset} style={{ marginTop: '1rem' }}>
            Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
