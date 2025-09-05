'use client';

import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { ApiClient } from '@/lib/api';

export type BackendType = 'official' | 'mock';

interface BackendContextType {
  backendType: BackendType;
  setBackendType: (type: BackendType) => void;
  getApiBaseUrl: () => string;
  apiClient: ApiClient;
}

const BackendContext = createContext<BackendContextType | undefined>(undefined);

const OFFICIAL_API_URL = 'https://31pwr5t6ij.execute-api.eu-west-2.amazonaws.com';
const MOCK_API_URL = process.env.NEXT_PUBLIC_MOCK_API_BASE_URL || 'http://localhost:8000';

export function BackendProvider({ children }: { children: React.ReactNode }) {
  const [backendType, setBackendTypeState] = useState<BackendType>('mock');

  useEffect(() => {
    const savedBackend = localStorage.getItem('backend-type') as BackendType;
    if (savedBackend && (savedBackend === 'official' || savedBackend === 'mock')) {
      setBackendTypeState(savedBackend);
    }
  }, []);

  const setBackendType = (type: BackendType) => {
    setBackendTypeState(type);
    localStorage.setItem('backend-type', type);
  };

  const getApiBaseUrl = () => {
    return backendType === 'official' ? OFFICIAL_API_URL : MOCK_API_URL;
  };

  const apiClient = useMemo(() => {
    const client = new ApiClient();
    client.setBackendType(backendType);
    return client;
  }, [backendType]);

  return (
    <BackendContext.Provider value={{ backendType, setBackendType, getApiBaseUrl, apiClient }}>
      {children}
    </BackendContext.Provider>
  );
}

export function useBackend() {
  const context = useContext(BackendContext);
  if (context === undefined) {
    throw new Error('useBackend must be used within a BackendProvider');
  }
  return context;
}