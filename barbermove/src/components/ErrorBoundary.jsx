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
        <div className="p-4 font-sans text-white bg-black">
          <h1 className="text-lg mb-2 font-extrabold">Ocorreu um erro ao renderizar a página</h1>
          <p className="mb-3">Se a tela estava em branco, aqui vai o detalhe do erro para diagnóstico:</p>
          {this.state.error && (
            <pre className="whitespace-pre-wrap bg-zinc-900 border border-zinc-800 p-3 rounded">{String(this.state.error)}</pre>
          )}
          {stack && (
            <details open className="mt-3">
              <summary>Stack técnico</summary>
              <pre className="whitespace-pre-wrap bg-zinc-900 border border-zinc-800 p-3 rounded mt-2">{stack}</pre>
            </details>
          )}
          <button onClick={this.handleReload} className="mt-4 px-3 py-2 bg-zinc-800 text-white rounded">Recarregar página</button>
        </div>
      );
    }
    return this.props.children;
  }
}
