import React from 'react';
export default function ScreenWrapper({ children }) {
  return <div className="mx-auto w-full max-w-4xl px-3 py-4 pb-[calc(5.5rem+env(safe-area-inset-bottom))] sm:px-4 sm:py-6">{children}</div>;
}
