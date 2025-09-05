'use client';

import { useBackend, BackendType } from '@/contexts/BackendContext';

export function BackendToggle() {
  const { backendType, setBackendType } = useBackend();

  const handleToggle = (type: BackendType) => {
    setBackendType(type);
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow mb-6">
      <h3 className="text-lg font-semibold mb-3">Backend Selection</h3>
      <div className="flex gap-2">
        <button
          onClick={() => handleToggle('mock')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            backendType === 'mock'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Mock Server
        </button>
        <button
          onClick={() => handleToggle('official')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            backendType === 'official'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Official API
        </button>
      </div>
      <p className="text-sm text-gray-600 mt-2">
        Current: {backendType === 'mock' ? 'Mock Server' : 'Official API'}
      </p>
    </div>
  );
}