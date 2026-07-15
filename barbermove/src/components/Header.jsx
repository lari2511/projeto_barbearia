import React from 'react';
import { Scissors } from 'lucide-react';

export default function Header({ title, subtitle, actionButton, onNotify }) {
  return (
    <div className="bm-card flex items-center justify-between mb-4 p-3">
      <div className="flex items-start gap-3 min-w-0">
        <div className="text-2xl flex-shrink-0"><Scissors size={22} className="text-orange-400"/></div>
        <div className="min-w-0">
          <h1 className="bm-title truncate">{title}</h1>
          {subtitle && <div className="bm-subtitle mt-1 truncate">{subtitle}</div>}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onNotify}
          className="bm-notif-btn relative flex items-center justify-center"
          aria-label="Notificações"
        >
          🔔
          <span className="absolute right-0 top-0 w-2 h-2 rounded-full bg-orange-400 ring-1 ring-black" />
        </button>

        {actionButton && (
          <button type="button" onClick={actionButton.onClick} className="bm-accent-btn flex items-center gap-2">
            {actionButton.icon}
            <span>{actionButton.label}</span>
          </button>
        )}
      </div>
    </div>
  );
}
