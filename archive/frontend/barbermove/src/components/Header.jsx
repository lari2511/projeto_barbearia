import React from 'react';
export default function Header({ title, actionButton }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h1 className="text-xl font-bold">{title}</h1>
      {actionButton && (
        <button onClick={actionButton.onClick} className="px-3 py-1 rounded bg-zinc-800 border border-zinc-700">
          {actionButton.icon} <span className="ml-2">{actionButton.label}</span>
        </button>
      )}
    </div>
  );
}
