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
        <div className="min-h-[100dvh] bg-black px-4 py-6 text-white">
          <div className="mx-auto flex w-full max-w-xl flex-col gap-4 rounded-3xl border border-zinc-800 bg-zinc-950 p-4 shadow-2xl shadow-black/40 sm:p-6">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.28em] text-orange-300">BarberMove</p>
            <h1 className="mt-2 text-xl font-extrabold sm:text-2xl">Ocorreu um erro ao renderizar a página</h1>
            <p className="mt-2 text-sm text-zinc-300">O app não conseguiu montar a tela. Você pode recarregar agora ou copiar o detalhe abaixo para diagnóstico.</p>
          </div>
          {this.state.error && (
            <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded-2xl border border-zinc-800 bg-zinc-900 p-3 text-xs text-zinc-200">{String(this.state.error)}</pre>
          )}
          {stack && (
            <details className="rounded-2xl border border-zinc-800 bg-zinc-900 p-3">
              <summary className="cursor-pointer text-sm font-bold text-zinc-200">Stack técnico</summary>
              <pre className="mt-3 max-h-56 overflow-auto whitespace-pre-wrap text-[11px] leading-relaxed text-zinc-300">{stack}</pre>
            </details>
          )}
          <button onClick={this.handleReload} className="inline-flex w-full items-center justify-center rounded-2xl bg-orange-500 px-4 py-3 text-sm font-black text-white hover:bg-orange-600 sm:w-auto">
            Recarregar página
          </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
