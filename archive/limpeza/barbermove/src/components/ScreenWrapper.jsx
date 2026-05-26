import React from 'react';

export default function ScreenWrapper({ children, className = '' }) {
  return (
    <div className={`min-h-screen bg-[#050505] text-white font-sans antialiased flex justify-center px-3 py-4 sm:px-4 ${className}`}>
      <div className="w-full max-w-[430px] min-h-[calc(100vh-2rem)] rounded-[2rem] border border-orange-500/20 bg-[radial-gradient(circle_at_top,rgba(249,115,22,0.10),transparent_26%),linear-gradient(180deg,rgba(15,15,17,0.99),rgba(5,5,5,1))] shadow-[0_18px_42px_rgba(0,0,0,0.52),0_0_0_1px_rgba(124,58,237,0.14),0_0_70px_rgba(249,115,22,0.10)] overflow-hidden">
        <div className="w-full min-h-[calc(100vh-2rem)] p-4 sm:p-5">
          {children}
        </div>
      </div>
    </div>
  );
}
