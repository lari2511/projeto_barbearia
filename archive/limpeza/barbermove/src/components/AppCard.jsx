import React from 'react';

export default function AppCard({ children, className = '', variant }) {
  // Garantir aparência consistente mesmo quando faltam classes
  const baseUtils = 'bg-zinc-900 rounded-2xl p-5';
  const classes = `${baseUtils} app-card ${variant ? `app-card-${variant}` : ''} ${className}`.trim();
  return (
    <div className={classes}>
      {children}
    </div>
  );
}
