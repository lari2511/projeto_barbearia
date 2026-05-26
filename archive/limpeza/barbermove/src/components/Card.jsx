import React from 'react';

export default function Card({ children, className = '' }) {
  return (
    <div className={`bg-[#1e1e24] rounded-2xl border border-zinc-800/50 p-4 ${className}`}>
      {children}
    </div>
  );
}
