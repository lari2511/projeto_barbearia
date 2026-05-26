import React from 'react';

export default function Header({ title, right, actionButton, className = '' }) {
  return (
    <header className={`app-header ${className} flex items-center justify-between`}> 
      <div className="flex items-center gap-3">
        <div className="text-lg">🔔</div>
        <div>
          {title && <div className="font-extrabold text-base">{title}</div>}
        </div>
      </div>
      <div>
        {actionButton ? (
          <button onClick={actionButton.onClick} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl font-extrabold text-sm bg-transparent border border-transparent text-[var(--panel-ink,white)]">
            {actionButton.icon}
            <span className="ml-1">{actionButton.label}</span>
          </button>
        ) : (
          right
        )}
      </div>
    </header>
  );
}
