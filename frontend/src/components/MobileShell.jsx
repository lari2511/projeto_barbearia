import React, { useState } from 'react'

export default function MobileShell({ children }) {
  const [enabled, setEnabled] = useState(true)

  // Ativa o preview móvel por padrão apenas em desenvolvimento
  const isDev = import.meta.env && import.meta.env.DEV

  if (!isDev) return children

  return (
    <div className="mobile-preview-root">
      <div className={`device-frame ${enabled ? 'device-enabled' : 'device-disabled'}`}>
        {children}
      </div>

      <div className="mobile-preview-controls">
        <button onClick={() => setEnabled((s) => !s)} className="px-3 py-1 rounded bg-barberBlue text-white text-sm">
          {enabled ? 'Desativar preview móvel' : 'Ativar preview móvel'}
        </button>
        <span className="ml-2 text-xs text-barberTextGray">Preview móvel (dev)</span>
      </div>
    </div>
  )
}
