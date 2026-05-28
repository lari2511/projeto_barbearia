import React from 'react';
export default function AppCard({ children, className = '' }) {
  const base = 'bg-zinc-900 border border-zinc-800 rounded-lg p-4';
  const classes = (base + ' ' + (className || '')).trim();
  return (
    <div className={classes}>
      {children}
    </div>
  );
}
