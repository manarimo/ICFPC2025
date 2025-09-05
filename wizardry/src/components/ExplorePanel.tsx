'use client';

import { useState } from 'react';
import { GameState } from '@/types/api';
import { apiClient } from '@/lib/api';

interface ExplorePanelProps {
  gameState: GameState;
  onUpdateGameState: (updates: Partial<GameState>) => void;
}

export function ExplorePanel({ gameState, onUpdateGameState }: ExplorePanelProps) {
  const [routeInput, setRouteInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const parseRouteInput = (input: string): { plans: string[], routePlans: number[][] } => {
    const lines = input
      .trim()
      .split('\n')
      .filter(line => line.trim());

    const plans: string[] = [];
    const routePlans: number[][] = [];

    for (const line of lines) {
      const trimmedLine = line.trim();
      // Validate that each character is a digit 0-5
      if (!/^[0-5]+$/.test(trimmedLine)) {
        throw new Error(`Invalid route: "${trimmedLine}". Must contain only digits 0-5.`);
      }
      
      plans.push(trimmedLine);
      routePlans.push(trimmedLine.split('').map(d => parseInt(d, 10)));
    }

    return { plans, routePlans };
  };

  const handleExplore = async () => {
    if (!routeInput.trim()) {
      setError('Please enter at least one route');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const { plans, routePlans } = parseRouteInput(routeInput);
      
      const response = await apiClient.explore({
        id: gameState.teamId,
        plans: plans,
      });

      const newResults = routePlans.map((routePlan, index) => ({
        routePlan,
        roomLabels: response.results[index] || []
      }));

      onUpdateGameState({
        queryCount: response.queryCount,
        explorationResults: [...gameState.explorationResults, ...newResults]
      });

      setRouteInput('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred during exploration');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-2xl font-semibold mb-4">Explore Routes</h2>
      
      <div className="space-y-4">
        <div>
          <label htmlFor="routes" className="block text-sm font-medium text-gray-700 mb-2">
            Route Plans (one per line, consecutive door numbers 0-5)
          </label>
          <textarea
            id="routes"
            value={routeInput}
            onChange={(e) => setRouteInput(e.target.value)}
            rows={6}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
            placeholder=""
            disabled={isLoading}
          />
          <p className="text-sm text-gray-600 mt-1">
            Example: &quot;012&quot; means go through door 0, then door 1, then door 2
          </p>
        </div>

        {error && (
          <div className="text-red-600 text-sm">{error}</div>
        )}

        <button
          onClick={handleExplore}
          disabled={isLoading || !routeInput.trim()}
          className="bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Exploring...' : 'Explore Routes'}
        </button>
      </div>

      {gameState.explorationResults.length > 0 && (
        <div className="mt-8">
          <h3 className="text-lg font-semibold mb-4">Exploration Results</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full bg-white border border-gray-300">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 border-b text-left text-sm font-medium text-gray-700">
                    Route Plan
                  </th>
                  <th className="px-4 py-2 border-b text-left text-sm font-medium text-gray-700">
                    Room Labels Discovered
                  </th>
                </tr>
              </thead>
              <tbody>
                {gameState.explorationResults.map((result, index) => (
                  <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    <td className="px-4 py-2 border-b text-sm font-mono">
                      [{result.routePlan.join(', ')}]
                    </td>
                    <td className="px-4 py-2 border-b text-sm font-mono">
                      [{result.roomLabels.join(', ')}]
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}