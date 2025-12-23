'use client';
import Link from 'next/link';
import { Home, Grid, Settings, MessageSquare, Menu, X, ChevronRight, Activity } from 'lucide-react';
import { useState } from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export default function Sidebar() {
  const [isOpen, setIsOpen] = useState(false);

  const menuItems = [
    { icon: Home, label: 'Dashboard', href: '/' },
    { icon: Grid, label: 'All Brands', href: '/brands' },
    { icon: Activity, label: 'System Status', href: '/status' },
  ];

  return (
    <>
      {/* Mobile Menu Button */}
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-4 left-4 z-50 p-2 bg-white rounded-lg shadow-md lg:hidden border border-gray-200"
      >
        {isOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Sidebar */}
      <aside className={cn(
        "fixed inset-y-0 left-0 z-40 w-64 bg-white border-r border-gray-200 transform transition-transform duration-300 ease-in-out lg:translate-x-0",
        isOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="flex flex-col h-full p-6">
          <div className="flex items-center gap-3 mb-10">
            <img 
              src="https://d3m9l0v76dty0.cloudfront.net/system/logos/609/original/58f32fd9c7512e0da74a38e385cc9a2f.png" 
              alt="Halilit" 
              className="h-8 object-contain"
            />
            <span className="font-bold text-xl tracking-tight text-gray-900">Support</span>
          </div>

          <nav className="flex-grow space-y-1 overflow-y-auto">
            <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-4 px-3">
              Main Menu
            </div>
            {menuItems.map((item) => (
              <Link
                key={item.label}
                href={item.href}
                className="flex items-center gap-3 px-4 py-3 text-gray-600 hover:bg-gray-50 hover:text-blue-600 rounded-xl transition-all group"
                onClick={() => setIsOpen(false)}
              >
                <item.icon size={20} className="group-hover:scale-110 transition-transform" />
                <span className="font-medium">{item.label}</span>
              </Link>
            ))}
          </nav>

          <div className="mt-auto pt-6 border-t border-gray-100">
            <div className="flex items-center gap-3 px-4 py-3 text-gray-400 text-sm">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span>System Online</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-30 lg:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  );
}
