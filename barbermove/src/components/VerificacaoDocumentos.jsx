// --- ARQUIVO: barbermove/src/components/VerificacaoDocumentos.jsx ---
// Componente para upload e verificação de documentos

import React, { useState } from 'react';
import { Upload, CheckCircle } from 'lucide-react';

export default function VerificacaoDocumentos({ _usuarioId, onVerificado }) {
  const [etapa, setEtapa] = useState('inicio'); // 'inicio', 'upload', 'confirmacao', 'finalizado'
  const [documentos, setDocumentos] = useState({
    cpf: '',
    rg: '',
    frente: null,
    verso: null,
    selfie: null
  });
  const [loading, setLoading] = useState(false);
  const [mensagem, setMensagem] = useState('');
  const [sucesso, setSucesso] = useState(false);

  const handleUpload = (tipo, arquivo) => {
    if (!arquivo) return;
    setDocumentos(prev => ({
      ...prev,
      [tipo === 'frente' ? 'frente' : tipo === 'verso' ? 'verso' : 'selfie']: arquivo
    }));
    setMensagem(`${tipo.toUpperCase()} selecionado!`);
  };

  const handleSalvarDocumentos = async () => {
    if (!documentos.cpf || !documentos.rg || !documentos.frente || !documentos.verso || !documentos.selfie) {
      setMensagem('Preencha todos os campos');
      return;
    }

    setLoading(true);
    try {
      const uploadData = new FormData();
      uploadData.append('documento_frente', documentos.frente);
      uploadData.append('documento_verso', documentos.verso);
      uploadData.append('selfie_documento', documentos.selfie);

      const uploadResponse = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/documentos/upload-files`, {
        method: 'POST',
        body: uploadData,
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });

      if (!uploadResponse.ok) {
        setMensagem('Erro ao enviar imagens');
        setLoading(false);
        return;
      }

      const uploadResult = await uploadResponse.json();

      const salvarResponse = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/documentos/upload`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          rg: documentos.rg,
          documento_frente_url: uploadResult.documento_frente_url,
          documento_verso_url: uploadResult.documento_verso_url,
          selfie_documento_url: uploadResult.selfie_documento_url
        })
      });

      if (!salvarResponse.ok) {
        setMensagem('Erro ao salvar documentos');
        setLoading(false);
        return;
      }

      await fetch(`${import.meta.env.VITE_API_URL}/api/v1/usuarios/me`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ cpf: documentos.cpf })
      });

      setSucesso(true);
      setMensagem('Documentos salvos! Aguardando verificação...');
      setEtapa('finalizado');
      setTimeout(() => onVerificado && onVerificado(), 2000);
    } catch (_err) {
      setMensagem('Erro ao salvar documentos');
    }
    setLoading(false);
  };

  return (
    <div className="bg-zinc-900 rounded-3xl p-8 border border-zinc-800 max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold text-white mb-8">Verificação de Documentos</h2>

      {etapa === 'inicio' && (
        <div className="space-y-4">
          <p className="text-zinc-400">Para usar a plataforma como barbeiro/barbearia, é necessário verificar sua identidade.</p>
          <button
            onClick={() => setEtapa('upload')}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-xl transition"
          >
            Começar Verificação
          </button>
        </div>
      )}

      {etapa === 'upload' && (
        <div className="space-y-6">
          {/* CPF e RG */}
          <div className="grid grid-cols-2 gap-4">
            <input
              type="text"
              placeholder="CPF (000.000.000-00)"
              className="bg-zinc-800 text-white px-4 py-3 rounded-xl border border-zinc-700 focus:border-blue-500 outline-none"
              value={documentos.cpf}
              onChange={(e) => setDocumentos(prev => ({ ...prev, cpf: e.target.value }))}
            />
            <input
              type="text"
              placeholder="RG/CNH"
              className="bg-zinc-800 text-white px-4 py-3 rounded-xl border border-zinc-700 focus:border-blue-500 outline-none"
              value={documentos.rg}
              onChange={(e) => setDocumentos(prev => ({ ...prev, rg: e.target.value }))}
            />
          </div>

          {/* Upload de Documentos */}
          <div className="space-y-4">
            <div className="border-2 border-dashed border-zinc-700 rounded-xl p-6 text-center">
              <Upload size={32} className="mx-auto text-zinc-500 mb-2" />
              <p className="text-zinc-400 mb-4">Documento Frente</p>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => handleUpload('frente', e.target.files[0])}
                className="hidden"
                id="frente"
              />
              <label htmlFor="frente" className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg cursor-pointer inline-block">
                Selecionar
              </label>
              {documentos.frente && <p className="text-green-500 mt-2">✓ Enviado</p>}
            </div>

            <div className="border-2 border-dashed border-zinc-700 rounded-xl p-6 text-center">
              <Upload size={32} className="mx-auto text-zinc-500 mb-2" />
              <p className="text-zinc-400 mb-4">Documento Verso</p>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => handleUpload('verso', e.target.files[0])}
                className="hidden"
                id="verso"
              />
              <label htmlFor="verso" className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg cursor-pointer inline-block">
                Selecionar
              </label>
              {documentos.verso && <p className="text-green-500 mt-2">✓ Enviado</p>}
            </div>

            <div className="border-2 border-dashed border-zinc-700 rounded-xl p-6 text-center">
              <Upload size={32} className="mx-auto text-zinc-500 mb-2" />
              <p className="text-zinc-400 mb-4">Selfie com Documento</p>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => handleUpload('selfie', e.target.files[0])}
                className="hidden"
                id="selfie"
              />
              <label htmlFor="selfie" className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg cursor-pointer inline-block">
                Selecionar
              </label>
              {documentos.selfie && <p className="text-green-500 mt-2">✓ Enviado</p>}
            </div>
          </div>

          {mensagem && (
            <div className="bg-zinc-800 border border-zinc-700 rounded-xl p-4">
              <p className={sucesso ? 'text-green-400' : 'text-yellow-400'}>{mensagem}</p>
            </div>
          )}

          <div className="flex gap-4">
            <button
              onClick={() => setEtapa('inicio')}
              className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white font-bold py-3 rounded-xl transition"
            >
              Voltar
            </button>
            <button
              onClick={handleSalvarDocumentos}
              disabled={loading}
              className="flex-1 bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded-xl transition disabled:opacity-50"
            >
              {loading ? 'Salvando...' : 'Confirmar e Enviar'}
            </button>
          </div>
        </div>
      )}

      {etapa === 'finalizado' && (
        <div className="text-center space-y-4">
          <CheckCircle size={64} className="mx-auto text-green-500" />
          <h3 className="text-xl font-bold text-white">Documentos Enviados!</h3>
          <p className="text-zinc-400">Aguardando verificação pela equipe. Você será notificado em breve.</p>
        </div>
      )}
    </div>
  );
}
