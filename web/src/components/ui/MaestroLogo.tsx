import React from 'react';

interface MaestroLogoProps {
  className?: string;
}

export function MaestroLogo({ className = "w-10 h-10" }: MaestroLogoProps) {
  return (
    <svg 
      viewBox="0 0 100 100" 
      className={className} 
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <filter id="neonGlow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>

      {/* Connecting strokes */}
      <path 
        d="M20 80 L35 30 L50 60 L65 30 L80 80" 
        fill="none" 
        stroke="currentColor" 
        strokeWidth="4" 
        strokeLinecap="round" 
        strokeLinejoin="round" 
        className="text-zinc-600"
      />

      {/* Base nodes (circles) */}
      <circle cx="20" cy="80" r="5" className="fill-zinc-800 stroke-zinc-700" strokeWidth="2" />
      <circle cx="35" cy="30" r="5" className="fill-zinc-800 stroke-zinc-700" strokeWidth="2" />
      <circle cx="65" cy="30" r="5" className="fill-zinc-800 stroke-zinc-700" strokeWidth="2" />
      <circle cx="80" cy="80" r="5" className="fill-zinc-800 stroke-zinc-700" strokeWidth="2" />

      {/* Glowing Center Core */}
      <circle 
        cx="50" 
        cy="60" 
        r="6" 
        className="fill-cyan-400" 
        filter="url(#neonGlow)"
      />
    </svg>
  );
}
