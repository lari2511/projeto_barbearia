import React from 'react'

export default function LayoutMobile({ children }) {
  return (
    <div className="min-h-screen bg-barberBg text-white flex flex-col">
      <div className="w-full max-w-md mx-auto flex-1 flex flex-col"> 
        {children}
      </div>
    </div>
  )
}
