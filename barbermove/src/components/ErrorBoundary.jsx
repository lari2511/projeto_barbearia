import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, info: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    this.setState({ info });
    // Log do erro para monitoramento em desenvolvimento
    if (import.meta.env.DEV) {
      console.error('🐞 Erro capturado:', error, info);
    }
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      const stack = (this.state.error && this.state.error.stack) || (this.state.info && this.state.info.componentStack);
      return (
        <div style={{ padding: 16, fontFamily: 'system-ui, Arial', color: '#111', background: '#fff' }}>
          <h1 style={{ fontSize: 18, marginBottom: 8 }}>Ocorreu um erro ao renderizar a página</h1>
          <p style={{ marginBottom: 12 }}>Se a tela estava em branco, aqui vai o detalhe do erro para diagnóstico:</p>
          {this.state.error && (
            <pre style={{ whiteSpace: 'pre-wrap', background: '#f9fafb', border: '1px solid #e5e7eb', padding: 12, borderRadius: 8 }}>
              {String(this.state.error)}
            </pre>
          )}
          {stack && (
            <details open style={{ marginTop: 12 }}>
              <summary>Stack técnico</summary>
              <pre style={{ whiteSpace: 'pre-wrap', background: '#f9fafb', border: '1px solid #e5e7eb', padding: 12, borderRadius: 8 }}>
                {stack}
              </pre>
            </details>
          )}
          <button onClick={this.handleReload} style={{ marginTop: 16, padding: '8px 12px', background: '#111827', color: '#fff', borderRadius: 6 }}>
            Recarregar página
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
