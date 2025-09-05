'use client';

import { useState, useEffect } from 'react';
import { useBackend } from '@/contexts/BackendContext';
import { storage } from '@/lib/storage';

interface SessionSetupProps {
  onSessionStart: (teamId: string, problemName: string) => void;
}

export function SessionSetup({ onSessionStart }: SessionSetupProps) {
  const { apiClient } = useBackend();
  const [teamId, setTeamId] = useState('');
  const [problemName, setProblemName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    // Load saved team ID and problem name from local storage
    const savedTeamId = storage.getTeamId();
    const savedProblemName = storage.getProblemName();
    
    if (savedTeamId) {
      setTeamId(savedTeamId);
    }
    if (savedProblemName) {
      setProblemName(savedProblemName);
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!teamId.trim() || !problemName.trim()) {
      setError('Please enter both Team ID and Problem Name');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const response = await apiClient.select({
        id: teamId.trim(),
        problemName: problemName.trim(),
      });

      // If we get a response with problemName, consider it successful
      if (response.problemName) {
        // Save to local storage for persistence
        storage.setTeamId(teamId.trim());
        storage.setProblemName(response.problemName);
        
        onSessionStart(teamId.trim(), response.problemName);
      } else {
        setError('Failed to start session');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto bg-white p-6 rounded-lg shadow">
      <h2 className="text-2xl font-semibold mb-6 text-center">Start Session</h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="teamId" className="block text-sm font-medium text-gray-700 mb-1">
            Team ID
          </label>
          <input
            type="text"
            id="teamId"
            value={teamId}
            onChange={(e) => setTeamId(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Enter your team ID"
            disabled={isLoading}
          />
        </div>

        <div>
          <label htmlFor="problemName" className="block text-sm font-medium text-gray-700 mb-1">
            Problem Name
          </label>
          <input
            type="text"
            id="problemName"
            value={problemName}
            onChange={(e) => setProblemName(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Enter problem name"
            disabled={isLoading}
          />
        </div>

        {error && (
          <div className="text-red-600 text-sm">{error}</div>
        )}

        <button
          type="submit"
          disabled={isLoading}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Starting Session...' : 'Start Session'}
        </button>
      </form>
    </div>
  );
}