import React from 'react';

export default function PainelLayout({ children }) {
  return (
    <div className="min-h-screen bg-black text-white">
      <main>{children}</main>
    </div>
  );
}
