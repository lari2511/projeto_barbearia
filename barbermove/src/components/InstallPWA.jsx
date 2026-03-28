import { useState } from 'react';
import { Download, X } from 'lucide-react';

export default function InstallPWA() {
  const [showBanner, setShowBanner] = useState(true);
  const [showInstructions, setShowInstructions] = useState(false);

  const isIOS = /iPhone|iPad|iPod/.test(navigator.userAgent);
  const isAndroid = /Android/.test(navigator.userAgent);
  const isInStandaloneMode = window.matchMedia('(display-mode: standalone)').matches;

  // Não mostrar se já está instalado
  if (isInStandaloneMode) return null;
  if (!showBanner) return null;

  return (
    <>
      {/* Banner Principal */}
      <div className="fixed top-0 left-0 right-0 bg-gradient-to-r from-blue-600 to-blue-500 text-white p-3 shadow-lg z-50">
        <div className="flex items-center justify-between max-w-md mx-auto">
          <div className="flex items-center gap-2 flex-1">
            <Download className="w-5 h-5" />
            <span className="font-semibold text-sm">Instalar BarberMove</span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowInstructions(true)}
              className="bg-white text-blue-600 px-3 py-1.5 rounded text-sm font-semibold hover:bg-blue-50"
            >
              Como?
            </button>
            <button
              onClick={() => setShowBanner(false)}
              className="text-white hover:bg-blue-700 p-1.5 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Modal de Instruções */}
      {showInstructions && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-[100] p-4">
          <div className="bg-gray-900 rounded-2xl max-w-md w-full p-6 text-white">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold">Instalar App</h3>
              <button
                onClick={() => setShowInstructions(false)}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {isIOS && (
              <div className="space-y-4">
                <div className="bg-blue-600 p-4 rounded-lg">
                  <p className="font-semibold mb-3 text-lg">📱 iPhone/iPad (Safari)</p>
                  <ol className="text-sm space-y-3 list-decimal list-inside">
                    <li><strong>Passo 1:</strong> Toque no botão <span className="bg-white text-blue-600 px-2 py-1 rounded text-xs">📤 Compartilhar</span> na parte inferior da tela</li>
                    <li><strong>Passo 2:</strong> Role a lista e encontre <span className="bg-white text-blue-600 px-2 py-1 rounded text-xs">➕ Adicionar à Tela de Início</span></li>
                    <li><strong>Passo 3:</strong> Toque em <span className="bg-white text-blue-600 px-2 py-1 rounded text-xs">Adicionar</span> no canto superior</li>
                  </ol>
                  <div className="mt-3 pt-3 border-t border-blue-400">
                    <p className="text-xs">✅ O ícone do BarberMove aparecerá na sua tela inicial como um app normal!</p>
                  </div>
                </div>
              </div>
            )}

            {isAndroid && (
              <div className="space-y-4">
                <div className="bg-green-600 p-4 rounded-lg">
                  <p className="font-semibold mb-3 text-lg">🤖 Android (Chrome)</p>
                  <ol className="text-sm space-y-3 list-decimal list-inside">
                    <li><strong>Passo 1:</strong> Toque no menu <span className="bg-white text-green-600 px-2 py-1 rounded text-xs">⋮</span> (3 pontos verticais) no canto superior direito</li>
                    <li><strong>Passo 2:</strong> Toque em <span className="bg-white text-green-600 px-2 py-1 rounded text-xs">Adicionar à tela inicial</span></li>
                    <li><strong>Passo 3:</strong> Confirme tocando em <span className="bg-white text-green-600 px-2 py-1 rounded text-xs">Adicionar</span></li>
                  </ol>
                  <div className="mt-3 pt-3 border-t border-green-400">
                    <p className="text-xs">✅ O app ficará disponível na sua gaveta de apps!</p>
                  </div>
                </div>
              </div>
            )}

            {!isIOS && !isAndroid && (
              <div className="space-y-4">
                <div className="bg-purple-600 p-4 rounded-lg">
                  <p className="font-semibold mb-2">💻 Para Desktop:</p>
                  <ol className="text-sm space-y-2 list-decimal list-inside">
                    <li>Clique no ícone <strong>➕</strong> na barra de endereço</li>
                    <li>Ou vá no menu → <strong>"Instalar BarberMove"</strong></li>
                    <li>Confirme a instalação</li>
                  </ol>
                </div>
              </div>
            )}

            <div className="mt-6 pt-4 border-t border-gray-700">
              <p className="text-xs text-gray-400 text-center">
                ✨ Depois de instalado, o app funcionará como nativo, 
                com ícone próprio e sem barra de navegador!
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
